"""Snapshot test for the buzz summary format."""

from __future__ import annotations

from pathlib import Path

from shortcut_lib import decode_file
from shortcut_lib.summary import workflow_to_summary

SAMPLES = Path(__file__).parent.parent / "samples"
SNAPSHOTS = Path(__file__).parent / "snapshots"


def test_start_pomodoro_jelly_snapshot() -> None:
    """The summary output for the canonical sample stays stable.

    Update via: ``uv run shortcut-decode samples/start_pomodoro.shortcut
    --format buzz -o tests/snapshots/start_pomodoro.buzz``.
    """
    actual = workflow_to_summary(
        decode_file(SAMPLES / "start_pomodoro.shortcut").workflow
    )
    expected = (SNAPSHOTS / "start_pomodoro.buzz").read_text()
    assert actual == expected


def _make_action(identifier: str, **params: object) -> dict[str, object]:
    """Build a minimal WFWorkflowActions entry for unit testing."""
    import uuid
    from typing import Any

    p: dict[str, Any] = {"UUID": str(uuid.uuid4()).upper()}
    p.update(params)
    return {"WFWorkflowActionIdentifier": identifier, "WFWorkflowActionParameters": p}


def _workflow(*actions: dict) -> dict:
    return {"WFWorkflowActions": list(actions)}


# ---------------------------------------------------------------------------
# for-each head
# ---------------------------------------------------------------------------


def test_summary_for_each_head() -> None:
    action = _make_action(
        "is.workflow.actions.repeat.each",
        WFControlFlowMode=0,
        WFInput={
            "Type": "Variable",
            "Variable": {
                "Value": {"VariableName": "MyList", "Type": "Variable"},
                "WFSerializationType": "WFTextTokenAttachment",
            },
        },
    )
    close = _make_action(
        "is.workflow.actions.repeat.each",
        WFControlFlowMode=2,
    )
    summary = workflow_to_summary(_workflow(action, close))
    assert "for each in" in summary
    assert "end for-each" in summary


# ---------------------------------------------------------------------------
# repeat head
# ---------------------------------------------------------------------------


def test_summary_repeat_head() -> None:
    action = _make_action(
        "is.workflow.actions.repeat.count",
        WFControlFlowMode=0,
        WFRepeatCount=5,
    )
    close = _make_action(
        "is.workflow.actions.repeat.count",
        WFControlFlowMode=2,
    )
    summary = workflow_to_summary(_workflow(action, close))
    assert "repeat 5 times" in summary
    assert "end repeat" in summary


# ---------------------------------------------------------------------------
# menu: head, case marker, and end
# ---------------------------------------------------------------------------


def test_summary_menu_case() -> None:
    head = _make_action(
        "is.workflow.actions.choosefrommenu",
        WFControlFlowMode=0,
        WFMenuPrompt="Choose",
        WFMenuItems=["Option A", "Option B"],
    )
    case_a = _make_action(
        "is.workflow.actions.choosefrommenu",
        WFControlFlowMode=1,
        WFMenuItemTitle="Option A",
    )
    close = _make_action(
        "is.workflow.actions.choosefrommenu",
        WFControlFlowMode=2,
    )
    summary = workflow_to_summary(_workflow(head, case_a, close))
    assert "menu" in summary
    assert "case" in summary
    assert "Option A" in summary
    assert "end menu" in summary


# ---------------------------------------------------------------------------
# if / else / end
# ---------------------------------------------------------------------------


def test_summary_if_else() -> None:
    from shortcut_lib.schema.control import WFCondition

    head = _make_action(
        "is.workflow.actions.conditional",
        WFControlFlowMode=0,
        WFCondition=int(WFCondition.EQ),
        WFConditionalActionString="hello",
        WFInput={
            "Type": "Variable",
            "Variable": {"VariableName": "X", "Type": "Variable"},
        },
    )
    else_marker = _make_action(
        "is.workflow.actions.conditional",
        WFControlFlowMode=1,
    )
    close = _make_action(
        "is.workflow.actions.conditional",
        WFControlFlowMode=2,
    )
    summary = workflow_to_summary(_workflow(head, else_marker, close))
    assert "if" in summary
    assert "else" in summary
    assert "end if" in summary


def test_summary_compact() -> None:
    """Sanity: the summary should be markedly smaller than the XML plist."""
    import plistlib

    decoded = decode_file(SAMPLES / "start_pomodoro.shortcut")
    summary = workflow_to_summary(decoded.workflow)
    xml = plistlib.dumps(decoded.workflow, fmt=plistlib.FMT_XML).decode()
    # 5x is a conservative floor; in practice we see ~7-10x.
    assert len(xml) > 5 * len(summary), (
        f"summary not compact enough: xml={len(xml)} summary={len(summary)}"
    )
