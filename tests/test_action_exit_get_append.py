"""ExitShortcut + GetVariable + AppendVariable tests (P3)."""

from __future__ import annotations

import pytest

from shortcut_lib.schema import SchemaError, list_actions
from shortcut_lib.schema.actions.append_variable import AppendVariable
from shortcut_lib.schema.actions.exit_shortcut import ExitShortcut
from shortcut_lib.schema.actions.get_variable import GetVariable


def test_exit_shortcut_emits_zero_params() -> None:
    action = ExitShortcut().to_action_dict()
    assert action["WFWorkflowActionIdentifier"] == "is.workflow.actions.exit"
    # UUID is the only key in params
    assert set(action["WFWorkflowActionParameters"]) == {"UUID"}


def test_get_variable_emits_name() -> None:
    action = GetVariable(name="Note").to_action_dict()
    params = action["WFWorkflowActionParameters"]
    assert action["WFWorkflowActionIdentifier"] == "is.workflow.actions.getvariable"
    assert params["WFVariable"]["Value"]["VariableName"] == "Note"


def test_get_variable_without_name_raises() -> None:
    with pytest.raises(SchemaError, match="requires `name`"):
        GetVariable().to_action_dict()


def test_append_variable_with_input() -> None:
    action = AppendVariable(name="Lines", input="hello").to_action_dict()
    params = action["WFWorkflowActionParameters"]
    assert action["WFWorkflowActionIdentifier"] == "is.workflow.actions.appendvariable"
    assert params["WFVariableName"] == "Lines"
    assert params["WFInput"] == "hello"


def test_append_variable_without_name_raises() -> None:
    with pytest.raises(SchemaError, match="requires `name`"):
        AppendVariable(input="hello").to_action_dict()


def test_all_three_in_registry() -> None:
    idents = {row["identifier"] for row in list_actions()}
    assert "is.workflow.actions.exit" in idents
    assert "is.workflow.actions.getvariable" in idents
    assert "is.workflow.actions.appendvariable" in idents
