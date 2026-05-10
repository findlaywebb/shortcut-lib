"""Tests for SetDoNotDisturb (is.workflow.actions.dnd.set) action schema."""

from __future__ import annotations

import shortcut_lib.schema.actions.set_focus  # noqa: F401 — trigger registration
from shortcut_lib.schema.actions.set_focus import SetDoNotDisturb
from shortcut_lib.schema.registry import lookup
from shortcut_lib.schema.values import NamedVar, Output

# ---------------------------------------------------------------------------
# Identifier / registry
# ---------------------------------------------------------------------------


def test_set_focus_identifier() -> None:
    """to_action_dict carries the Apple dnd.set identifier."""
    action = SetDoNotDisturb()
    d = action.to_action_dict()
    assert d["WFWorkflowActionIdentifier"] == "is.workflow.actions.dnd.set"


def test_set_focus_registered() -> None:
    """SetDoNotDisturb is discoverable in the registry by its identifier."""
    cls = lookup("is.workflow.actions.dnd.set")
    assert cls is SetDoNotDisturb


# ---------------------------------------------------------------------------
# Empty params — valid corpus shape (dictionary.xml appearance)
# ---------------------------------------------------------------------------


def test_set_focus_empty_params_valid() -> None:
    """No-arg constructor emits only UUID — matches dictionary.xml wire shape."""
    action = SetDoNotDisturb()
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    # Only UUID should be present (the base class always injects it).
    assert set(params.keys()) == {"UUID"}


# ---------------------------------------------------------------------------
# enabled key — integer 1 / 0 encoding
# ---------------------------------------------------------------------------


def test_set_focus_enabled_true_emits_integer_1() -> None:
    """enabled=True emits Enabled: 1 (integer, not boolean string)."""
    params = SetDoNotDisturb(enabled=True).to_action_dict()[
        "WFWorkflowActionParameters"
    ]
    assert params["Enabled"] == 1
    assert isinstance(params["Enabled"], int)


def test_set_focus_enabled_false_emits_integer_0() -> None:
    """enabled=False emits Enabled: 0."""
    params = SetDoNotDisturb(enabled=False).to_action_dict()[
        "WFWorkflowActionParameters"
    ]
    assert params["Enabled"] == 0
    assert isinstance(params["Enabled"], int)


def test_set_focus_enabled_none_omits_key() -> None:
    """enabled=None (default) omits the Enabled key."""
    params = SetDoNotDisturb().to_action_dict()["WFWorkflowActionParameters"]
    assert "Enabled" not in params


# ---------------------------------------------------------------------------
# assertion_type
# ---------------------------------------------------------------------------


def test_set_focus_assertion_type_emitted() -> None:
    """AssertionType is emitted verbatim — corpus value 'Time'."""
    params = SetDoNotDisturb(assertion_type="Time").to_action_dict()[
        "WFWorkflowActionParameters"
    ]
    assert params["AssertionType"] == "Time"


def test_set_focus_assertion_type_none_omitted() -> None:
    """assertion_type=None (default) omits the AssertionType key."""
    params = SetDoNotDisturb().to_action_dict()["WFWorkflowActionParameters"]
    assert "AssertionType" not in params


# ---------------------------------------------------------------------------
# focus_modes — plain dict (no WF envelope), from start_pomodoro.xml
# ---------------------------------------------------------------------------


def test_set_focus_modes_dict_emitted() -> None:
    """FocusModes is emitted as a plain dict (no WF envelope)."""
    fm = {"DisplayString": "Work", "Identifier": "com.apple.focus.work"}
    params = SetDoNotDisturb(focus_modes=fm).to_action_dict()[
        "WFWorkflowActionParameters"
    ]
    assert params["FocusModes"] == fm


def test_set_focus_modes_none_omitted() -> None:
    """focus_modes=None (default) omits the FocusModes key."""
    params = SetDoNotDisturb().to_action_dict()["WFWorkflowActionParameters"]
    assert "FocusModes" not in params


# ---------------------------------------------------------------------------
# until — WFTextTokenString envelope for variable refs
# ---------------------------------------------------------------------------


def test_set_focus_until_named_var_rewrapped_as_token_string() -> None:
    """until= with a NamedVar is emitted as WFTextTokenString (Time key).

    start_pomodoro.xml wraps even single ActionOutput refs in
    WFTextTokenString for the Time slot — this test verifies that
    NamedVar goes through the same rewrap path.
    """
    var = NamedVar("Break End Time")
    params = SetDoNotDisturb(until=var).to_action_dict()["WFWorkflowActionParameters"]
    assert "Time" in params
    t = params["Time"]
    assert t["WFSerializationType"] == "WFTextTokenString"
    inner = t["Value"]
    assert "string" in inner
    assert "￼" in inner["string"]
    assert "{0, 1}" in inner["attachmentsByRange"]
    token = inner["attachmentsByRange"]["{0, 1}"]
    assert token["Type"] == "Variable"
    assert token["VariableName"] == "Break End Time"


def test_set_focus_until_action_output_rewrapped_as_token_string() -> None:
    """until= with an Output is emitted as WFTextTokenString (not WFTextTokenAttachment)."""
    ref = Output(uuid="3776F881-73AB-4A82-961F-7AEC4563A72B", name="Break End Time")
    params = SetDoNotDisturb(until=ref).to_action_dict()["WFWorkflowActionParameters"]
    t = params["Time"]
    assert t["WFSerializationType"] == "WFTextTokenString"
    inner = t["Value"]
    token = inner["attachmentsByRange"]["{0, 1}"]
    assert token["OutputUUID"] == "3776F881-73AB-4A82-961F-7AEC4563A72B"
    assert token["OutputName"] == "Break End Time"
    assert token["Type"] == "ActionOutput"


def test_set_focus_until_none_omits_time_key() -> None:
    """until=None omits the Time key."""
    params = SetDoNotDisturb().to_action_dict()["WFWorkflowActionParameters"]
    assert "Time" not in params


# ---------------------------------------------------------------------------
# event — WFTextTokenAttachment (single-var slot)
# ---------------------------------------------------------------------------


def test_set_focus_event_named_var_emitted_as_attachment() -> None:
    """event= with a NamedVar emits Event as WFTextTokenAttachment."""
    var = NamedVar("Break End Time")
    params = SetDoNotDisturb(event=var).to_action_dict()["WFWorkflowActionParameters"]
    assert "Event" in params
    ev = params["Event"]
    assert ev["WFSerializationType"] == "WFTextTokenAttachment"
    assert ev["Value"]["Type"] == "Variable"
    assert ev["Value"]["VariableName"] == "Break End Time"


def test_set_focus_event_none_omits_key() -> None:
    """event=None (default) omits the Event key."""
    params = SetDoNotDisturb().to_action_dict()["WFWorkflowActionParameters"]
    assert "Event" not in params


# ---------------------------------------------------------------------------
# Wire-format equivalence vs corpus — start_pomodoro.xml appearance
# ---------------------------------------------------------------------------


def test_set_focus_wire_equivalence_corpus_shape() -> None:
    """Reproduces the full wire shape from start_pomodoro.xml (rich params).

    Corpus wire keys observed:
        AssertionType = "Time"
        Enabled = 1 (integer)
        Event = WFTextTokenAttachment (ActionOutput)
        FocusModes = {DisplayString: "Work", Identifier: "com.apple.focus.work"}
        Time = WFTextTokenString (ActionOutput in attachmentsByRange)
    """
    ref = Output(uuid="3776F881-73AB-4A82-961F-7AEC4563A72B", name="Break End Time")
    action = SetDoNotDisturb(
        enabled=True,
        assertion_type="Time",
        focus_modes={"DisplayString": "Work", "Identifier": "com.apple.focus.work"},
        until=ref,
        event=ref,
    )
    params = action.to_action_dict()["WFWorkflowActionParameters"]

    assert params["Enabled"] == 1
    assert params["AssertionType"] == "Time"
    assert params["FocusModes"] == {
        "DisplayString": "Work",
        "Identifier": "com.apple.focus.work",
    }

    time_val = params["Time"]
    assert time_val["WFSerializationType"] == "WFTextTokenString"
    attachment = time_val["Value"]["attachmentsByRange"]["{0, 1}"]
    assert attachment["OutputUUID"] == "3776F881-73AB-4A82-961F-7AEC4563A72B"
    assert attachment["Type"] == "ActionOutput"

    event_val = params["Event"]
    assert event_val["WFSerializationType"] == "WFTextTokenAttachment"
    assert event_val["Value"]["OutputUUID"] == "3776F881-73AB-4A82-961F-7AEC4563A72B"
    assert event_val["Value"]["Type"] == "ActionOutput"
