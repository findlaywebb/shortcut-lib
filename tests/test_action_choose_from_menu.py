"""Tests for ChooseFromMenu control-flow construct.

Covers emit shape, control-flow modes, grouping identifier consistency,
head parameters, case markers, error conditions, and chaining.
"""

from __future__ import annotations

import pytest

from shortcut_lib.builder import Shortcut
from shortcut_lib.schema import ChooseFromMenu, SchemaError, list_control_flow
from shortcut_lib.schema.actions.comment import Comment
from shortcut_lib.schema.actions.get_text import GetText
from shortcut_lib.schema.actions.set_clipboard import SetClipboard

_MENU_ID = "is.workflow.actions.choosefrommenu"


def _two_case_shortcut() -> tuple[Shortcut, list[dict]]:
    """Return a 2-case shortcut and its emitted action dicts."""
    s = Shortcut(name="MenuTest")
    s.add(
        ChooseFromMenu(
            prompt="Pick",
            cases=[
                ("A", [Comment(text="a")]),
                ("B", [Comment(text="b")]),
            ],
        )
    )
    actions = s.to_workflow()["WFWorkflowActions"]
    return s, actions


def test_two_cases_emits_correct_dict_count() -> None:
    """Two-case menu: head + per-case marker + per-case body + tail = 6."""
    _, actions = _two_case_shortcut()
    assert len(actions) == 6


def test_control_flow_modes_are_0_1_1_2() -> None:
    """ChooseFromMenu actions carry WFControlFlowMode sequence [0, 1, 1, 2]."""
    _, actions = _two_case_shortcut()
    menu_actions = [a for a in actions if a["WFWorkflowActionIdentifier"] == _MENU_ID]
    modes = [a["WFWorkflowActionParameters"]["WFControlFlowMode"] for a in menu_actions]
    assert modes == [0, 1, 1, 2]


def test_grouping_identifier_is_consistent() -> None:
    """All four choosefrommenu actions share the same GroupingIdentifier."""
    _, actions = _two_case_shortcut()
    menu_actions = [a for a in actions if a["WFWorkflowActionIdentifier"] == _MENU_ID]
    identifiers = {
        a["WFWorkflowActionParameters"]["GroupingIdentifier"] for a in menu_actions
    }
    assert len(identifiers) == 1


def test_head_emits_menu_items_and_prompt() -> None:
    """Head action carries WFMenuItems list and WFMenuPrompt."""
    _, actions = _two_case_shortcut()
    menu_actions = [a for a in actions if a["WFWorkflowActionIdentifier"] == _MENU_ID]
    head_params = menu_actions[0]["WFWorkflowActionParameters"]
    assert head_params["WFMenuItems"] == ["A", "B"]
    assert head_params["WFMenuPrompt"] == "Pick"


def test_case_markers_carry_titles() -> None:
    """Case-marker actions (mode 1) carry WFMenuItemTitle in order."""
    _, actions = _two_case_shortcut()
    menu_actions = [a for a in actions if a["WFWorkflowActionIdentifier"] == _MENU_ID]
    markers = [
        a
        for a in menu_actions
        if a["WFWorkflowActionParameters"]["WFControlFlowMode"] == 1
    ]
    titles = [m["WFWorkflowActionParameters"]["WFMenuItemTitle"] for m in markers]
    assert titles == ["A", "B"]


def test_empty_cases_raises_schema_error() -> None:
    """ChooseFromMenu with no cases raises SchemaError on emit."""
    s = Shortcut(name="Empty")
    s.add(ChooseFromMenu(cases=[]))
    with pytest.raises(SchemaError, match="needs at least one case"):
        s.to_workflow()


def test_single_case_works() -> None:
    """Single-case menu emits 4 dicts (head + marker + body + tail)."""
    s = Shortcut(name="OneCase")
    s.add(ChooseFromMenu(cases=[("Only", [Comment(text="x")])]))
    actions = s.to_workflow()["WFWorkflowActions"]
    assert len(actions) == 4
    menu_actions = [a for a in actions if a["WFWorkflowActionIdentifier"] == _MENU_ID]
    modes = [a["WFWorkflowActionParameters"]["WFControlFlowMode"] for a in menu_actions]
    assert modes == [0, 1, 2]


def test_choosefrommenu_listed_in_control_flow_registry() -> None:
    """list_control_flow() includes ChooseFromMenu by name."""
    names = {row["name"] for row in list_control_flow()}
    assert "ChooseFromMenu" in names


def test_case_with_action_input_chains_correctly() -> None:
    """Body action inside a case can reference a prior action's output UUID."""
    s = Shortcut(name="ChainTest")
    text = s.add(GetText(text="hello"))
    s.add(ChooseFromMenu(cases=[("A", [SetClipboard(input=text)])]))
    actions = s.to_workflow()["WFWorkflowActions"]

    get_text_action = actions[0]
    get_text_uuid = get_text_action["WFWorkflowActionParameters"]["UUID"]

    # Layout: GetText(0), head(1), case-A-marker(2), SetClipboard(3), tail(4)
    set_clipboard_action = actions[3]
    assert (
        set_clipboard_action["WFWorkflowActionIdentifier"]
        == "is.workflow.actions.setclipboard"
    )
    wf_input = set_clipboard_action["WFWorkflowActionParameters"]["WFInput"]
    assert wf_input["Value"]["OutputUUID"] == get_text_uuid
