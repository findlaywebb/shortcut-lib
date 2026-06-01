"""Unit tests for the MCP eval harness pure logic.

Covers the deterministic graders (`expect_no_build`, `must_not_contain`) and
the stdlib stats helpers. No Anthropic/OpenAI API calls and no shortcut
signing: the grader tests stub `decode_file` so the branch logic is exercised
without the macOS signing CLI.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("fastmcp", reason="evals require [mcp] extra")

# The evals dir is not an installed package; add it so the harness modules
# import the same way the driver does.
_EVALS_MCP = Path(__file__).resolve().parents[1] / "evals" / "mcp"
sys.path.insert(0, str(_EVALS_MCP))

import _grading  # noqa: E402  # ty: ignore[unresolved-import]
import _stats  # noqa: E402  # ty: ignore[unresolved-import]
from _grading import Graders, Task, grade  # noqa: E402  # ty: ignore[unresolved-import]

# ── Helpers ──────────────────────────────────────────────────────────


def _task(graders: Graders) -> Task:
    return Task(id="t", prompt="p", graders=graders)


def _fake_workflow(*identifiers: str) -> dict[str, Any]:
    """A minimal decoded workflow dict carrying the given action identifiers."""
    return {
        "WFWorkflowActions": [
            {"WFWorkflowActionIdentifier": ident} for ident in identifiers
        ]
    }


def _stub_decode(
    monkeypatch: pytest.MonkeyPatch,
    *identifiers: str,
    surfaces: list[str] | None = None,
) -> None:
    """Patch _grading.decode_file to return a workflow with the given actions."""
    workflow = _fake_workflow(*identifiers)
    if surfaces is not None:
        workflow["WFWorkflowTypes"] = surfaces

    class _Decoded:
        def __init__(self) -> None:
            self.workflow = workflow

    monkeypatch.setattr(_grading, "decode_file", lambda _path: _Decoded())


def _touch_shortcut(tmp_path: Path, name: str = "Clip Hello") -> Path:
    """Write a placeholder .shortcut file so candidate.exists() is true."""
    path = tmp_path / f"{name}.shortcut"
    path.write_bytes(b"stub")
    return path


# ── expect_no_build ──────────────────────────────────────────────────


def test_expect_no_build_passes_when_no_file(tmp_path: Path) -> None:
    task = _task(Graders(expect_no_build=True))
    passed, reason = grade(task, tmp_path, built_path=None, saw_recovery=False)
    assert passed
    assert "refused" in reason.lower()


def test_expect_no_build_fails_when_file_exists(tmp_path: Path) -> None:
    built = _touch_shortcut(tmp_path)
    task = _task(Graders(expect_no_build=True))
    passed, reason = grade(task, tmp_path, built_path=str(built), saw_recovery=False)
    assert not passed
    assert "expected refusal" in reason


def test_expect_no_build_detects_unreported_file(tmp_path: Path) -> None:
    # A file landed in output_dir even though built_path was never reported.
    _touch_shortcut(tmp_path)
    task = _task(Graders(expect_no_build=True))
    passed, _ = grade(task, tmp_path, built_path=None, saw_recovery=False)
    assert not passed


# ── must_not_contain ─────────────────────────────────────────────────


def test_must_not_contain_fails_on_forbidden(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_decode(monkeypatch, "is.workflow.actions.setclipboard")
    built = _touch_shortcut(tmp_path)
    task = _task(Graders(must_not_contain=["is.workflow.actions.setclipboard"]))
    passed, reason = grade(task, tmp_path, built_path=str(built), saw_recovery=False)
    assert not passed
    assert "forbidden" in reason
    assert "setclipboard" in reason


def test_must_not_contain_passes_when_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _stub_decode(monkeypatch, "is.workflow.actions.setclipboard")
    built = _touch_shortcut(tmp_path)
    task = _task(Graders(must_not_contain=["is.workflow.actions.notification"]))
    passed, reason = grade(task, tmp_path, built_path=str(built), saw_recovery=False)
    assert passed
    assert reason == "ok"


def test_must_not_contain_checked_after_must_contain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A missing required action fails before the forbidden check runs.
    _stub_decode(monkeypatch, "is.workflow.actions.setclipboard")
    built = _touch_shortcut(tmp_path)
    task = _task(
        Graders(
            must_contain=["is.workflow.actions.notification"],
            must_not_contain=["is.workflow.actions.setclipboard"],
        )
    )
    passed, reason = grade(task, tmp_path, built_path=str(built), saw_recovery=False)
    assert not passed
    assert "missing required" in reason


# ── _stats: pass_at_k_unbiased ───────────────────────────────────────


def test_pass_at_k_unbiased_known_value() -> None:
    # 6 of 10 succeed, k=8: n-c=4 < 8, estimator returns 1.0.
    assert _stats.pass_at_k_unbiased(6, 10, 8) == 1.0


def test_pass_at_k_unbiased_partial() -> None:
    # 2 of 5 succeed, k=2: 1 - C(3,2)/C(5,2) = 1 - 3/10 = 0.7.
    assert _stats.pass_at_k_unbiased(2, 5, 2) == pytest.approx(0.7)


def test_pass_at_k_unbiased_k1_equals_rate() -> None:
    # At k=1 the estimator is just c/n.
    assert _stats.pass_at_k_unbiased(3, 10, 1) == pytest.approx(0.3)


def test_pass_at_k_unbiased_all_fail() -> None:
    assert _stats.pass_at_k_unbiased(0, 5, 3) == 0.0


# ── _stats: pass_hat_k ───────────────────────────────────────────────


def test_pass_hat_k_value() -> None:
    assert _stats.pass_hat_k(0.6, 2) == pytest.approx(0.36)


def test_pass_hat_k_k1_identity() -> None:
    assert _stats.pass_hat_k(0.42, 1) == pytest.approx(0.42)


# ── _stats: bootstrap_ci ─────────────────────────────────────────────


def test_bootstrap_ci_brackets_mean() -> None:
    scores = [0.0, 0.5, 1.0, 0.5, 0.75, 0.25]
    mean = sum(scores) / len(scores)
    lo, hi = _stats.bootstrap_ci(scores, seed=0)
    assert lo <= mean <= hi


def test_bootstrap_ci_is_deterministic() -> None:
    scores = [0.2, 0.4, 0.6, 0.8, 1.0]
    assert _stats.bootstrap_ci(scores, seed=7) == _stats.bootstrap_ci(scores, seed=7)


def test_bootstrap_ci_single_task_is_degenerate() -> None:
    assert _stats.bootstrap_ci([0.5]) == (0.5, 0.5)


def test_bootstrap_ci_empty() -> None:
    assert _stats.bootstrap_ci([]) == (0.0, 0.0)
