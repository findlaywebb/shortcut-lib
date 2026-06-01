"""Agent-level eval harness for the shortcut-lib MCP server.

Drives a model through the FastMCP server's tools (hosted in-process, the
same code path as stdio, no transport noise) and grades each task's emitted
``.shortcut`` file with deterministic decoders.

The harness is provider-agnostic: the same tasks and the same deterministic
graders run against both Anthropic (Messages API) and OpenAI (Responses API
tool-calling). Only the model conversation loop differs; the MCP-call
mechanics and grading are shared.

Usage::

    uv run python evals/mcp/run_evals.py
    uv run python evals/mcp/run_evals.py --k 3 --task 01-clipboard-roundtrip
    uv run python evals/mcp/run_evals.py --model gpt-5.5 --k 10
    uv run python evals/mcp/run_evals.py --dry-run            # no API calls

Requires ``ANTHROPIC_API_KEY`` (Anthropic models) or ``OPENAI_API_KEY``
(OpenAI models) set unless ``--dry-run``.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("fastmcp", reason="evals require [mcp] extra")
pytest.importorskip("anthropic", reason="evals require [evals] extra")

from anthropic import APIStatusError, RateLimitError
from fastmcp import Client

from shortcut_lib.mcp.server import build_server

# The evals dir is not an installed package; add it to the path so the
# sibling modules import cleanly whether this file is run as a script
# (python evals/mcp/run_evals.py) or imported by a test.
sys.path.insert(0, str(Path(__file__).parent))
import _stats  # ty: ignore[unresolved-import]
from _drivers import (  # ty: ignore[unresolved-import]
    _SDK_MAX_RETRIES,
    ModelDriver,
    build_driver,
    provider_api_error,
    provider_for,
)
from _grading import (  # ty: ignore[unresolved-import]
    Task,
    grade,
    load_tasks,
)

_DEFAULT_MODEL = "claude-sonnet-4-6"
# Concurrency calibrated for tier-1 rate limits (~50k input tokens/minute
# on haiku); ~22k tokens per attempt means 2 in flight keeps headroom for
# the SDK's automatic 429 retries to settle within one minute.
_DEFAULT_CONCURRENCY = 2
_RESULTS_DIR = Path(__file__).parent / "results"


# ── Result model ─────────────────────────────────────────────────────


@dataclass
class AttemptResult:
    passed: bool
    reason: str
    tool_calls: int
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    built_path: str | None = None
    saw_recovery: bool = False


@dataclass
class TaskResult:
    id: str
    attempts: list[AttemptResult]

    @property
    def passed_any(self) -> bool:
        return any(a.passed for a in self.attempts)

    @property
    def pass_rate(self) -> float:
        if not self.attempts:
            return 0.0
        return sum(a.passed for a in self.attempts) / len(self.attempts)


# ── Agent loop ───────────────────────────────────────────────────────


def _failed_attempt(reason: str) -> AttemptResult:
    """Build an AttemptResult that fails fast with a human-readable reason."""
    return AttemptResult(
        passed=False,
        reason=reason,
        tool_calls=0,
        input_tokens=0,
        output_tokens=0,
        built_path=None,
        saw_recovery=False,
    )


async def _run_attempt(
    driver: ModelDriver,
    task: Task,
    output_dir: Path,
) -> AttemptResult:
    # Each attempt gets its own server + Client so concurrent attempts don't
    # share state. The output directory is injected into shortcut_build args
    # at routing time (not env), so attempts running side-by-side land their
    # files in disjoint directories. The provider-specific conversation loop
    # lives behind the driver; everything below it is provider-neutral.
    server = build_server()
    async with Client(server) as mcp_client:
        state = await driver.run(task, mcp_client, output_dir)

    passed, reason = grade(task, output_dir, state.built_path, state.saw_recovery)
    return AttemptResult(
        passed=passed,
        reason=reason,
        tool_calls=state.tool_calls,
        input_tokens=state.input_tokens,
        output_tokens=state.output_tokens,
        cache_read_tokens=state.cache_read_tokens,
        cache_write_tokens=state.cache_write_tokens,
        built_path=state.built_path,
        saw_recovery=state.saw_recovery,
    )


# ── Driver ───────────────────────────────────────────────────────────


def _summarise(results: Iterable[TaskResult], k: int) -> dict[str, Any]:
    rs = list(results)
    task_count = max(len(rs), 1)
    pass_at_1 = sum(r.attempts[0].passed for r in rs if r.attempts) / task_count
    pass_at_k = sum(r.passed_any for r in rs) / task_count
    total_tool_calls = sum(a.tool_calls for r in rs for a in r.attempts)
    total_in = sum(a.input_tokens for r in rs for a in r.attempts)
    total_out = sum(a.output_tokens for r in rs for a in r.attempts)
    total_cache_read = sum(a.cache_read_tokens for r in rs for a in r.attempts)
    total_cache_write = sum(a.cache_write_tokens for r in rs for a in r.attempts)

    # Bootstrap pass@1's CI at the task level: per-task pass-rate is the unit.
    # pass@1 is the mean of those rates only when k==1; for the interval we
    # resample whole tasks, which is the honest cluster for a small suite.
    per_task_rates = [r.pass_rate for r in rs]
    ci_low, ci_high = _stats.bootstrap_ci(per_task_rates)

    # Unbiased pass@k estimator pooled across tasks: average each task's
    # 1 - C(n-c,k)/C(n,k). With k attempts per task this matches the run's k.
    pass_k_unbiased = (
        sum(
            _stats.pass_at_k_unbiased(
                sum(a.passed for a in r.attempts), len(r.attempts), k
            )
            for r in rs
            if r.attempts
        )
        / task_count
    )

    # pass^k uses the overall per-attempt success probability as p.
    total_attempts = sum(len(r.attempts) for r in rs)
    total_passes = sum(a.passed for r in rs for a in r.attempts)
    p_overall = total_passes / total_attempts if total_attempts else 0.0

    return {
        "task_count": len(rs),
        "k": k,
        "pass@1": pass_at_1,
        "pass@1_ci_low": ci_low,
        "pass@1_ci_high": ci_high,
        f"pass@{k}": pass_at_k,
        "pass@k_unbiased": pass_k_unbiased,
        "pass_hat_k": _stats.pass_hat_k(p_overall, k),
        "tool_calls_total": total_tool_calls,
        "input_tokens_total": total_in,
        "output_tokens_total": total_out,
        "cache_read_tokens_total": total_cache_read,
        "cache_write_tokens_total": total_cache_write,
        "tokens_per_task": (total_in + total_out) / task_count,
        "tool_calls_per_task": total_tool_calls / task_count,
        "tasks": [
            {
                "id": r.id,
                "passed_any": r.passed_any,
                "pass_rate": r.pass_rate,
                "attempts": [
                    {
                        "passed": a.passed,
                        "reason": a.reason,
                        "tool_calls": a.tool_calls,
                        "input_tokens": a.input_tokens,
                        "output_tokens": a.output_tokens,
                        "cache_read_tokens": a.cache_read_tokens,
                        "cache_write_tokens": a.cache_write_tokens,
                        "built_path": a.built_path,
                        "saw_recovery": a.saw_recovery,
                    }
                    for a in r.attempts
                ],
            }
            for r in rs
        ],
    }


async def _run_all(
    tasks: list[Task],
    *,
    k: int,
    driver: ModelDriver,
    output_root: Path,
    concurrency: int,
) -> list[TaskResult]:
    """Run every (task, attempt) pair under a shared concurrency bound.

    Attempts are independent: each gets its own FastMCP server + Client +
    output directory, so we fan them all out under one Semaphore. The bound
    applies to the number of agent loops in flight at any moment, which is
    also (approximately) the number of concurrent API requests, so it's the
    right knob for rate-limit headroom regardless of provider.
    """
    semaphore = asyncio.Semaphore(concurrency)

    async def one_attempt(task: Task, idx: int) -> tuple[Task, int, AttemptResult]:
        async with semaphore:
            with tempfile.TemporaryDirectory(
                prefix=f"{task.id}-{idx}-", dir=output_root
            ) as td:
                try:
                    attempt = await _run_attempt(driver, task, Path(td))
                except RateLimitError as exc:
                    attempt = _failed_attempt(
                        f"rate limit (exhausted {_SDK_MAX_RETRIES} retries): "
                        f"{exc.message}"
                    )
                except APIStatusError as exc:
                    attempt = _failed_attempt(
                        f"API error {exc.status_code}: {exc.message}"
                    )
                except provider_api_error() as exc:
                    attempt = _failed_attempt(f"provider API error: {exc}")
            verdict = "PASS" if attempt.passed else "FAIL"
            print(
                f"[{task.id}] attempt {idx + 1}/{k}: {verdict}: "
                f"{attempt.reason} (tool_calls={attempt.tool_calls}, "
                f"tokens={attempt.input_tokens}+{attempt.output_tokens}, "
                f"cache r/w={attempt.cache_read_tokens}/"
                f"{attempt.cache_write_tokens})"
            )
            return task, idx, attempt

    coros = [one_attempt(task, idx) for task in tasks for idx in range(k)]
    completed = await asyncio.gather(*coros)

    grouped: dict[str, list[AttemptResult | None]] = {t.id: [None] * k for t in tasks}
    for task, idx, attempt in completed:
        grouped[task.id][idx] = attempt
    return [
        TaskResult(id=t.id, attempts=[a for a in grouped[t.id] if a is not None])
        for t in tasks
    ]


def _dry_run(tasks: list[Task]) -> int:
    """Validate task JSON files and exit; no API calls."""
    for task in tasks:
        g = task.graders
        print(f"[{task.id}] prompt={task.prompt[:60]}…")
        if g.expect_no_build:
            print("           expect_no_build=True (refuse-case)")
            continue
        print(
            f"           graders={g.must_contain} "
            f"actions=[{g.min_actions},{g.max_actions}]"
        )
        if g.must_not_contain:
            print(f"           must_not_contain={g.must_not_contain}")
    print(f"\n{len(tasks)} task(s) validated.")
    return 0


def _git_stamp() -> tuple[str | None, bool]:
    """Return ``(short_sha, dirty)`` for the repo, degrading to ``(None, False)``.

    Stamps every result with the commit it ran against so a regression can be
    pinned to a code state. Any git failure (no repo, git absent) yields a
    null commit rather than crashing the run.
    """
    repo = Path(__file__).resolve().parent

    def _git(*cmd: str) -> str | None:
        try:
            out = subprocess.run(  # noqa: S603 (fixed argv, no shell)
                ["git", *cmd],  # noqa: S607 (git resolved from PATH by design)
                cwd=repo,
                capture_output=True,
                text=True,
                check=True,
            )
        except (OSError, subprocess.CalledProcessError):
            return None
        return out.stdout

    sha = _git("rev-parse", "--short", "HEAD")
    status = _git("status", "--porcelain")
    commit = sha.strip() if sha is not None else None
    dirty = bool(status.strip()) if status is not None else False
    return commit, dirty


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--k", type=int, default=1, help="attempts per task")
    parser.add_argument("--task", type=str, default=None, help="substring filter")
    parser.add_argument("--model", type=str, default=_DEFAULT_MODEL)
    parser.add_argument(
        "--provider",
        type=str,
        choices=["anthropic", "openai"],
        default=None,
        help="override provider inference from the model name",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=_DEFAULT_CONCURRENCY,
        help="max attempts in flight at once",
    )
    parser.add_argument(
        "--reasoning-effort",
        type=str,
        choices=["none", "minimal", "low", "medium", "high"],
        default="none",
        help="OpenAI reasoning.effort axis; recorded on every result. "
        "'none' sends no reasoning param. Ignored by Anthropic models.",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="validate tasks only; no API calls"
    )
    args = parser.parse_args()

    tasks = load_tasks(args.task)

    if args.dry_run:
        return _dry_run(tasks)

    provider = args.provider or provider_for(args.model)
    driver = build_driver(provider, args.model, args.reasoning_effort)

    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mcp-evals-") as scratch_root:
        results = asyncio.run(
            _run_all(
                tasks,
                k=args.k,
                driver=driver,
                output_root=Path(scratch_root),
                concurrency=args.concurrency,
            )
        )

    summary = _summarise(results, k=args.k)
    summary["model"] = args.model
    summary["provider"] = provider
    summary["reasoning_effort"] = args.reasoning_effort
    commit, dirty = _git_stamp()
    summary["git_commit"] = commit
    summary["git_dirty"] = dirty
    summary["timestamp"] = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
    out_path = _RESULTS_DIR / f"{summary['timestamp']}.json"
    out_path.write_text(json.dumps(summary, indent=2))
    print(f"\nWrote {out_path}")
    dirty_mark = " (dirty)" if dirty else ""
    print(
        f"{provider}/{args.model} (effort={args.reasoning_effort}) "
        f"@ {commit}{dirty_mark}  "
        f"pass@1={summary['pass@1']:.2%} "
        f"[{summary['pass@1_ci_low']:.2%}, {summary['pass@1_ci_high']:.2%}]  "
        f"pass@{args.k}(est)={summary['pass@k_unbiased']:.2%}  "
        f"pass^{args.k}={summary['pass_hat_k']:.2%}  "
        f"tool_calls={summary['tool_calls_total']}  "
        f"tokens={summary['input_tokens_total']}+{summary['output_tokens_total']}  "
        f"cache r/w={summary['cache_read_tokens_total']}/"
        f"{summary['cache_write_tokens_total']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
