"""Tests for GetText — is.workflow.actions.gettext."""

from __future__ import annotations

from shortcut_lib.schema.actions.get_text import GetText
from shortcut_lib.schema.registry import list_actions
from shortcut_lib.schema.values import NamedVar, Text


def test_get_text_with_literal_string() -> None:
    """Plain string produces WFTextActionText == the string literal."""
    result = GetText(text="hello").to_action_dict()
    params = result["WFWorkflowActionParameters"]
    assert result["WFWorkflowActionIdentifier"] == "is.workflow.actions.gettext"
    assert params["WFTextActionText"] == "hello"


def test_get_text_with_templated_text() -> None:
    """Templated Text produces a WFTextTokenString-shaped parameter."""
    t = Text("Hello {x}", substitutions={"x": NamedVar("Y")})
    result = GetText(text=t).to_action_dict()
    params = result["WFWorkflowActionParameters"]
    token_param = params["WFTextActionText"]

    assert token_param["WFSerializationType"] == "WFTextTokenString"
    value = token_param["Value"]
    assert "string" in value
    assert "attachmentsByRange" in value
    # The placeholder character should replace {x}
    assert "￼" in value["string"]
    # One attachment for the single substitution
    assert len(value["attachmentsByRange"]) == 1
    # The attachment token should reference the NamedVar "Y"
    attachment = next(iter(value["attachmentsByRange"].values()))
    assert attachment["Type"] == "Variable"
    assert attachment["VariableName"] == "Y"


def test_get_text_registered() -> None:
    """GetText appears in list_actions() with the correct identifier."""
    identifiers = {entry["identifier"] for entry in list_actions()}
    assert "is.workflow.actions.gettext" in identifiers


def test_get_text_empty_string_emits() -> None:
    """Empty string is emitted as WFTextActionText == "" (not omitted).

    GetText routes through coerce_text_field, which returns a str
    unchanged — including the empty string. The key is always present
    because _params unconditionally includes WFTextActionText.
    This differs from text=None, which emits null rather than "".
    """
    params = GetText(text="").to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFTextActionText"] == ""

    # Contrast: text=None emits null, not "". Both are emitted (not omitted).
    params_none = GetText(text=None).to_action_dict()["WFWorkflowActionParameters"]
    assert params_none["WFTextActionText"] is None
