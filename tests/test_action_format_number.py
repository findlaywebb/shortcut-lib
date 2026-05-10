"""Tests for the FormatNumber action schema."""

from __future__ import annotations

from shortcut_lib.schema.actions.format_number import FormatNumber
from shortcut_lib.schema.registry import lookup
from shortcut_lib.schema.values import Output

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _prev_action_output() -> Output:
    """Return a sample ActionOutput reference matching corpus wire shape."""
    return Output(uuid="AC7B3655-7E12-4D60-A7FF-C7F5D9233F9D", name="Rounded Number")


# ---------------------------------------------------------------------------
# Wire-format tests
# ---------------------------------------------------------------------------


def test_format_number_with_action_output_produces_attachment() -> None:
    """WFNumber with an Output ref emits a WFTextTokenAttachment envelope.

    Confirmed against samples/decoded/dictionary.xml lines 332-345 (first
    appearance) and 4523-4536 (second appearance). Both show WFNumber as a
    WFTextTokenAttachment, NOT a WFTextTokenString.
    """
    ref = _prev_action_output()
    action = FormatNumber(
        uuid="8DB53EA1-4E2D-4D11-A952-079C35C97119",
        number=ref,
    )
    result = action.to_action_dict()
    assert result["WFWorkflowActionIdentifier"] == "is.workflow.actions.format.number"
    params = result["WFWorkflowActionParameters"]
    wf_number = params["WFNumber"]
    assert wf_number["WFSerializationType"] == "WFTextTokenAttachment"
    assert wf_number["Value"]["Type"] == "ActionOutput"
    assert wf_number["Value"]["OutputUUID"] == "AC7B3655-7E12-4D60-A7FF-C7F5D9233F9D"
    assert wf_number["Value"]["OutputName"] == "Rounded Number"


def test_format_number_corpus_wire_equivalence() -> None:
    """Emitted dict matches the corpus shape from dictionary.xml (1st appearance).

    Corpus UUID: 8DB53EA1-4E2D-4D11-A952-079C35C97119
    Input: ActionOutput from "Rounded Number" (AC7B3655-7E12-4D60-A7FF-C7F5D9233F9D)
    No WFNumberFormatDecimalPlaces in corpus — key must be absent.
    """
    ref = _prev_action_output()
    action = FormatNumber(
        uuid="8DB53EA1-4E2D-4D11-A952-079C35C97119",
        number=ref,
    )
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "WFNumberFormatDecimalPlaces" not in params
    assert params["UUID"] == "8DB53EA1-4E2D-4D11-A952-079C35C97119"


def test_format_number_with_decimal_places() -> None:
    """WFNumberFormatDecimalPlaces is emitted when decimal_places is set."""
    action = FormatNumber(number=42.5, decimal_places=0)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFNumberFormatDecimalPlaces"] == 0


def test_format_number_decimal_places_of_4() -> None:
    """decimal_places=4 emits the integer 4 verbatim."""
    action = FormatNumber(number=3.14159, decimal_places=4)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFNumberFormatDecimalPlaces"] == 4


def test_format_number_no_input_omits_wfnumber() -> None:
    """When number is None, WFNumber key is absent from emitted params."""
    action = FormatNumber()
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "WFNumber" not in params
    assert "WFNumberFormatDecimalPlaces" not in params


def test_format_number_scalar_int() -> None:
    """A plain int scalar is passed through as-is for WFNumber."""
    action = FormatNumber(number=100)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFNumber"] == 100


def test_format_number_scalar_float() -> None:
    """A plain float scalar is passed through as-is for WFNumber."""
    action = FormatNumber(number=1.5)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFNumber"] == 1.5


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_format_number_registered() -> None:
    """FormatNumber is findable in the registry by its identifier."""
    cls = lookup("is.workflow.actions.format.number")
    assert cls is FormatNumber


def test_format_number_default_output_name() -> None:
    """FormatNumber.default_output_name is 'Formatted Number'."""
    assert FormatNumber.default_output_name == "Formatted Number"


# ---------------------------------------------------------------------------
# Output reference chaining
# ---------------------------------------------------------------------------


def test_format_number_output_reference() -> None:
    """output() returns an Output whose uuid matches the action's uuid."""
    action = FormatNumber(number=42)
    ref = action.output()
    assert ref.uuid == action.uuid


def test_format_number_output_name_fallback() -> None:
    """output() name falls back to 'Formatted Number' when no custom name is set."""
    action = FormatNumber(number=42)
    ref = action.output()
    assert ref.name == "Formatted Number"
