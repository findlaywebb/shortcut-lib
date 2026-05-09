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


def test_ask_text_with_number_flags_raises() -> None:
    """allows_decimal/allows_negative are Number-only — caller mistake should fail loudly."""
    import pytest

    from shortcut_lib.schema import SchemaError

    with pytest.raises(SchemaError, match="only applies to input_type='Number'"):
        AskForInput(input_type="Text", allows_decimal=True)


def test_ask_invalid_input_type_raises() -> None:
    """Typo or unsupported value should fail at construction."""
    import pytest

    from shortcut_lib.schema import SchemaError

    with pytest.raises(SchemaError, match=r"not a.*valid Apple input type"):
        AskForInput(input_type="number")  # ty: ignore[invalid-argument-type]  # intentional bad value


def test_ask_date_and_time_routes_default_to_dedicated_key() -> None:
    """Verified via samples/decoded/add_expiry_reminder.xml."""
    params = AskForInput(
        prompt="What is the expiry date?",
        input_type="Date and Time",
        default_answer="2026-12-31 14:00",
    ).to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFAskActionDefaultAnswerDateAndTime"] == "2026-12-31 14:00"
    assert "WFAskActionDefaultAnswer" not in params
    assert "WFAskActionDefaultAnswerNumber" not in params


def test_ask_date_routes_default_to_date_key() -> None:
    """Date and Time use WFAskActionDefaultAnswerDate (inferred — flag if a real sample contradicts)."""
    params = AskForInput(
        input_type="Date", default_answer="2026-05-08"
    ).to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFAskActionDefaultAnswerDate"] == "2026-05-08"


def test_ask_url_uses_text_default_key() -> None:
    """URL type shares the Text answer key."""
    params = AskForInput(
        input_type="URL", default_answer="https://example.com"
    ).to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFAskActionDefaultAnswer"] == "https://example.com"


def test_ask_text_factory() -> None:
    """AskForInput.text() produces a Text-type action with the right wire shape."""
    params = AskForInput.text(prompt="X", default_answer="hello").to_action_dict()[
        "WFWorkflowActionParameters"
    ]
    assert params["WFInputType"] == "Text"
    assert params["WFAskActionPrompt"] == "X"
    assert params["WFAskActionDefaultAnswer"] == "hello"
    assert "WFAskActionAllowsDecimalNumbers" not in params
    assert "WFAskActionAllowsNegativeNumbers" not in params


def test_ask_number_factory() -> None:
    """AskForInput.number() produces Number type with decimal/negative flags."""
    params = AskForInput.number(prompt="X", allows_decimal=True).to_action_dict()[
        "WFWorkflowActionParameters"
    ]
    assert params["WFInputType"] == "Number"
    assert params["WFAskActionAllowsDecimalNumbers"] is True
    assert "WFAskActionAllowsNegativeNumbers" not in params


def test_ask_text_no_allows_decimal_kwarg() -> None:
    """AskForInput.text() does not accept allows_decimal — TypeError at call time."""
    import pytest

    with pytest.raises(TypeError):
        AskForInput.text(prompt="X", allows_decimal=True)  # ty: ignore[unknown-argument]


def test_ask_factory_round_trip_equals_direct() -> None:
    """Factory params are identical to direct constructor for Number type.

    UUIDs differ per-instance, so compare the parameters dict only.
    """
    via_factory = AskForInput.number(prompt="X", allows_decimal=True).to_action_dict()[
        "WFWorkflowActionParameters"
    ]
    via_direct = AskForInput(
        prompt="X", input_type="Number", allows_decimal=True
    ).to_action_dict()["WFWorkflowActionParameters"]
    # Exclude the UUID — it is unique per instance by design.
    via_factory.pop("UUID", None)
    via_direct.pop("UUID", None)
    assert via_factory == via_direct


def test_ask_registered() -> None:
    """AskForInput appears in list_actions() with the correct identifier."""
    actions = list_actions()
    identifiers = [a["identifier"] for a in actions]
    assert "is.workflow.actions.ask" in identifiers
    cls = lookup("is.workflow.actions.ask")
    assert cls is AskForInput
