"""Tests for the FormatDate action schema."""

from __future__ import annotations

import pytest

from shortcut_lib.schema.actions.format_date import FormatDate
from shortcut_lib.schema.base import SchemaError
from shortcut_lib.schema.registry import lookup
from shortcut_lib.schema.values import CurrentDate


def test_format_date_short_style() -> None:
    """FormatDate emits WFDate, WFDateFormatStyle with default Short style."""
    action = FormatDate(input=CurrentDate, date_style="Short", time_style="None")
    result = action.to_action_dict()
    assert result["WFWorkflowActionIdentifier"] == "is.workflow.actions.format.date"
    params = result["WFWorkflowActionParameters"]
    assert params["WFDateFormatStyle"] == "Short"
    assert params["WFTimeFormatStyle"] == "None"
    # WFDate is present — coerce_value on a MagicVar produces WFTextTokenAttachment
    wf_date = params["WFDate"]
    assert wf_date["WFSerializationType"] == "WFTextTokenAttachment"
    assert wf_date["Value"] == {"Type": "CurrentDate"}


def test_format_date_custom_requires_format_string() -> None:
    """date_style='Custom' without custom_format raises SchemaError."""
    with pytest.raises(SchemaError, match="custom_format"):
        FormatDate(input=CurrentDate, date_style="Custom")


def test_format_date_custom_with_format_string() -> None:
    """date_style='Custom' with custom_format emits both WFDateFormatStyle and WFDateFormat."""
    action = FormatDate(
        input=CurrentDate, date_style="Custom", custom_format="yyyy-MM-dd"
    )
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFDateFormatStyle"] == "Custom"
    assert params["WFDateFormat"] == "yyyy-MM-dd"
    # WFTimeFormatStyle is absent when time_style is not set
    assert "WFTimeFormatStyle" not in params


def test_format_date_with_currentdate_magic_var() -> None:
    """Passing CurrentDate magic var emits the correct WFTextTokenAttachment token."""
    action = FormatDate(input=CurrentDate)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    wf_date = params["WFDate"]
    # coerce_value on MagicVar → WFTextTokenAttachment with inner token
    assert wf_date["WFSerializationType"] == "WFTextTokenAttachment"
    assert wf_date["Value"] == {"Type": "CurrentDate"}


def test_format_date_registered() -> None:
    """FormatDate is findable in the registry by its identifier."""
    cls = lookup("is.workflow.actions.format.date")
    assert cls is FormatDate


def test_format_date_default_output_name() -> None:
    """FormatDate.default_output_name is 'Formatted Date'."""
    assert FormatDate.default_output_name == "Formatted Date"


def test_format_date_no_input_omits_wfdate() -> None:
    """When input is None, WFDate key is absent from emitted params."""
    action = FormatDate(date_style="Medium", time_style="None")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "WFDate" not in params
    assert params["WFDateFormatStyle"] == "Medium"
