"""Tests for the SetVariable schema action."""

from __future__ import annotations

import pytest

from shortcut_lib.schema.actions.dictate_text import DictateText
from shortcut_lib.schema.actions.set_variable import SetVariable
from shortcut_lib.schema.base import SchemaError
from shortcut_lib.schema.registry import list_actions


def test_set_variable_emits_correct_identifier_and_keys() -> None:
    """to_action_dict emits the right identifier and both WF keys."""
    action = SetVariable(name="MyVar", input="hello")
    result = action.to_action_dict()

    assert result["WFWorkflowActionIdentifier"] == "is.workflow.actions.setvariable"
    params = result["WFWorkflowActionParameters"]
    assert "WFVariableName" in params
    assert params["WFVariableName"] == "MyVar"
    assert "WFInput" in params
    assert params["WFInput"] == "hello"


def test_set_variable_with_action_input_resolves_output() -> None:
    """Passing another Action as input resolves to that action's OutputUUID."""
    dictate = DictateText()
    sv = SetVariable(name="Captured", input=dictate)

    result = sv.to_action_dict()
    params = result["WFWorkflowActionParameters"]

    assert "WFInput" in params
    wf_input = params["WFInput"]
    # coerce_value on an Action calls action.output().to_param(), which
    # produces a WFTextTokenAttachment envelope with an OutputUUID inside.
    assert wf_input["Value"]["OutputUUID"] == dictate.uuid


def test_set_variable_registered() -> None:
    """SetVariable's identifier appears in the action registry."""
    identifiers = [entry["identifier"] for entry in list_actions()]
    assert "is.workflow.actions.setvariable" in identifiers


def test_set_variable_empty_name_raises() -> None:
    """SetVariable with an empty name raises SchemaError."""
    action = SetVariable(name="", input="value")
    with pytest.raises(SchemaError, match="name"):
        action.to_action_dict()


def test_set_variable_empty_input_emits_empty_string() -> None:
    """SetVariable(input="") emits WFInput as "" rather than omitting it.

    SetVariable routes input through coerce_value, not coerce_text_field.
    coerce_value passes plain scalars (including "") through unchanged,
    and _params emits WFInput whenever input is not None.
    An empty string is not None, so WFInput="" appears in the wire dict.
    This contrasts with input=None, which causes WFInput to be omitted
    entirely — the two have different wire representations.
    """
    params = SetVariable(name="X", input="").to_action_dict()[
        "WFWorkflowActionParameters"
    ]
    assert params["WFInput"] == ""

    # Contrast: input=None omits WFInput entirely.
    params_none = SetVariable(name="X", input=None).to_action_dict()[
        "WFWorkflowActionParameters"
    ]
    assert "WFInput" not in params_none
