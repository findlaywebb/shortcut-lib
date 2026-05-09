"""Tests for Shortcut Setup (WFWorkflowImportQuestions) authoring API.

Covers:
- ask_text_on_import sugar
- ask_on_import for arbitrary action/parameter combinations
- DefaultValue omission when default=None
- Error path: question targeting an action not add()ed to the shortcut
- Lift round-trip fidelity for start_pomodoro (the UUID-less action case)
- ActionIndex correctness when a control-flow construct precedes the target
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shortcut_lib import decode_file
from shortcut_lib.builder import Shortcut
from shortcut_lib.schema.actions.show_notification import ShowNotification
from shortcut_lib.schema.base import SchemaError
from shortcut_lib.schema.control import If

SAMPLES_DIR = Path(__file__).parent.parent / "samples"


def test_ask_text_on_import_emits_question() -> None:
    """ask_text_on_import adds a GetText and emits one ImportQuestion entry."""
    s = Shortcut(name="Test")
    s.ask_text_on_import("Your token?", default="mydefault")

    workflow = s.to_workflow()
    questions = workflow["WFWorkflowImportQuestions"]

    assert len(questions) == 1
    q = questions[0]
    assert q["Category"] == "Parameter"
    assert q["ParameterKey"] == "WFTextActionText"
    assert q["Text"] == "Your token?"
    assert q["DefaultValue"] == "mydefault"
    # ActionIndex 0 — it's the first (and only) action.
    assert q["ActionIndex"] == 0


def test_ask_on_import_targets_arbitrary_action() -> None:
    """ask_on_import emits a question targeting any action's parameter slot."""
    s = Shortcut(name="Test")
    notif = s.add(ShowNotification(title="Hello"))
    s.ask_on_import(
        action=notif,
        parameter_key="WFNotificationActionTitle",
        question="What title?",
        default="My Title",
    )

    workflow = s.to_workflow()
    questions = workflow["WFWorkflowImportQuestions"]

    assert len(questions) == 1
    q = questions[0]
    assert q["ParameterKey"] == "WFNotificationActionTitle"
    assert q["Text"] == "What title?"
    assert q["DefaultValue"] == "My Title"
    # ShowNotification is the first (and only) action — index 0.
    assert q["ActionIndex"] == 0


def test_setup_question_default_omitted_when_none() -> None:
    """Passing default=None must not emit a DefaultValue key."""
    s = Shortcut(name="Test")
    notif = s.add(ShowNotification(title="Hi"))
    s.ask_on_import(
        action=notif,
        parameter_key="WFNotificationActionTitle",
        question="Title?",
        default=None,
    )

    workflow = s.to_workflow()
    q = workflow["WFWorkflowImportQuestions"][0]
    assert "DefaultValue" not in q


def test_setup_question_unregistered_action_raises() -> None:
    """Registering a question against an action not add()ed must raise SchemaError."""
    s = Shortcut(name="Test")
    orphan = ShowNotification(title="Orphan")
    # Deliberately do NOT add orphan to the shortcut.
    s.ask_on_import(
        action=orphan,
        parameter_key="WFNotificationActionTitle",
        question="Will this raise?",
    )

    with pytest.raises(SchemaError, match="not present in this Shortcut"):
        s.to_workflow()


def test_lift_setup_question_round_trip_start_pomodoro() -> None:
    """Lift→emit must preserve WFWorkflowImportQuestions for start_pomodoro.

    start_pomodoro's dnd.set action (ActionIndex=9) has NO UUID key in its
    plist — this test guards the identity-based lookup fix that replaced the
    old UUID-based approach.
    """
    sample = SAMPLES_DIR / "start_pomodoro.shortcut"
    original = decode_file(sample).workflow
    lifted = Shortcut.from_workflow(original)
    re_emitted = lifted.to_workflow()

    orig_questions = original.get("WFWorkflowImportQuestions", [])
    emitted_questions = re_emitted.get("WFWorkflowImportQuestions", [])

    assert len(emitted_questions) == len(orig_questions)
    for orig_q, emit_q in zip(orig_questions, emitted_questions, strict=True):
        # Compare key-by-key (order-independent).
        assert set(orig_q.keys()) == set(emit_q.keys()), (
            f"key mismatch: original has {set(orig_q.keys())}, "
            f"emitted has {set(emit_q.keys())}"
        )
        for key in orig_q:
            assert emit_q[key] == orig_q[key], (
                f"key {key!r}: expected {orig_q[key]!r}, got {emit_q[key]!r}"
            )


def test_action_index_after_control_flow() -> None:
    """ActionIndex must reflect the post-expansion position of a leaf action.

    An If(...) expands to at minimum 3 flat entries (head + else-marker +
    end-marker when otherwise is empty, or head + then-body + end-marker
    when otherwise is absent). A leaf action added *after* the If must
    have its ActionIndex shifted by the full expansion count.
    """
    s = Shortcut(name="Test")
    # If with one action in the then-branch and no otherwise:
    # Emits: [if-head, then-action, if-end] → 3 flat entries at indices 0,1,2.
    inner = ShowNotification(title="Inside")
    if_block = s.add(If(operand="x", op="==", value="x", then=[inner]))
    # A second top-level leaf action: flat index should be 3.
    notif = s.add(ShowNotification(title="After"))
    s.ask_on_import(
        action=notif,
        parameter_key="WFNotificationActionTitle",
        question="After the if?",
    )

    workflow = s.to_workflow()
    actions_flat = workflow["WFWorkflowActions"]
    questions = workflow["WFWorkflowImportQuestions"]

    # The If block (no otherwise branch) emits 3 entries.
    # The notif lands at flat index 3.
    expected_index = 3
    assert len(actions_flat) >= expected_index + 1
    assert questions[0]["ActionIndex"] == expected_index

    # Sanity: the action at that index is the ShowNotification.
    target_dict = actions_flat[expected_index]
    assert (
        target_dict["WFWorkflowActionIdentifier"] == "is.workflow.actions.notification"
    )
    # And the If head is at index 0.
    _ = if_block  # used only for construction; avoid unused-variable lint.
