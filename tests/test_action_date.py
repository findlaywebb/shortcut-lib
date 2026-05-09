"""Tests for the DateAction schema."""

from __future__ import annotations

import pytest

import shortcut_lib.schema.actions.date  # noqa: F401 — trigger registration
from shortcut_lib.schema.actions.date import DateAction
from shortcut_lib.schema.base import SchemaError
from shortcut_lib.schema.registry import lookup


def test_date_action_default_is_current_date() -> None:
    """Default construction emits no mode/date keys — matches both corpus samples.

    Both corpus appearances (daily_standup.xml:870 and dictionary.xml:482)
    have an empty parameters dict (UUID only), meaning "Current Date" mode
    emits no extra keys.
    """
    action = DateAction()
    result = action.to_action_dict()
    assert result["WFWorkflowActionIdentifier"] == "is.workflow.actions.date"
    params = result["WFWorkflowActionParameters"]
    assert "WFDateActionMode" not in params
    assert "WFDateActionDate" not in params


def test_date_action_current_date_explicit() -> None:
    """Explicitly passing mode='Current Date' also emits no extra keys."""
    action = DateAction(mode="Current Date")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "WFDateActionMode" not in params
    assert "WFDateActionDate" not in params


def test_date_action_specified_date() -> None:
    """mode='Specified Date' emits both WFDateActionMode and WFDateActionDate."""
    action = DateAction(mode="Specified Date", date="2025-06-15")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFDateActionMode"] == "Specified Date"
    assert params["WFDateActionDate"] == "2025-06-15"


def test_date_action_specified_date_requires_date() -> None:
    """mode='Specified Date' without date raises SchemaError."""
    with pytest.raises(SchemaError, match="date must be set"):
        DateAction(mode="Specified Date")


def test_date_action_invalid_mode() -> None:
    """An unrecognised mode raises SchemaError naming the bad value."""
    with pytest.raises(SchemaError, match="'Tomorrow'"):
        DateAction(mode="Tomorrow")  # ty: ignore[invalid-argument-type]


def test_date_action_registered() -> None:
    """DateAction is findable in the registry by its identifier."""
    cls = lookup("is.workflow.actions.date")
    assert cls is DateAction


def test_date_action_default_output_name() -> None:
    """DateAction.default_output_name is 'Date'."""
    assert DateAction.default_output_name == "Date"


def test_date_action_wire_format_equivalence_daily_standup() -> None:
    """Wire format matches daily_standup.xml:870 sample exactly (minus UUID).

    Sample at lines 868-876: parameters dict contains only UUID — no mode or
    date keys. Default DateAction() must reproduce this exactly.
    """
    action = DateAction(uuid="4C2D9B0F-4380-496B-B8A4-7B855589C271")
    result = action.to_action_dict()
    assert result["WFWorkflowActionIdentifier"] == "is.workflow.actions.date"
    params = result["WFWorkflowActionParameters"]
    assert params["UUID"] == "4C2D9B0F-4380-496B-B8A4-7B855589C271"
    assert set(params.keys()) == {"UUID"}


def test_date_action_wire_format_equivalence_dictionary() -> None:
    """Wire format matches dictionary.xml:482 sample exactly (minus UUID).

    Sample at lines 480-488: parameters dict contains only UUID.
    """
    action = DateAction(uuid="587672B1-BF85-45B6-A32B-99CA787A0227")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["UUID"] == "587672B1-BF85-45B6-A32B-99CA787A0227"
    assert set(params.keys()) == {"UUID"}
