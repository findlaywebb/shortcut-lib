"""Tests for the Number action schema.

Wire-format verification is grounded in ``samples/decoded/dictionary.xml``
(lines 284-291 and 4562-4569), where both corpus appearances carry only a
``UUID`` key — ``WFNumberActionNumber`` is absent.
"""

from __future__ import annotations

from shortcut_lib.schema.actions.number import Number
from shortcut_lib.schema.registry import lookup


def test_number_identifier() -> None:
    """Number carries the correct Apple action identifier."""
    assert Number.identifier == "is.workflow.actions.number"


def test_number_default_output_name() -> None:
    """output() resolves to 'Number' when no custom name is set."""
    action = Number()
    assert action.output().name == "Number"


def test_number_registered() -> None:
    """Number is discoverable from the action registry by identifier."""
    cls = lookup("is.workflow.actions.number")
    assert cls is Number


def test_number_no_value_omits_key() -> None:
    """With number=None (default), WFNumberActionNumber is absent from params.

    This reproduces the corpus wire format exactly: both samples carry
    only UUID in WFWorkflowActionParameters.
    """
    action = Number()
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "WFNumberActionNumber" not in params
    assert "UUID" in params


def test_number_integer_literal() -> None:
    """An integer value is emitted as WFNumberActionNumber."""
    action = Number(number=42)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFNumberActionNumber"] == 42


def test_number_float_literal() -> None:
    """A float value is emitted as WFNumberActionNumber."""
    action = Number(number=3.14)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFNumberActionNumber"] == 3.14


def test_number_zero_emits_key() -> None:
    """Passing 0 explicitly writes the key (distinguishable from None/absent)."""
    action = Number(number=0)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFNumberActionNumber"] == 0


def test_number_action_input_chaining() -> None:
    """Passing an Action as number chains its output reference via coerce_value."""
    from shortcut_lib.schema.actions.get_text import GetText

    source = GetText(text="5")
    action = Number(number=source)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    wire = params["WFNumberActionNumber"]
    assert wire["WFSerializationType"] == "WFTextTokenAttachment"
    assert wire["Value"]["OutputUUID"] == source.uuid
    assert wire["Value"]["Type"] == "ActionOutput"


def test_number_corpus_wire_equivalence() -> None:
    """to_action_dict() output matches the corpus wire shape exactly.

    Verified against dictionary.xml lines 284-291 and 4562-4569:
    WFWorkflowActionIdentifier = 'is.workflow.actions.number'
    WFWorkflowActionParameters = {UUID: <uuid>}   (no other keys)
    """
    action = Number(uuid="BF31D62D-3A6F-4C2F-92A3-245CEA74DE76")
    result = action.to_action_dict()
    assert result["WFWorkflowActionIdentifier"] == "is.workflow.actions.number"
    params = result["WFWorkflowActionParameters"]
    assert params == {"UUID": "BF31D62D-3A6F-4C2F-92A3-245CEA74DE76"}
