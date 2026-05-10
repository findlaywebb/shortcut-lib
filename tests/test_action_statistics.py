"""Tests for Statistics — is.workflow.actions.statistics."""

from __future__ import annotations

import pytest

from shortcut_lib.schema.actions.get_variable import GetVariable
from shortcut_lib.schema.actions.statistics import (
    _VALID_OPERATIONS,
    Statistics,
    WFStatisticsOperation,
)
from shortcut_lib.schema.base import SchemaError
from shortcut_lib.schema.registry import list_actions

# ---------------------------------------------------------------------------
# Identifier / registration
# ---------------------------------------------------------------------------


def test_statistics_registered() -> None:
    """Statistics appears in list_actions() under the correct identifier."""
    identifiers = {entry["identifier"] for entry in list_actions()}
    assert "is.workflow.actions.statistics" in identifiers


def test_statistics_identifier() -> None:
    """The class-level identifier matches the Apple action string."""
    assert Statistics.identifier == "is.workflow.actions.statistics"


# ---------------------------------------------------------------------------
# Default operation ("Average") — wire-format omission
# ---------------------------------------------------------------------------


def test_statistics_default_operation_omits_key() -> None:
    """Default operation "Average" is omitted from the wire dict.

    Both corpus appearances (samples/decoded/dictionary.xml lines 26 and 239)
    omit ``WFStatisticsOperation``, confirming "Average" is Apple's implicit
    default. The model must match this wire-identical emission.
    """
    action = Statistics()
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "WFStatisticsOperation" not in params


def test_statistics_default_operation_value() -> None:
    """The default operation attribute is 'Average'."""
    action = Statistics()
    assert action.operation == "Average"


# ---------------------------------------------------------------------------
# Each operation produces the correct WFStatisticsOperation wire key
# ---------------------------------------------------------------------------


NON_DEFAULT_OPERATIONS = (
    "Minimum",
    "Maximum",
    "Sum",
    "Count",
    "Range",
    "Median",
    "Mode",
    "Standard Deviation",
)


@pytest.mark.parametrize("op", NON_DEFAULT_OPERATIONS)
def test_statistics_non_default_operation_emits_key(op: str) -> None:
    """Non-default operations emit WFStatisticsOperation with the correct string."""
    action = Statistics(operation=op)  # ty: ignore[invalid-argument-type]
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFStatisticsOperation"] == op


def test_statistics_average_explicit_omits_key() -> None:
    """Explicitly passing 'Average' still omits the key (same as default)."""
    action = Statistics(operation="Average")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "WFStatisticsOperation" not in params


# ---------------------------------------------------------------------------
# Input parameter handling
# ---------------------------------------------------------------------------


def test_statistics_no_input_omits_key() -> None:
    """When input is None, Input is omitted from the wire dict."""
    action = Statistics()
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "Input" not in params


def test_statistics_action_input_produces_attachment() -> None:
    """Passing an Action as input emits WFTextTokenAttachment.

    Both corpus observations use WFTextTokenAttachment for Input
    (observed_envelope_types.json: 2 of 2). coerce_value on an Action
    → output().to_param() → WFTextTokenAttachment.
    """
    var = GetVariable(name="My Numbers")
    action = Statistics(input=var)
    params = action.to_action_dict()["WFWorkflowActionParameters"]

    assert "Input" in params
    inp = params["Input"]
    assert inp["WFSerializationType"] == "WFTextTokenAttachment"
    assert inp["Value"]["OutputUUID"] == var.uuid


def test_statistics_input_uuid_matches_source_action() -> None:
    """The Input OutputUUID matches the source action's uuid field."""
    var = GetVariable(name="Scores")
    stats = Statistics(input=var, operation="Sum")
    params = stats.to_action_dict()["WFWorkflowActionParameters"]
    assert params["Input"]["Value"]["OutputUUID"] == var.uuid


# ---------------------------------------------------------------------------
# Wire-format equivalence with corpus samples
# ---------------------------------------------------------------------------


def test_statistics_wire_format_default_matches_corpus() -> None:
    """Wire format for the default case matches corpus structure.

    Both corpus appearances (dictionary.xml) have:
    - No WFStatisticsOperation key
    - Input as WFTextTokenAttachment with ActionOutput type
    - UUID present

    This test validates the emitted structure matches the expected shape.
    """
    source_uuid = "693E408D-A668-49B2-BFDB-D4A9994E250A"
    source = GetVariable(name="Calculation Result", uuid=source_uuid)
    action = Statistics(input=source, uuid="A280C7C5-5E59-4AA0-986E-9262311695AA")

    result = action.to_action_dict()

    assert result["WFWorkflowActionIdentifier"] == "is.workflow.actions.statistics"
    params = result["WFWorkflowActionParameters"]
    assert params["UUID"] == "A280C7C5-5E59-4AA0-986E-9262311695AA"
    assert "WFStatisticsOperation" not in params
    inp = params["Input"]
    assert inp["WFSerializationType"] == "WFTextTokenAttachment"
    assert inp["Value"]["OutputUUID"] == source_uuid


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_statistics_invalid_operation_raises_schema_error() -> None:
    """An unrecognised operation raises SchemaError naming the bad value."""
    with pytest.raises(SchemaError, match="'Mean'"):
        Statistics(operation="Mean")  # ty: ignore[invalid-argument-type]


def test_statistics_invalid_operation_error_mentions_valid_set() -> None:
    """SchemaError for bad operation lists valid options."""
    with pytest.raises(SchemaError, match="Average"):
        Statistics(operation="Variance")  # ty: ignore[invalid-argument-type]


def test_statistics_all_valid_operations_accepted() -> None:
    """All nine operations in WFStatisticsOperation construct without error."""
    import typing

    all_ops = typing.get_args(WFStatisticsOperation)
    assert len(all_ops) == 9
    for op in all_ops:
        action = Statistics(operation=op)
        # Should not raise; emit a wire dict without error
        result = action.to_action_dict()
        assert result["WFWorkflowActionIdentifier"] == "is.workflow.actions.statistics"


def test_statistics_valid_operations_set_matches_literal() -> None:
    """_VALID_OPERATIONS is the exact frozenset of Literal args."""
    import typing

    expected = frozenset(typing.get_args(WFStatisticsOperation))
    assert expected == _VALID_OPERATIONS


# ---------------------------------------------------------------------------
# UUID is always emitted
# ---------------------------------------------------------------------------


def test_statistics_uuid_always_present() -> None:
    """UUID is always emitted in the wire dict (Apple requires it)."""
    action = Statistics()
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "UUID" in params
    assert len(params["UUID"]) == 36  # standard UUID string length
