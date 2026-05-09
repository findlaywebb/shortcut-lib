"""Tests for AddNewReminder action schema.

Wire-format equivalence uses batch_add_reminders.xml action 12 (the child-
reminder entry), which exercises WFCalendarItemTitle (WFTextTokenString with
a NamedVar), WFAlertEnabled, WFAlertCondition, WFCalendarItemCalendar,
WFParentTask (WFTextTokenAttachment), and WFURL simultaneously.
"""

from __future__ import annotations

import copy
import plistlib
from pathlib import Path
from typing import Any

import pytest

import shortcut_lib.schema.actions.add_new_reminder  # noqa: F401 — trigger registration
from shortcut_lib.schema.actions.add_new_reminder import AddNewReminder
from shortcut_lib.schema.base import SchemaError
from shortcut_lib.schema.registry import lookup
from shortcut_lib.schema.values import NamedVar, Output

DECODED = Path(__file__).parent.parent / "samples" / "decoded"
BATCH_REMINDERS = DECODED / "batch_add_reminders.xml"
ADD_EXPIRY = DECODED / "add_expiry_reminder.xml"


# ---------------------------------------------------------------------------
# Helpers (mirrors test_wire_format_equivalence.py conventions)
# ---------------------------------------------------------------------------


def _load(path: Path) -> dict[str, Any]:
    """Load a decoded plist XML file."""
    return plistlib.loads(path.read_bytes())


def _strip_output_uuids(obj: Any) -> None:
    """Recursively strip OutputUUID so UUIDs don't matter in comparison."""
    if isinstance(obj, dict):
        obj.pop("OutputUUID", None)
        obj.pop("VariableUUID", None)
        for v in obj.values():
            _strip_output_uuids(v)
    elif isinstance(obj, list):
        for v in obj:
            _strip_output_uuids(v)


def _normalise(action_dict: dict[str, Any]) -> dict[str, Any]:
    """Strip non-deterministic fields before comparison."""
    out = copy.deepcopy(action_dict)
    params = out.get("WFWorkflowActionParameters", {})
    params.pop("UUID", None)
    params.pop("CustomOutputName", None)
    _strip_output_uuids(params)
    return out


# ---------------------------------------------------------------------------
# test_basic_minimal — title only
# ---------------------------------------------------------------------------


def test_basic_minimal() -> None:
    """AddNewReminder with a bare string title emits only WFCalendarItemTitle."""
    action = AddNewReminder(title="Buy milk")
    d = action.to_action_dict()

    assert d["WFWorkflowActionIdentifier"] == "is.workflow.actions.addnewreminder"
    params = d["WFWorkflowActionParameters"]
    assert params["WFCalendarItemTitle"] == "Buy milk"
    # All optional keys must be absent.
    for key in (
        "WFCalendarItemCalendar",
        "WFCalendarItemNotes",
        "WFAlertEnabled",
        "WFAlertCondition",
        "WFAlertCustomTime",
        "WFAlertLocationRadius",
        "WFURL",
        "WFFlag",
        "WFParentTask",
    ):
        assert key not in params, f"Expected {key!r} to be absent for minimal action"


# ---------------------------------------------------------------------------
# test_full_fields — all fields populated
# ---------------------------------------------------------------------------


def test_full_fields() -> None:
    """All optional fields appear in output when explicitly set."""
    parent = AddNewReminder(title="Parent Task")
    location_radius = {
        "Value": {"Magnitude": "250", "Unit": "ft"},
        "WFSerializationType": "WFQuantityFieldValue",
    }

    action = AddNewReminder(
        title="Sub-task",
        calendar="Shopping",
        notes="Pick up organic variety",
        alert_enabled="Alert",
        alert_condition="When I Arrive",
        alert_location_radius=location_radius,
        url="https://example.com/list",
        flag=False,
        parent_task=parent,
    )
    params = action.to_action_dict()["WFWorkflowActionParameters"]

    assert params["WFCalendarItemTitle"] == "Sub-task"
    assert params["WFCalendarItemCalendar"] == "Shopping"
    assert params["WFCalendarItemNotes"] == "Pick up organic variety"
    assert params["WFAlertEnabled"] == "Alert"
    assert params["WFAlertCondition"] == "When I Arrive"
    assert params["WFAlertLocationRadius"] == location_radius
    assert params["WFURL"] == "https://example.com/list"
    assert params["WFFlag"] is False
    # WFParentTask is a WFTextTokenAttachment.
    parent_param = params["WFParentTask"]
    assert parent_param["WFSerializationType"] == "WFTextTokenAttachment"
    assert parent_param["Value"]["OutputName"] == "New Reminder"
    assert parent_param["Value"]["Type"] == "ActionOutput"


# ---------------------------------------------------------------------------
# test_required_title — missing title raises SchemaError
# ---------------------------------------------------------------------------


def test_required_title() -> None:
    """Constructing AddNewReminder without a title raises SchemaError."""
    with pytest.raises(SchemaError, match="WFCalendarItemTitle"):
        AddNewReminder()  # ty: ignore[call-overload]  # intentional missing title


def test_required_title_none_explicit() -> None:
    """Passing title=None explicitly also raises SchemaError."""
    with pytest.raises(SchemaError, match="WFCalendarItemTitle"):
        AddNewReminder(title=None)


# ---------------------------------------------------------------------------
# test_alert_condition_only_when_alert_enabled
# ---------------------------------------------------------------------------


def test_alert_condition_without_alert_enabled() -> None:
    """WFAlertCondition can be present without WFAlertEnabled.

    Observed in batch_add_reminders action 2: WFAlertCondition="When I Arrive"
    appears without a WFAlertEnabled key. The schema does not enforce the
    co-occurrence of these fields. Both can be set independently.
    """
    action = AddNewReminder(title="Pick up parcel", alert_condition="When I Arrive")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFAlertCondition"] == "When I Arrive"
    assert "WFAlertEnabled" not in params


def test_alert_enabled_without_alert_condition() -> None:
    """WFAlertEnabled can be set without WFAlertCondition — schema is permissive."""
    action = AddNewReminder(title="Check email", alert_enabled="No Alert")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFAlertEnabled"] == "No Alert"
    assert "WFAlertCondition" not in params


def test_invalid_alert_enabled_raises() -> None:
    """An unrecognised alert_enabled value raises SchemaError."""
    with pytest.raises(SchemaError, match="'Enabled'"):
        AddNewReminder(
            title="t",
            alert_enabled="Enabled",  # ty: ignore[invalid-argument-type]
        )


def test_invalid_alert_condition_raises() -> None:
    """An unrecognised alert_condition value raises SchemaError."""
    with pytest.raises(SchemaError, match="'On Tuesday'"):
        AddNewReminder(
            title="t",
            alert_condition="On Tuesday",  # ty: ignore[invalid-argument-type]
        )


# ---------------------------------------------------------------------------
# test_registered — registry lookup
# ---------------------------------------------------------------------------


def test_registered() -> None:
    """AddNewReminder is discoverable via the registry."""
    cls = lookup("is.workflow.actions.addnewreminder")
    assert cls is AddNewReminder


def test_default_output_name() -> None:
    """AddNewReminder.default_output_name is 'New Reminder' (matches samples)."""
    assert AddNewReminder.default_output_name == "New Reminder"


# ---------------------------------------------------------------------------
# test_wire_format_equivalence
# ---------------------------------------------------------------------------


def test_wire_format_equivalence_child_reminder() -> None:
    """Schema matches batch_add_reminders.xml action 12 (child reminder).

    Source: samples/decoded/batch_add_reminders.xml, action index 12.
    This action adds a shopping-list sub-task attached to a parent reminder.

    Sample params (after normalisation):
        WFCalendarItemTitle   = WFTextTokenString wrapping NamedVar "Repeat Item"
        WFAlertEnabled        = "No Alert"
        WFAlertCondition      = "When I Arrive"
        WFCalendarItemCalendar = "Shopping"
        WFParentTask          = WFTextTokenAttachment (OutputName "New Reminder")
        WFURL                 = ""

    Note: the sample's WFParentTask references action 2's UUID. After
    normalisation (OutputUUID stripped by _strip_output_uuids) only
    OutputName and Type remain — both deterministic.
    """
    if not BATCH_REMINDERS.exists():
        pytest.skip(f"Sample not found: {BATCH_REMINDERS}")

    workflow = _load(BATCH_REMINDERS)
    sample_action = workflow["WFWorkflowActions"][12]
    assert (
        sample_action["WFWorkflowActionIdentifier"]
        == "is.workflow.actions.addnewreminder"
    )
    sample_norm = _normalise(sample_action)

    # The parent reminder is action 2 in the sample. We supply a dummy Output
    # with the correct OutputName so the normalised comparison matches.
    parent_output = Output(
        uuid="871C1213-2ADD-467B-AC34-63E43A2A858E",
        name="New Reminder",
    )
    repeat_item = NamedVar("Repeat Item")

    schema_action = AddNewReminder(
        title=repeat_item,
        calendar="Shopping",
        alert_enabled="No Alert",
        alert_condition="When I Arrive",
        url="",
        parent_task=parent_output,
    )
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm


def test_wire_format_equivalence_timed_alert() -> None:
    """Schema matches set_weekend_chores.xml action 3 (timed-alert reminder).

    Source: samples/decoded/set_weekend_chores.xml, action index 3.
    Sample params (after normalisation):
        WFCalendarItemTitle   = WFTextTokenString wrapping NamedVar "Repeat Item"
        WFAlertCondition      = "At Time"
        WFAlertCustomTime     = WFTextTokenString with Ask attachment
        WFAlertEnabled        = "Alert"
        WFCalendarItemCalendar = "Chores"
        WFCalendarItemNotes   = ""
    """
    from shortcut_lib.schema.values import Ask

    weekend_sample = DECODED / "set_weekend_chores.xml"
    if not weekend_sample.exists():
        pytest.skip(f"Sample not found: {weekend_sample}")

    workflow = _load(weekend_sample)
    sample_action = workflow["WFWorkflowActions"][3]
    assert (
        sample_action["WFWorkflowActionIdentifier"]
        == "is.workflow.actions.addnewreminder"
    )
    sample_norm = _normalise(sample_action)

    repeat_item = NamedVar("Repeat Item")
    schema_action = AddNewReminder(
        title=repeat_item,
        calendar="Chores",
        notes="",
        alert_enabled="Alert",
        alert_condition="At Time",
        alert_custom_time=Ask,
    )
    schema_norm = _normalise(schema_action.to_action_dict())

    assert schema_norm == sample_norm


def test_empty_string_fields_emitted() -> None:
    """Empty string values for notes and url are emitted (not suppressed).

    Samples consistently carry empty-string WFCalendarItemNotes and WFURL
    when those fields are present. Passing "" must not suppress the key.
    """
    action = AddNewReminder(title="Test", notes="", url="")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "WFCalendarItemNotes" in params
    assert params["WFCalendarItemNotes"] == ""
    assert "WFURL" in params
    assert params["WFURL"] == ""


def test_none_fields_omitted() -> None:
    """None values for optional fields produce absent keys."""
    action = AddNewReminder(title="Test", notes=None, url=None)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "WFCalendarItemNotes" not in params
    assert "WFURL" not in params


def test_title_as_named_var() -> None:
    """A NamedVar title is coerced to a WFTextTokenString envelope."""
    var = NamedVar("Repeat Item")
    action = AddNewReminder(title=var)
    params = action.to_action_dict()["WFWorkflowActionParameters"]

    title = params["WFCalendarItemTitle"]
    assert isinstance(title, dict)
    assert title["WFSerializationType"] == "WFTextTokenString"
    inner = title["Value"]
    assert inner["string"] == "￼"
    token = next(iter(inner["attachmentsByRange"].values()))
    assert token["Type"] == "Variable"
    assert token["VariableName"] == "Repeat Item"


def test_alert_custom_time_is_text_token_string() -> None:
    """alert_custom_time is emitted as WFTextTokenString (not WFTextTokenAttachment).

    Observed in both set_weekend_chores.xml and add_expiry_reminder.xml.
    coerce_text_field wraps a single variable reference in the template envelope.
    """
    from shortcut_lib.schema.values import Ask

    action = AddNewReminder(
        title="Meet",
        alert_enabled="Alert",
        alert_condition="At Time",
        alert_custom_time=Ask,
    )
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    custom_time = params["WFAlertCustomTime"]
    assert custom_time["WFSerializationType"] == "WFTextTokenString"
    token = next(iter(custom_time["Value"]["attachmentsByRange"].values()))
    assert token["Type"] == "Ask"
