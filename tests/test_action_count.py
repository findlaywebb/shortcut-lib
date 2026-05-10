"""Tests for the Count action schema."""

from __future__ import annotations

import pytest

from shortcut_lib.schema.actions.count import Count
from shortcut_lib.schema.base import SchemaError
from shortcut_lib.schema.registry import list_actions, lookup

# ---------------------------------------------------------------------------
# Default behaviour
# ---------------------------------------------------------------------------


def test_count_default_type_is_items() -> None:
    """Default count_type is 'Items'; WFCountType = 'Items' always emitted.

    Confirmed: samples/decoded/combine_screenshots_and_share.xml carries
    WFCountType = 'Items' explicitly.
    """
    params = Count().to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFCountType"] == "Items"
    assert "Input" not in params


def test_count_no_input_omits_input_key() -> None:
    """When input is None, the Input key is absent from emitted params."""
    params = Count(count_type="Words").to_action_dict()["WFWorkflowActionParameters"]
    assert "Input" not in params
    assert params["WFCountType"] == "Words"


# ---------------------------------------------------------------------------
# Each count_type value
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "count_type",
    ["Items", "Characters", "Words", "Sentences", "Lines"],
)
def test_count_type_emitted(count_type: str) -> None:
    """Each WFCountType value round-trips through the wire format."""
    params = Count(count_type=count_type).to_action_dict()[  # ty: ignore[invalid-argument-type]
        "WFWorkflowActionParameters"
    ]
    assert params["WFCountType"] == count_type


# ---------------------------------------------------------------------------
# Input field wiring
# ---------------------------------------------------------------------------


def test_count_input_action_ref() -> None:
    """An Action reference in input emits a WFTextTokenAttachment envelope.

    Apple uses 'Input' (not 'WFInput') as the parameter key — confirmed
    against both corpus samples.
    """
    from shortcut_lib.schema.actions.get_clipboard import GetClipboard

    src = GetClipboard()
    params = Count(input=src, count_type="Characters").to_action_dict()[
        "WFWorkflowActionParameters"
    ]
    assert "Input" in params
    assert params["Input"]["WFSerializationType"] == "WFTextTokenAttachment"
    assert params["Input"]["Value"]["OutputUUID"] == src.uuid


def test_count_input_string() -> None:
    """A plain string in input is passed through as-is."""
    params = Count(input="hello", count_type="Words").to_action_dict()[
        "WFWorkflowActionParameters"
    ]
    assert params["Input"] == "hello"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_count_invalid_type_raises() -> None:
    """An unrecognised count_type raises SchemaError naming the bad value."""
    with pytest.raises(SchemaError, match="'Paragraphs'"):
        Count(count_type="Paragraphs")  # ty: ignore[invalid-argument-type]


# ---------------------------------------------------------------------------
# Registry + metadata
# ---------------------------------------------------------------------------


def test_count_registered() -> None:
    """Count is findable in the registry by its identifier."""
    cls = lookup("is.workflow.actions.count")
    assert cls is Count


def test_count_in_list_actions() -> None:
    """Count appears in list_actions() output."""
    identifiers = [a["identifier"] for a in list_actions()]
    assert "is.workflow.actions.count" in identifiers


def test_count_default_output_name() -> None:
    """default_output_name is 'Count'."""
    assert Count.default_output_name == "Count"


# ---------------------------------------------------------------------------
# Identifier
# ---------------------------------------------------------------------------


def test_count_identifier() -> None:
    """Count action emits the correct WFWorkflowActionIdentifier."""
    result = Count().to_action_dict()
    assert result["WFWorkflowActionIdentifier"] == "is.workflow.actions.count"
