"""Pure-stdlib statistics helpers for the MCP eval harness.

No numpy or scipy: the harness ships with a thin dependency surface, so the
estimators here lean on :mod:`random`, :mod:`math`, and :mod:`statistics`
only. Everything is deterministic given an explicit seed so two runs over the
same per-task scores produce identical confidence intervals.
"""

from __future__ import annotations

import math
import random
import statistics


def bootstrap_ci(
    per_task_scores: list[float],
    confidence: float = 0.95,
    n_boot: int = 10000,
    seed: int = 0,
) -> tuple[float, float]:
    """Percentile bootstrap CI over per-task pass-rates.

    Tasks are the resampling unit (the clusters): attempts within a task are
    not independent, so we resample whole tasks with replacement and take the
    mean of each resample. This gives a task-level interval, which is the
    honest unit for a small task suite.

    Args:
        per_task_scores: One pass-rate per task, each in ``[0, 1]``.
        confidence: Central mass of the interval, e.g. ``0.95``.
        n_boot: Number of bootstrap resamples.
        seed: RNG seed for reproducibility.

    Returns:
        A ``(lo, hi)`` tuple of percentile bounds. Returns ``(0.0, 0.0)`` for
        an empty input and a degenerate ``(score, score)`` for a single task.
    """
    if not per_task_scores:
        return 0.0, 0.0
    if len(per_task_scores) == 1:
        only = per_task_scores[0]
        return only, only

    rng = random.Random(seed)  # noqa: S311 (statistical bootstrap, not crypto)
    n = len(per_task_scores)
    means: list[float] = []
    for _ in range(n_boot):
        resample = [rng.choice(per_task_scores) for _ in range(n)]
        means.append(statistics.fmean(resample))
    means.sort()

    tail = (1.0 - confidence) / 2.0
    lo = _percentile(means, tail)
    hi = _percentile(means, 1.0 - tail)
    return lo, hi


def _percentile(sorted_values: list[float], q: float) -> float:
    """Return the ``q`` quantile of an already-sorted list via interpolation."""
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    pos = q * (len(sorted_values) - 1)
    lower = math.floor(pos)
    upper = math.ceil(pos)
    if lower == upper:
        return sorted_values[lower]
    frac = pos - lower
    return sorted_values[lower] * (1.0 - frac) + sorted_values[upper] * frac


def pass_at_k_unbiased(successes: int, n: int, k: int) -> float:
    """Unbiased pass@k estimator from the HumanEval / Codex paper.

    Computes ``1 - C(n - c, k) / C(n, k)`` where ``c`` is the number of
    successful attempts out of ``n`` total. This is the probability that at
    least one of ``k`` attempts sampled without replacement succeeds.

    Args:
        successes: Number of passing attempts (``c``).
        n: Total attempts.
        k: Sample size for the pass@k estimate.

    Returns:
        The estimated pass@k in ``[0, 1]``. Returns ``1.0`` when there are
        too few failures to draw ``k`` all-failing attempts (``n - c < k``).
    """
    if n - successes < k:
        return 1.0
    return 1.0 - math.comb(n - successes, k) / math.comb(n, k)


def pass_hat_k(p: float, k: int) -> float:
    """Reliability metric ``p ** k``.

    The probability that ``k`` independent attempts at per-attempt success
    rate ``p`` all pass. A pessimistic companion to the pass@k estimator:
    where pass@k rewards getting it right once, pass^k rewards getting it
    right every time.

    Args:
        p: Per-attempt success probability in ``[0, 1]``.
        k: Number of attempts.

    Returns:
        ``p ** k``.
    """
    return p**k
