"""Tests for the AskForInput action schema."""

from __future__ import annotations

from shortcut_lib.schema.actions.ask import AskForInput
from shortcut_lib.schema.registry import list_actions, lookup


def test_ask_text_basic() -> None:
    """Text type emits WFAskActionPrompt and WFAskActionDefaultAnswer."""
    result = AskForInput(
        prompt="What's your name?",
        input_type="Text",
        default_answer="Alice",
    ).to_action_dict()
    params = result["WFWorkflowActionParameters"]
    assert params["WFAskActionPrompt"] == "What's your name?"
    assert params["WFInputType"] == "Text"
    assert params["WFAskActionDefaultAnswer"] == "Alice"
    assert "WFAskActionDefaultAnswerNumber" not in params


def test_ask_number_routes_default_to_number_key() -> None:
    """Number type routes default_answer to WFAskActionDefaultAnswerNumber."""
    params = AskForInput(
        prompt="How many minutes?",
        input_type="Number",
        default_answer="5",
    ).to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFAskActionDefaultAnswerNumber"] == "5"
    assert "WFAskActionDefaultAnswer" not in params


def test_ask_number_includes_decimal_negative_flags() -> None:
    """Decimal and negative flags appear in params when explicitly set for Number."""
    params = AskForInput(
        input_type="Number",
        allows_decimal=False,
        allows_negative=False,
    ).to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFAskActionAllowsDecimalNumbers"] is False
    assert params["WFAskActionAllowsNegativeNumbers"] is False


def test_ask_text_excludes_number_flags() -> None:
    """Text type omits decimal/negative flags even if set on the instance."""
    action = AskForInput(
        input_type="Text",
        allows_decimal=True,
        allows_negative=True,
    )
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "WFAskActionAllowsDecimalNumbers" not in params
    assert "WFAskActionAllowsNegativeNumbers" not in params


def test_ask_registered() -> None:
    """AskForInput appears in list_actions() with the correct identifier."""
    actions = list_actions()
    identifiers = [a["identifier"] for a in actions]
    assert "is.workflow.actions.ask" in identifiers
    cls = lookup("is.workflow.actions.ask")
    assert cls is AskForInput
