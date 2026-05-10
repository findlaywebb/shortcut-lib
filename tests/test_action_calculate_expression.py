"""Tests for CalculateExpression schema action.

Wire-format expectations derive from two corpus appearances in
``samples/decoded/dictionary.xml``:

- Lines 394-424: ``Input`` = WFTextTokenString wrapping a single ActionOutput
  ref (OutputUUID 7B56D5FA-..., OutputName "Calculation Result");
  action UUID 693E408D-A668-49B2-BFDB-D4A9994E250A.
- Lines 4462-4492: same structure; OutputUUID 1686DF05-...;
  action UUID 3BC08D42-C707-4A96-A120-19D583A9229E.

Both appearances confirm: ``Input`` is the wire key (capitalised),
``WFSerializationType`` is ``WFTextTokenString``, ``default_output_name``
is ``"Calculation Result"``.
"""

from __future__ import annotations

import pytest

import shortcut_lib.schema.actions.calculate_expression  # noqa: F401
from shortcut_lib.schema.actions.calculate_expression import CalculateExpression
from shortcut_lib.schema.base import SchemaError
from shortcut_lib.schema.registry import lookup
from shortcut_lib.schema.values import NamedVar, Output

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_OBJECT_REPLACEMENT = "￼"  # U+FFFC used as attachment placeholder


def _params(action: CalculateExpression) -> dict:
    """Return the WFWorkflowActionParameters dict for an action."""
    return action.to_action_dict()["WFWorkflowActionParameters"]


# ---------------------------------------------------------------------------
# Identifier + registry
# ---------------------------------------------------------------------------


def test_identifier() -> None:
    """Action class carries the correct Apple identifier."""
    assert CalculateExpression.identifier == "is.workflow.actions.calculateexpression"


def test_default_output_name() -> None:
    """Output name matches the corpus-observed 'Calculation Result'."""
    assert CalculateExpression.default_output_name == "Calculation Result"


def test_registry_lookup() -> None:
    """@register makes the class discoverable via lookup()."""
    cls = lookup("is.workflow.actions.calculateexpression")
    assert cls is CalculateExpression


# ---------------------------------------------------------------------------
# Plain literal expression
# ---------------------------------------------------------------------------


def test_plain_string_expression() -> None:
    """A plain string expression passes through as-is (no extra envelope)."""
    action = CalculateExpression(expression="5 + 3")
    d = action.to_action_dict()

    assert d["WFWorkflowActionIdentifier"] == "is.workflow.actions.calculateexpression"
    params = d["WFWorkflowActionParameters"]

    assert params["Input"] == "5 + 3"
    assert "UUID" in params


def test_plain_string_complex_expression() -> None:
    """Operator precedence string round-trips verbatim."""
    params = _params(CalculateExpression(expression="(10 + 2) * 3 / 6"))
    assert params["Input"] == "(10 + 2) * 3 / 6"


# ---------------------------------------------------------------------------
# Variable interpolation — WFTextTokenString envelope
# ---------------------------------------------------------------------------


def test_named_var_expression_wrapped_as_wftexttokenstring() -> None:
    """A NamedVar expression is wrapped as a single-attachment WFTextTokenString.

    Matches the corpus pattern (both dictionary.xml appearances): Input is
    a WFTextTokenString envelope whose Value dict contains a
    ``{0, 1}`` attachment entry and an object-replacement placeholder string.
    """
    var = NamedVar("My Expression")
    params = _params(CalculateExpression(expression=var))

    token_str = params["Input"]
    assert token_str["WFSerializationType"] == "WFTextTokenString"

    value = token_str["Value"]
    assert value["string"] == _OBJECT_REPLACEMENT

    attachments = value["attachmentsByRange"]
    assert "{0, 1}" in attachments
    attachment = attachments["{0, 1}"]
    assert attachment["VariableName"] == "My Expression"


def test_output_ref_expression_wrapped_as_wftexttokenstring() -> None:
    """An Output ref (ActionOutput) produces a WFTextTokenString envelope.

    Matches the exact structure in corpus lines 401-419 and 4468-4488:
    the attachment carries Type=ActionOutput, OutputName, OutputUUID.
    """
    ref = Output(uuid="7B56D5FA-ED27-4E45-A75D-3C187C8BBBC1", name="Calculation Result")
    params = _params(CalculateExpression(expression=ref))

    token_str = params["Input"]
    assert token_str["WFSerializationType"] == "WFTextTokenString"

    value = token_str["Value"]
    assert value["string"] == _OBJECT_REPLACEMENT

    attachments = value["attachmentsByRange"]
    assert "{0, 1}" in attachments
    attachment = attachments["{0, 1}"]
    assert attachment["Type"] == "ActionOutput"
    assert attachment["OutputName"] == "Calculation Result"
    assert attachment["OutputUUID"] == "7B56D5FA-ED27-4E45-A75D-3C187C8BBBC1"


# ---------------------------------------------------------------------------
# Wire-equivalence vs corpus appearance 1 (dictionary.xml lines 394-424)
# ---------------------------------------------------------------------------


def test_wire_equivalence_corpus_appearance_1() -> None:
    """Round-trip matches corpus appearance 1 (dictionary.xml lines 394-424).

    The corpus action has:
    - Action UUID: 693E408D-A668-49B2-BFDB-D4A9994E250A
    - Input: WFTextTokenString wrapping ActionOutput with
      OutputUUID 7B56D5FA-ED27-4E45-A75D-3C187C8BBBC1,
      OutputName "Calculation Result"
    """
    ref = Output(uuid="7B56D5FA-ED27-4E45-A75D-3C187C8BBBC1", name="Calculation Result")
    action = CalculateExpression(
        expression=ref,
        uuid="693E408D-A668-49B2-BFDB-D4A9994E250A",
    )
    d = action.to_action_dict()
    params = d["WFWorkflowActionParameters"]

    assert d["WFWorkflowActionIdentifier"] == "is.workflow.actions.calculateexpression"
    assert params["UUID"] == "693E408D-A668-49B2-BFDB-D4A9994E250A"

    token_str = params["Input"]
    assert token_str["WFSerializationType"] == "WFTextTokenString"
    assert token_str["Value"]["string"] == _OBJECT_REPLACEMENT

    attachment = token_str["Value"]["attachmentsByRange"]["{0, 1}"]
    assert attachment["Type"] == "ActionOutput"
    assert attachment["OutputUUID"] == "7B56D5FA-ED27-4E45-A75D-3C187C8BBBC1"
    assert attachment["OutputName"] == "Calculation Result"


# ---------------------------------------------------------------------------
# Wire-equivalence vs corpus appearance 2 (dictionary.xml lines 4462-4492)
# ---------------------------------------------------------------------------


def test_wire_equivalence_corpus_appearance_2() -> None:
    """Round-trip matches corpus appearance 2 (dictionary.xml lines 4462-4492).

    The corpus action has:
    - Action UUID: 3BC08D42-C707-4A96-A120-19D583A9229E
    - Input: WFTextTokenString wrapping ActionOutput with
      OutputUUID 1686DF05-15FF-4E55-AB6C-BB86C77F3BFB,
      OutputName "Calculation Result"
    """
    ref = Output(uuid="1686DF05-15FF-4E55-AB6C-BB86C77F3BFB", name="Calculation Result")
    action = CalculateExpression(
        expression=ref,
        uuid="3BC08D42-C707-4A96-A120-19D583A9229E",
    )
    params = action.to_action_dict()["WFWorkflowActionParameters"]

    assert params["UUID"] == "3BC08D42-C707-4A96-A120-19D583A9229E"

    token_str = params["Input"]
    assert token_str["WFSerializationType"] == "WFTextTokenString"

    attachment = token_str["Value"]["attachmentsByRange"]["{0, 1}"]
    assert attachment["Type"] == "ActionOutput"
    assert attachment["OutputUUID"] == "1686DF05-15FF-4E55-AB6C-BB86C77F3BFB"
    assert attachment["OutputName"] == "Calculation Result"


# ---------------------------------------------------------------------------
# Action output chaining
# ---------------------------------------------------------------------------


def test_output_method_returns_calculation_result_name() -> None:
    """output() uses default_output_name when no custom name is set."""
    action = CalculateExpression(expression="1 + 1")
    ref = action.output()
    assert ref.name == "Calculation Result"
    assert ref.uuid == action.uuid


def test_chaining_expression_into_next_action() -> None:
    """A CalculateExpression output can feed into another expression slot."""
    first = CalculateExpression(expression="3 + 4")
    second = CalculateExpression(expression=first)

    params = _params(second)
    token_str = params["Input"]
    assert token_str["WFSerializationType"] == "WFTextTokenString"

    attachment = token_str["Value"]["attachmentsByRange"]["{0, 1}"]
    assert attachment["Type"] == "ActionOutput"
    assert attachment["OutputUUID"] == first.uuid
    assert attachment["OutputName"] == "Calculation Result"


# ---------------------------------------------------------------------------
# Guard: expression required
# ---------------------------------------------------------------------------


def test_missing_expression_raises_schema_error() -> None:
    """Omitting expression raises SchemaError at build time."""
    with pytest.raises(SchemaError, match="requires `expression`"):
        CalculateExpression().to_action_dict()
