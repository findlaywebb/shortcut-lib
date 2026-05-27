"""Agent-level eval harness for the shortcut-lib MCP server.

Drives Claude through the FastMCP server's tools (hosted in-process — same
code path as stdio, no transport noise) and grades each task's emitted
``.shortcut`` file with deterministic decoders.

Usage::

    uv run python evals/mcp/run_evals.py
    uv run python evals/mcp/run_evals.py --k 3 --task 01-clipboard-roundtrip
    uv run python evals/mcp/run_evals.py --dry-run            # no API calls

Requires ``ANTHROPIC_API_KEY`` set unless ``--dry-run``.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("fastmcp", reason="evals require [mcp] extra")
pytest.importorskip("anthropic", reason="evals require [evals] extra")

from anthropic import Anthropic
from fastmcp import Client

from shortcut_lib.decode import DecodeError, decode_file
from shortcut_lib.mcp.server import build_server

_DEFAULT_MODEL = "claude-sonnet-4-6"
_SYSTEM_PROMPT = (
    "You are an Apple Shortcuts author. Your only goal in this session is to "
    "produce one signed .shortcut file that satisfies the user's request, "
    "using the tools provided. "
    "Always start by inspecting the registry (shortcut_list_actions) and the "
    "action schemas (shortcut_get_action_schema) before constructing a spec. "
    "Use shortcut_validate_spec before shortcut_build so a bad spec costs "
    "nothing. Stop after a successful shortcut_build call — do not chat."
)
_TASKS_DIR = Path(__file__).parent / "tasks"
_RESULTS_DIR = Path(__file__).parent / "results"
_MAX_AGENT_TURNS = 16


# ── Task model ───────────────────────────────────────────────────────


@dataclass
class Graders:
    name_contains: str | None = None
    min_actions: int = 1
    max_actions: int = 50
    must_contain: list[str] = field(default_factory=list)
    surfaces: list[str] = field(default_factory=list)
    decode_succeeds: bool = True
    recovery_expected: bool = False


@dataclass
class Task:
    id: str
    prompt: str
    graders: Graders

    @classmethod
    def from_file(cls, path: Path) -> Task:
        raw = json.loads(path.read_text())
        return cls(
            id=raw["id"],
            prompt=raw["prompt"],
            graders=Graders(**raw.get("graders", {})),
        )


def load_tasks(task_filter: str | None = None) -> list[Task]:
    files = sorted(_TASKS_DIR.glob("*.json"))
    tasks = [Task.from_file(f) for f in files]
    if task_filter:
        tasks = [t for t in tasks if task_filter in t.id]
    if not tasks:
        raise SystemExit(f"No tasks matched filter {task_filter!r}.")
    return tasks


# ── Result model ─────────────────────────────────────────────────────


@dataclass
class AttemptResult:
    passed: bool
    reason: str
    tool_calls: int
    input_tokens: int
    output_tokens: int
    built_path: str | None
    saw_recovery: bool


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


# ── Tool schema translation ──────────────────────────────────────────


async def _list_anthropic_tools(client: Client) -> list[dict[str, Any]]:
    """Translate the FastMCP server's tools/list into Anthropic's tool schema."""
    tools = await client.list_tools()
    return [
        {
            "name": t.name,
            "description": t.description or "",
            "input_schema": t.inputSchema or {"type": "object", "properties": {}},
        }
        for t in tools
    ]


def _tool_result_text(content: list[Any]) -> str:
    """Render an MCP tool result's content blocks as a single string for Anthropic."""
    parts: list[str] = []
    for block in content:
        text = getattr(block, "text", None)
        if isinstance(text, str):
            parts.append(text)
    return "\n".join(parts) if parts else json.dumps(None)


# ── Agent loop ───────────────────────────────────────────────────────


async def _run_attempt(
    anthropic_client: Anthropic,
    model: str,
    task: Task,
    output_dir: Path,
) -> AttemptResult:
    os.environ["SHORTCUT_LIB_MCP_OUTPUT_DIR"] = str(output_dir)
    server = build_server()
    saw_recovery = False
    tool_calls = 0
    total_in = 0
    total_out = 0
    built_path: str | None = None

    async with Client(server) as mcp_client:
        tools = await _list_anthropic_tools(mcp_client)
        messages: list[dict[str, Any]] = [{"role": "user", "content": task.prompt}]

        for _ in range(_MAX_AGENT_TURNS):
            # Anthropic SDK types `tools` / `messages` as TypedDict unions; the
            # plain dicts we build are structurally identical but ty rejects
            # them. The dicts are right at runtime — silence the false positive
            # rather than threading TypedDicts through every helper.
            response = anthropic_client.messages.create(
                model=model,
                max_tokens=2048,
                system=_SYSTEM_PROMPT,
                tools=tools,  # ty: ignore[invalid-argument-type]
                messages=messages,  # ty: ignore[invalid-argument-type]
            )
            total_in += response.usage.input_tokens
            total_out += response.usage.output_tokens

            messages.append({"role": "assistant", "content": response.content})
            if response.stop_reason != "tool_use":
                break

            tool_uses = [b for b in response.content if b.type == "tool_use"]
            tool_results: list[dict[str, Any]] = []
            for use in tool_uses:
                tool_calls += 1
                try:
                    call_result = await mcp_client.call_tool(use.name, use.input or {})
                    text = _tool_result_text(call_result.content)
                    is_error = bool(call_result.is_error)
                    if use.name == "shortcut_build" and not is_error:
                        sc = call_result.structured_content or {}
                        path_val = sc.get("path")
                        if isinstance(path_val, str):
                            built_path = path_val
                except Exception as exc:
                    text = f"tool {use.name} raised: {exc}"
                    is_error = True
                if is_error:
                    saw_recovery = True
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": use.id,
                        "content": text,
                        "is_error": is_error,
                    }
                )
            messages.append({"role": "user", "content": tool_results})

    passed, reason = _grade(task, output_dir, built_path, saw_recovery)
    return AttemptResult(
        passed=passed,
        reason=reason,
        tool_calls=tool_calls,
        input_tokens=total_in,
        output_tokens=total_out,
        built_path=built_path,
        saw_recovery=saw_recovery,
    )


# ── Grading ──────────────────────────────────────────────────────────


def _grade(
    task: Task,
    output_dir: Path,
    built_path: str | None,
    saw_recovery: bool,
) -> tuple[bool, str]:
    """Return ``(passed, reason)`` for the attempt.

    The agent's emitted ``.shortcut`` file is the source of truth. We decode
    it and check the graders deterministically — no LLM-as-judge.
    """
    candidate = Path(built_path) if built_path else _newest_shortcut(output_dir)
    if candidate is None or not candidate.exists():
        return False, "no .shortcut file produced"

    g = task.graders
    if g.name_contains and g.name_contains.lower() not in candidate.stem.lower():
        return False, (
            f"filename {candidate.stem!r} missing required substring "
            f"{g.name_contains!r}"
        )

    try:
        decoded = decode_file(candidate)
    except DecodeError as exc:
        if g.decode_succeeds:
            return False, f"decode failed: {exc}"
        return True, "decode failed as expected"

    actions = decoded.workflow.get("WFWorkflowActions") or []
    identifiers = [a.get("WFWorkflowActionIdentifier") for a in actions]

    if not (g.min_actions <= len(actions) <= g.max_actions):
        return False, (
            f"action count {len(actions)} outside [{g.min_actions}, {g.max_actions}]"
        )
    missing = [ident for ident in g.must_contain if ident not in identifiers]
    if missing:
        return False, f"missing required action identifiers: {missing}"

    surfaces = decoded.workflow.get("WFWorkflowTypes") or []
    missing_surfaces = [s for s in g.surfaces if s not in surfaces]
    if missing_surfaces:
        return False, f"missing required surfaces: {missing_surfaces}"

    if g.recovery_expected and not saw_recovery:
        return False, "task expected recovery from an error, but none was seen"

    return True, "ok"


def _newest_shortcut(directory: Path) -> Path | None:
    files = sorted(
        directory.glob("*.shortcut"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return files[0] if files else None


# ── Driver ───────────────────────────────────────────────────────────


def _summarise(results: Iterable[TaskResult], k: int) -> dict[str, Any]:
    rs = list(results)
    pass_at_1 = sum(r.attempts[0].passed for r in rs if r.attempts) / max(len(rs), 1)
    pass_at_k = sum(r.passed_any for r in rs) / max(len(rs), 1)
    total_tool_calls = sum(a.tool_calls for r in rs for a in r.attempts)
    total_in = sum(a.input_tokens for r in rs for a in r.attempts)
    total_out = sum(a.output_tokens for r in rs for a in r.attempts)
    return {
        "task_count": len(rs),
        "k": k,
        "pass@1": pass_at_1,
        f"pass@{k}": pass_at_k,
        "tool_calls_total": total_tool_calls,
        "input_tokens_total": total_in,
        "output_tokens_total": total_out,
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
    tasks: list[Task], *, k: int, model: str, output_root: Path
) -> list[TaskResult]:
    anthropic_client = Anthropic()
    results: list[TaskResult] = []
    for task in tasks:
        attempts: list[AttemptResult] = []
        for attempt_idx in range(k):
            with tempfile.TemporaryDirectory(
                prefix=f"{task.id}-{attempt_idx}-", dir=output_root
            ) as td:
                attempt = await _run_attempt(anthropic_client, model, task, Path(td))
            attempts.append(attempt)
            verdict = "PASS" if attempt.passed else "FAIL"
            print(
                f"[{task.id}] attempt {attempt_idx + 1}/{k}: {verdict} — "
                f"{attempt.reason} (tool_calls={attempt.tool_calls}, "
                f"tokens={attempt.input_tokens}+{attempt.output_tokens})"
            )
        results.append(TaskResult(id=task.id, attempts=attempts))
    return results


def _dry_run(tasks: list[Task]) -> int:
    """Validate task JSON files and exit; no API calls."""
    for task in tasks:
        print(f"[{task.id}] prompt={task.prompt[:60]}…")
        print(
            f"           graders={task.graders.must_contain} "
            f"actions=[{task.graders.min_actions},{task.graders.max_actions}]"
        )
    print(f"\n{len(tasks)} task(s) validated.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--k", type=int, default=1, help="attempts per task")
    parser.add_argument("--task", type=str, default=None, help="substring filter")
    parser.add_argument("--model", type=str, default=_DEFAULT_MODEL)
    parser.add_argument(
        "--dry-run", action="store_true", help="validate tasks only; no API calls"
    )
    args = parser.parse_args()

    tasks = load_tasks(args.task)

    if args.dry_run:
        return _dry_run(tasks)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY not set; pass --dry-run to validate tasks only.")
        return 2

    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mcp-evals-") as scratch_root:
        results = asyncio.run(
            _run_all(tasks, k=args.k, model=args.model, output_root=Path(scratch_root))
        )

    summary = _summarise(results, k=args.k)
    summary["model"] = args.model
    summary["timestamp"] = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
    out_path = _RESULTS_DIR / f"{summary['timestamp']}.json"
    out_path.write_text(json.dumps(summary, indent=2))
    print(f"\nWrote {out_path}")
    print(
        f"pass@1={summary['pass@1']:.2%}  "
        f"pass@{args.k}={summary[f'pass@{args.k}']:.2%}  "
        f"tool_calls={summary['tool_calls_total']}  "
        f"tokens={summary['input_tokens_total']}+{summary['output_tokens_total']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
