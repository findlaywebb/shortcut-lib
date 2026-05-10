"""Tests for the DetectNumber action schema."""

from __future__ import annotations

from shortcut_lib.schema.actions.detect_number import DetectNumber
from shortcut_lib.schema.registry import lookup
from shortcut_lib.schema.values import Output

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _formatted_number_output() -> Output:
    """Return a sample ActionOutput reference matching corpus wire shape."""
    return Output(uuid="8DB53EA1-4E2D-4D11-A952-079C35C97119", name="Formatted Number")


# ---------------------------------------------------------------------------
# Wire-format tests
# ---------------------------------------------------------------------------


def test_detect_number_with_action_output_produces_attachment() -> None:
    """WFInput with an Output ref emits a WFTextTokenAttachment envelope.

    Confirmed against samples/decoded/dictionary.xml lines 355-368 (first
    appearance) and 4546-4559 (second appearance). Both show WFInput as a
    WFTextTokenAttachment pointing at the preceding FormatNumber action output.
    """
    ref = _formatted_number_output()
    action = DetectNumber(
        uuid="77CAA732-E639-47F3-B65A-3259960A52D9",
        input=ref,
    )
    result = action.to_action_dict()
    assert result["WFWorkflowActionIdentifier"] == "is.workflow.actions.detect.number"
    params = result["WFWorkflowActionParameters"]
    wf_input = params["WFInput"]
    assert wf_input["WFSerializationType"] == "WFTextTokenAttachment"
    assert wf_input["Value"]["Type"] == "ActionOutput"
    assert wf_input["Value"]["OutputUUID"] == "8DB53EA1-4E2D-4D11-A952-079C35C97119"
    assert wf_input["Value"]["OutputName"] == "Formatted Number"


def test_detect_number_corpus_wire_equivalence() -> None:
    """Emitted dict matches the corpus shape from dictionary.xml (1st appearance).

    Corpus UUID: 77CAA732-E639-47F3-B65A-3259960A52D9
    Input: ActionOutput from "Formatted Number" (8DB53EA1-4E2D-4D11-A952-079C35C97119)
    No extra keys beyond WFInput and UUID.
    """
    ref = _formatted_number_output()
    action = DetectNumber(
        uuid="77CAA732-E639-47F3-B65A-3259960A52D9",
        input=ref,
    )
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    # Only WFInput and UUID should be present
    assert set(params.keys()) == {"WFInput", "UUID"}
    assert params["UUID"] == "77CAA732-E639-47F3-B65A-3259960A52D9"


def test_detect_number_no_input_omits_wfinput() -> None:
    """When input is None, WFInput key is absent from emitted params."""
    action = DetectNumber()
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "WFInput" not in params


def test_detect_number_no_extra_params() -> None:
    """DetectNumber emits no parameters beyond WFInput (when set) and UUID."""
    action = DetectNumber(input=_formatted_number_output())
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert set(params.keys()) == {"WFInput", "UUID"}


def test_detect_number_string_input() -> None:
    """A plain string passes through as-is for WFInput."""
    action = DetectNumber(input="42.5 and 3.14")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFInput"] == "42.5 and 3.14"


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_detect_number_registered() -> None:
    """DetectNumber is findable in the registry by its identifier."""
    cls = lookup("is.workflow.actions.detect.number")
    assert cls is DetectNumber


def test_detect_number_default_output_name() -> None:
    """DetectNumber.default_output_name is 'Numbers'."""
    assert DetectNumber.default_output_name == "Numbers"


# ---------------------------------------------------------------------------
# Output reference chaining
# ---------------------------------------------------------------------------


def test_detect_number_output_reference() -> None:
    """output() returns an Output whose uuid matches the action's uuid."""
    action = DetectNumber(input="some text with 42")
    ref = action.output()
    assert ref.uuid == action.uuid


def test_detect_number_output_name_fallback() -> None:
    """output() name falls back to 'Numbers' when no custom name is set."""
    action = DetectNumber(input="some text")
    ref = action.output()
    assert ref.name == "Numbers"
