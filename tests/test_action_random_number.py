"""Tests for the RandomNumber action schema.

Wire-format verification is grounded in ``samples/decoded/dictionary.xml``
(lines 293-300 and 4571-4578), where both corpus appearances carry only a
``UUID`` key — neither bound key is present.

Output-name verification: the downstream ``round`` action at lines 302-323
and 4580-4601 references this action's output as ``"Random Number"``,
confirming :attr:`RandomNumber.default_output_name`.
"""

from __future__ import annotations

from shortcut_lib.schema.actions.random_number import RandomNumber
from shortcut_lib.schema.registry import lookup


def test_random_number_identifier() -> None:
    """RandomNumber carries the correct Apple action identifier."""
    assert RandomNumber.identifier == "is.workflow.actions.number.random"


def test_random_number_default_output_name() -> None:
    """output() resolves to 'Random Number' when no custom name is set.

    Confirmed by downstream round-action reference at dictionary.xml
    lines 314 (OutputName = 'Random Number') and 4592.
    """
    action = RandomNumber()
    assert action.output().name == "Random Number"


def test_random_number_registered() -> None:
    """RandomNumber is discoverable from the action registry by identifier."""
    cls = lookup("is.workflow.actions.number.random")
    assert cls is RandomNumber


def test_random_number_no_bounds_omits_keys() -> None:
    """With default bounds (None), neither WFRandom key appears in params.

    Reproduces the corpus wire format exactly: both samples carry only
    UUID in WFWorkflowActionParameters.
    """
    action = RandomNumber()
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "WFRandomNumberMinimum" not in params
    assert "WFRandomNumberMaximum" not in params
    assert "UUID" in params


def test_random_number_minimum_only() -> None:
    """Setting minimum emits WFRandomNumberMinimum; maximum stays absent."""
    action = RandomNumber(minimum=1)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFRandomNumberMinimum"] == 1
    assert "WFRandomNumberMaximum" not in params


def test_random_number_maximum_only() -> None:
    """Setting maximum emits WFRandomNumberMaximum; minimum stays absent."""
    action = RandomNumber(maximum=100)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFRandomNumberMaximum"] == 100
    assert "WFRandomNumberMinimum" not in params


def test_random_number_both_bounds() -> None:
    """Both bounds emit the correct wire keys when both are set."""
    action = RandomNumber(minimum=1, maximum=6)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFRandomNumberMinimum"] == 1
    assert params["WFRandomNumberMaximum"] == 6


def test_random_number_float_bounds() -> None:
    """Float bounds are passed through as-is to the wire format."""
    action = RandomNumber(minimum=0.5, maximum=9.9)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFRandomNumberMinimum"] == 0.5
    assert params["WFRandomNumberMaximum"] == 9.9


def test_random_number_action_input_chaining() -> None:
    """Passing an Action as a bound chains its output reference via coerce_value."""
    from shortcut_lib.schema.actions.number import Number

    low = Number(number=1)
    high = Number(number=100)
    action = RandomNumber(minimum=low, maximum=high)
    params = action.to_action_dict()["WFWorkflowActionParameters"]

    min_wire = params["WFRandomNumberMinimum"]
    max_wire = params["WFRandomNumberMaximum"]
    assert min_wire["WFSerializationType"] == "WFTextTokenAttachment"
    assert min_wire["Value"]["OutputUUID"] == low.uuid
    assert max_wire["WFSerializationType"] == "WFTextTokenAttachment"
    assert max_wire["Value"]["OutputUUID"] == high.uuid


def test_random_number_corpus_wire_equivalence() -> None:
    """to_action_dict() output matches the corpus wire shape exactly.

    Verified against dictionary.xml lines 293-300 and 4571-4578:
    WFWorkflowActionIdentifier = 'is.workflow.actions.number.random'
    WFWorkflowActionParameters = {UUID: <uuid>}   (no other keys)
    """
    action = RandomNumber(uuid="BB37E983-4ED1-48FD-960D-3AE7FA5BAD3D")
    result = action.to_action_dict()
    assert result["WFWorkflowActionIdentifier"] == "is.workflow.actions.number.random"
    params = result["WFWorkflowActionParameters"]
    assert params == {"UUID": "BB37E983-4ED1-48FD-960D-3AE7FA5BAD3D"}
