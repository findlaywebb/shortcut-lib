"""Tests for the SetVariable schema action."""

from __future__ import annotations

from shortcut_lib.schema.actions.dictate_text import DictateText
from shortcut_lib.schema.actions.set_variable import SetVariable
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
