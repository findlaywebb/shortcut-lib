"""Tests for TextSplit — is.workflow.actions.text.split."""

from __future__ import annotations

import pytest

from shortcut_lib.schema.actions.text_split import TextSplit
from shortcut_lib.schema.base import SchemaError
from shortcut_lib.schema.registry import list_actions


def test_text_split_new_lines_default() -> None:
    """Default separator omits the key (matches Apple's emission).

    Apple omits the ``separator`` key for the default "New Lines"; five
    corpus samples confirm (e.g. samples/decoded/batch_add_reminders.xml:9).
    """
    result = TextSplit(input="hello\nworld").to_action_dict()

    assert result["WFWorkflowActionIdentifier"] == "is.workflow.actions.text.split"
    params = result["WFWorkflowActionParameters"]
    assert "separator" not in params
    assert params["text"] == "hello\nworld"
    assert "WFTextCustomSeparator" not in params


def test_text_split_custom_requires_separator() -> None:
    """Custom separator without custom_separator raises SchemaError."""
    with pytest.raises(SchemaError, match="custom_separator"):
        TextSplit(input="a,b,c", separator="Custom").to_action_dict()


def test_text_split_custom_with_separator_emits_both_keys() -> None:
    """Custom separator with custom_separator emits both separator keys."""
    result = TextSplit(
        input="a,b,c", separator="Custom", custom_separator=","
    ).to_action_dict()
    params = result["WFWorkflowActionParameters"]

    assert params["separator"] == "Custom"
    assert params["WFTextCustomSeparator"] == ","
    assert params["text"] == "a,b,c"


def test_text_split_with_action_input() -> None:
    """Passing another Action as input resolves to that action's OutputUUID."""
    from shortcut_lib.schema.actions.ask import AskForInput

    ask = AskForInput(prompt="Enter text")
    split = TextSplit(input=ask, separator="Spaces")

    params = split.to_action_dict()["WFWorkflowActionParameters"]

    assert "text" in params
    text_param = params["text"]
    # coerce_value on an Action → output().to_param() →
    # WFTextTokenAttachment with OutputUUID
    assert text_param["Value"]["OutputUUID"] == ask.uuid
    assert text_param["WFSerializationType"] == "WFTextTokenAttachment"


def test_text_split_registered() -> None:
    """TextSplit appears in list_actions() with the correct identifier."""
    identifiers = {entry["identifier"] for entry in list_actions()}
    assert "is.workflow.actions.text.split" in identifiers


def test_text_split_invalid_separator_raises() -> None:
    """An unrecognised separator raises SchemaError naming the bad value."""
    with pytest.raises(SchemaError, match="'Commas'"):
        TextSplit(input="a,b,c", separator="Commas")  # ty: ignore[invalid-argument-type]  # intentional bad value


def test_text_split_valid_separators_accepted() -> None:
    """All valid separators construct without error.

    "New Lines" is the default and is omitted from the emitted dict
    (matches Apple); the other two valid non-Custom separators are
    emitted verbatim.
    """
    # The default is omitted from the emitted dict.
    default_params = TextSplit(input="abc").to_action_dict()[
        "WFWorkflowActionParameters"
    ]
    assert "separator" not in default_params

    # Non-default separators are emitted.
    for sep in ("Spaces", "Every Character"):
        action = TextSplit(input="abc", separator=sep)
        params = action.to_action_dict()["WFWorkflowActionParameters"]
        assert params["separator"] == sep
