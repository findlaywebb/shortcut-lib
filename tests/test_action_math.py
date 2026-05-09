"""Tests for the Math action schema (is.workflow.actions.math)."""

from __future__ import annotations

import copy
import plistlib
from pathlib import Path
from typing import Any

import pytest

from shortcut_lib.schema.actions.math import (
    Math,
)
from shortcut_lib.schema.base import SchemaError
from shortcut_lib.schema.registry import lookup
from shortcut_lib.schema.values import Output

DECODED = Path(__file__).parent.parent / "samples" / "decoded"
DICTIONARY = DECODED / "dictionary.xml"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load(path: Path) -> dict[str, Any]:
    """Load a decoded plist XML file and return its top-level dict."""
    return plistlib.loads(path.read_bytes())


def _strip_output_uuids(obj: Any) -> None:
    """Recursively strip OutputUUID from all dicts."""
    if isinstance(obj, dict):
        obj.pop("OutputUUID", None)
        for v in obj.values():
            _strip_output_uuids(v)
    elif isinstance(obj, list):
        for v in obj:
            _strip_output_uuids(v)


def _normalise(action_dict: dict[str, Any]) -> dict[str, Any]:
    """Strip non-deterministic UUID fields before comparing."""
    out = copy.deepcopy(action_dict)
    params = out.get("WFWorkflowActionParameters", {})
    params.pop("UUID", None)
    params.pop("CustomOutputName", None)
    _strip_output_uuids(params)
    return out


# ---------------------------------------------------------------------------
# Default / omit-if-default behaviour
# ---------------------------------------------------------------------------


def test_math_all_defaults_empty_params() -> None:
    """Math() with no args emits no WFInput, WFMathOperation, or WFMathOperand.

    Both corpus appearances omit all three keys (dictionary.xml:373 omits
    WFMathOperation / WFMathOperand; dictionary.xml:4455 omits everything).
    This confirms the all-defaults behaviour.
    """
    action = Math()
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "WFInput" not in params
    assert "WFMathOperation" not in params
    assert "WFMathOperand" not in params
    assert "scientific" not in params


def test_math_default_operation_plus_omitted() -> None:
    """WFMathOperation is omitted when operation is '+' (the wire-format default).

    Confirmed: dictionary.xml:373 carries WFInput but no WFMathOperation,
    which Apple interprets as addition.
    """
    prev = Output(uuid="77CAA732-E639-47F3-B65A-3259960A52D9", name="Numbers")
    action = Math(input=prev, operation="+", operand=10)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "WFMathOperation" not in params
    assert "WFInput" in params
    assert params["WFMathOperand"] == 10


def test_math_input_encoded_as_text_token_attachment() -> None:
    """WFInput is encoded as WFTextTokenAttachment when an Output is provided.

    Confirmed against dictionary.xml:373 where WFInput carries an
    OutputName/OutputUUID attachment from a preceding 'Numbers' action.
    """
    prev = Output(uuid="77CAA732-E639-47F3-B65A-3259960A52D9", name="Numbers")
    action = Math(input=prev)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFInput"]["WFSerializationType"] == "WFTextTokenAttachment"


# ---------------------------------------------------------------------------
# Arithmetic operations
# ---------------------------------------------------------------------------


def test_math_subtraction() -> None:
    """'−' (U+2212 MINUS SIGN) is emitted as WFMathOperation for subtraction."""
    action = Math(operation="−", operand=5)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFMathOperation"] == "−"
    assert params["WFMathOperand"] == 5


def test_math_multiplication() -> None:
    """'×' (U+00D7) is emitted as WFMathOperation for multiplication."""
    action = Math(operation="×", operand=3)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFMathOperation"] == "×"


def test_math_division() -> None:
    """'÷' (U+00F7) is emitted as WFMathOperation for division."""
    action = Math(operation="÷", operand=2)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFMathOperation"] == "÷"


def test_math_modulo() -> None:
    """'Modulo' is emitted as WFMathOperation for the remainder operation."""
    action = Math(operation="Modulo", operand=7)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFMathOperation"] == "Modulo"
    assert params["WFMathOperand"] == 7


def test_math_no_operand_omits_wfmathoperand() -> None:
    """WFMathOperand is absent when operand is None."""
    action = Math(operation="×")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "WFMathOperand" not in params


def test_math_operand_action_output() -> None:
    """WFMathOperand accepts an Output reference (WFTextTokenAttachment)."""
    second = Output(uuid="AAAA-BBBB-CCCC-DDDD", name="Divisor")
    action = Math(operation="÷", operand=second)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFMathOperand"]["WFSerializationType"] == "WFTextTokenAttachment"


# ---------------------------------------------------------------------------
# Scientific / unary operations
# ---------------------------------------------------------------------------


def test_math_scientific_square_root() -> None:
    """scientific_operation='√' emits the 'scientific' key; WFMathOperation absent."""
    action = Math(scientific_operation="√")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["scientific"] == "√"
    assert "WFMathOperation" not in params


def test_math_scientific_sine() -> None:
    """scientific_operation='sin(x)' is emitted correctly."""
    action = Math(scientific_operation="sin(x)")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["scientific"] == "sin(x)"


def test_math_scientific_cosine() -> None:
    """scientific_operation='cos(x)' is emitted correctly."""
    action = Math(scientific_operation="cos(x)")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["scientific"] == "cos(x)"


def test_math_scientific_log() -> None:
    """scientific_operation='log(x)' is emitted correctly."""
    action = Math(scientific_operation="log(x)")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["scientific"] == "log(x)"


def test_math_scientific_absolute_value() -> None:
    """scientific_operation='abs(x)' is emitted correctly."""
    action = Math(scientific_operation="abs(x)")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["scientific"] == "abs(x)"


def test_math_scientific_cube_root() -> None:
    """scientific_operation='∛' (U+221B CUBE ROOT) is emitted correctly."""
    action = Math(scientific_operation="∛")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["scientific"] == "∛"


def test_math_scientific_xpy_emits_operand() -> None:
    """x^y emits WFMathOperand (the exponent); only scientific op to do so."""
    action = Math(scientific_operation="x^y", operand=3)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["scientific"] == "x^y"
    assert params["WFMathOperand"] == 3


def test_math_scientific_xpy_no_operand_omits_wfmathoperand() -> None:
    """x^y without operand omits WFMathOperand."""
    action = Math(scientific_operation="x^y")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["scientific"] == "x^y"
    assert "WFMathOperand" not in params


def test_math_scientific_non_xpy_operand_ignored() -> None:
    """Operand is not emitted for scientific ops other than x^y."""
    action = Math(scientific_operation="sin(x)", operand=45)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "WFMathOperand" not in params


# ---------------------------------------------------------------------------
# Validation / SchemaError
# ---------------------------------------------------------------------------


def test_math_invalid_operation_raises() -> None:
    """An unrecognised arithmetic operation raises SchemaError."""
    with pytest.raises(SchemaError, match="'/'"):
        Math(operation="/")  # ty: ignore[invalid-argument-type]


def test_math_invalid_scientific_raises() -> None:
    """An unrecognised scientific operation raises SchemaError."""
    with pytest.raises(SchemaError, match="'sqrt'"):
        Math(scientific_operation="sqrt")  # ty: ignore[invalid-argument-type]


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_math_registered() -> None:
    """Math is findable in the registry by its identifier."""
    cls = lookup("is.workflow.actions.math")
    assert cls is Math


def test_math_default_output_name() -> None:
    """Math.default_output_name is 'Calculation Result'."""
    assert Math.default_output_name == "Calculation Result"


def test_math_identifier() -> None:
    """Math.identifier matches Apple's wire-format identifier."""
    assert Math.identifier == "is.workflow.actions.math"


# ---------------------------------------------------------------------------
# Wire-format equivalence — corpus sample 1 (dictionary.xml:373)
# ---------------------------------------------------------------------------


def test_math_wire_format_sample1() -> None:
    """Math with WFInput from Output matches corpus sample at dictionary.xml:373.

    The sample carries WFInput as a WFTextTokenAttachment for the 'Numbers'
    output but no WFMathOperation or WFMathOperand — confirming all-default
    arithmetic mode with '+' omitted from the wire format.
    """
    plist_data = _load(DICTIONARY)
    actions = plist_data["WFWorkflowActions"]

    # Locate the first math action (line 373 = action index near the beginning)
    math_actions = [
        a
        for a in actions
        if a["WFWorkflowActionIdentifier"] == "is.workflow.actions.math"
    ]
    assert len(math_actions) >= 1, "Expected at least one math action in dictionary.xml"

    corpus_action = math_actions[0]
    corpus_params = corpus_action["WFWorkflowActionParameters"]

    # Build an equivalent action using our model, using the same Output UUID
    input_uuid = corpus_params["WFInput"]["Value"]["OutputUUID"]
    input_name = corpus_params["WFInput"]["Value"]["OutputName"]
    prev = Output(uuid=input_uuid, name=input_name)
    action = Math(input=prev, uuid=corpus_params["UUID"])

    our_dict = action.to_action_dict()

    # Normalise and compare
    assert _normalise(our_dict) == _normalise(corpus_action)


# ---------------------------------------------------------------------------
# Wire-format equivalence — corpus sample 2 (dictionary.xml:4455)
# ---------------------------------------------------------------------------


def test_math_wire_format_sample2() -> None:
    """Math with all defaults matches the bare corpus action at dictionary.xml:4455.

    The second corpus appearance contains only a UUID — no WFInput,
    WFMathOperation, or WFMathOperand — confirming the all-defaults
    wire format is a single-key params dict.
    """
    plist_data = _load(DICTIONARY)
    actions = plist_data["WFWorkflowActions"]

    math_actions = [
        a
        for a in actions
        if a["WFWorkflowActionIdentifier"] == "is.workflow.actions.math"
    ]
    assert len(math_actions) >= 2, (
        "Expected at least two math actions in dictionary.xml"
    )

    corpus_action = math_actions[1]
    corpus_uuid = corpus_action["WFWorkflowActionParameters"]["UUID"]

    action = Math(uuid=corpus_uuid)
    assert _normalise(action.to_action_dict()) == _normalise(corpus_action)
