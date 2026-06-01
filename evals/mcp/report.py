"""Cross-provider comparison report for MCP eval runs.

Reads ``evals/mcp/results/*.json``, keeps the latest run per (provider,
model), and prints a markdown comparison table plus a paired bootstrap delta
of each non-baseline model against a baseline. JSON only, no API calls.

Usage::

    uv run python evals/mcp/report.py
    uv run python evals/mcp/report.py --baseline claude-sonnet-4-6
    uv run python evals/mcp/report.py --floor-k 3
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

# The evals dir is not an installed package; add it to the path so _stats
# imports cleanly whether this file runs as a script or under a test.
sys.path.insert(0, str(Path(__file__).parent))
import _stats  # ty: ignore[unresolved-import]

_RESULTS_DIR = Path(__file__).parent / "results"
_DEFAULT_BASELINE = "claude-sonnet-4-6"
# Common floor k: recompute the unbiased pass@k at this k for every run so an
# OpenAI k=10 run is comparable to an Anthropic k=3 run.
_DEFAULT_FLOOR_K = 3


def _load_latest() -> dict[tuple[str, str, str], dict[str, Any]]:
    """Return the latest result per (provider, model, effort) keyed by triple.

    Reasoning effort is part of the key so an OpenAI sweep (the same model at
    low / medium / high) yields one row per effort rather than collapsing.
    The timestamp field orders runs; the lexicographic UTC stamp sorts the
    same as chronological order, so the max wins.
    """
    latest: dict[tuple[str, str, str], dict[str, Any]] = {}
    for path in sorted(_RESULTS_DIR.glob("*.json")):
        data = json.loads(path.read_text())
        model = data.get("model", "?")
        provider = data.get("provider", "anthropic")
        effort = data.get("reasoning_effort", "none")
        key = (provider, model, effort)
        stamp = data.get("timestamp", path.stem)
        current = latest.get(key)
        if current is None or stamp >= current.get("timestamp", ""):
            data["timestamp"] = stamp
            latest[key] = data
    return latest


def _per_task_rates(run: dict[str, Any]) -> list[float]:
    """Pull the per-task pass-rates from a run summary."""
    return [t["pass_rate"] for t in run.get("tasks", [])]


def _floor_pass_at_k(run: dict[str, Any], floor_k: int) -> float:
    """Recompute the unbiased pass@k at the common floor for one run.

    Averages each task's ``1 - C(n-c, floor_k)/C(n, floor_k)`` so runs at
    different k are comparable. Tasks with fewer than ``floor_k`` attempts
    contribute their available-k estimate (the estimator returns 1.0 when it
    cannot draw enough failures).
    """
    tasks = run.get("tasks", [])
    if not tasks:
        return 0.0
    total = 0.0
    for t in tasks:
        attempts = t.get("attempts", [])
        n = len(attempts)
        successes = sum(1 for a in attempts if a.get("passed"))
        total += _stats.pass_at_k_unbiased(successes, n, min(floor_k, n))
    return total / len(tasks)


def _format_row(
    provider: str, model: str, effort: str, run: dict[str, Any], floor_k: int
) -> str:
    """Render one table row for a model's latest run."""
    k = run.get("k", 1)
    n_tasks = run.get("task_count", 0)
    p1 = run.get("pass@1", 0.0)
    lo = run.get("pass@1_ci_low", 0.0)
    hi = run.get("pass@1_ci_high", 0.0)
    floor_pk = _floor_pass_at_k(run, floor_k)
    p_overall = run.get("pass_hat_k", 0.0)
    tokens = run.get("tokens_per_task", 0.0)
    calls = run.get("tool_calls_per_task", 0.0)
    commit = run.get("git_commit") or "?"
    dirty = "*" if run.get("git_dirty") else ""
    return (
        f"| {model} | {provider} | {effort} | {k} | {n_tasks} | "
        f"{p1:.0%} [{lo:.0%}, {hi:.0%}] | {floor_pk:.0%} | {p_overall:.2f} | "
        f"{tokens:,.0f} | {calls:.1f} | {commit}{dirty} |"
    )


def _print_table(
    latest: dict[tuple[str, str, str], dict[str, Any]], floor_k: int
) -> None:
    """Print the markdown comparison table."""
    print(
        f"| model | provider | effort | k | n_tasks | pass@1 [95% CI] | "
        f"pass@{floor_k} (est) | pass^{floor_k} | tokens/task | "
        f"tool_calls/task | git_commit |"
    )
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for (provider, model, effort), run in sorted(latest.items()):
        print(_format_row(provider, model, effort, run, floor_k))


def _paired_delta(
    baseline: list[float], other: list[float], seed: int = 0, n_boot: int = 10000
) -> tuple[float, float, float]:
    """Paired bootstrap of per-task pass-rate deltas (other minus baseline).

    Tasks are the resampling unit and the two models are paired per task, so
    we resample task indices and take the mean of the paired differences.

    Returns:
        ``(mean_delta, ci_low, ci_high)``.
    """
    diffs = [o - b for o, b in zip(other, baseline, strict=False)]
    if not diffs:
        return 0.0, 0.0, 0.0
    mean_delta = sum(diffs) / len(diffs)
    rng = random.Random(seed)  # noqa: S311 (statistical bootstrap, not crypto)
    n = len(diffs)
    means: list[float] = []
    for _ in range(n_boot):
        sample = [rng.choice(diffs) for _ in range(n)]
        means.append(sum(sample) / n)
    means.sort()
    lo = means[int(0.025 * (len(means) - 1))]
    hi = means[int(0.975 * (len(means) - 1))]
    return mean_delta, lo, hi


def _print_deltas(
    latest: dict[tuple[str, str, str], dict[str, Any]], baseline_model: str
) -> None:
    """Print paired bootstrap deltas of each non-baseline run vs baseline.

    The baseline is matched by model name (its own effort row is skipped from
    the delta list). Every other run, including each OpenAI effort level, is
    compared against it. Paired bootstrap is only valid when both runs cover
    the same task set, so a run with a different task count is skipped.
    """
    baseline_runs = [
        run for (_, model, _), run in latest.items() if model == baseline_model
    ]
    if not baseline_runs:
        print(f"\n(no baseline run for {baseline_model!r}; skipping deltas)")
        return
    baseline_rates = _per_task_rates(baseline_runs[0])

    print(f"\n### Paired delta vs baseline ({baseline_model})\n")
    print("| model | provider | effort | mean delta | 95% CI | excludes 0 |")
    print("|---|---|---|---|---|---|")
    for (provider, model, effort), run in sorted(latest.items()):
        if model == baseline_model:
            continue
        other_rates = _per_task_rates(run)
        if len(other_rates) != len(baseline_rates):
            print(
                f"| {model} | {provider} | {effort} | n/a "
                f"(task set differs) | n/a | n/a |"
            )
            continue
        mean_delta, lo, hi = _paired_delta(baseline_rates, other_rates)
        excludes = "yes" if (lo > 0 or hi < 0) else "no"
        print(
            f"| {model} | {provider} | {effort} | {mean_delta:+.0%} | "
            f"[{lo:+.0%}, {hi:+.0%}] | {excludes} |"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=str, default=_DEFAULT_BASELINE)
    parser.add_argument(
        "--floor-k",
        type=int,
        default=_DEFAULT_FLOOR_K,
        help="common floor k for the comparable pass@k estimator",
    )
    args = parser.parse_args()

    latest = _load_latest()
    if not latest:
        print(f"No result files in {_RESULTS_DIR}.")
        return 1

    _print_table(latest, args.floor_k)
    _print_deltas(latest, args.baseline)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
