"""Tests for BuildList — is.workflow.actions.list."""

from __future__ import annotations

import pytest

from shortcut_lib.schema.actions.get_text import GetText
from shortcut_lib.schema.actions.list import BuildList
from shortcut_lib.schema.base import SchemaError
from shortcut_lib.schema.registry import list_actions
from shortcut_lib.schema.values import NamedVar

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _params(b: BuildList) -> dict:
    return b.to_action_dict()["WFWorkflowActionParameters"]


# ---------------------------------------------------------------------------
# Empty list
# ---------------------------------------------------------------------------


def test_empty_list_omits_wfitems() -> None:
    """An empty BuildList emits no WFItems — matches Apple GUI wire format.

    Confirmed via samples/decoded/dictionary.xml: the list action there has
    only UUID in its WFWorkflowActionParameters, no WFItems key at all.
    """
    b = BuildList()
    params = _params(b)
    assert "WFItems" not in params
    assert set(params) == {"UUID"}


def test_empty_list_via_explicit_arg() -> None:
    """Explicitly passing items=[] also produces no WFItems key."""
    b = BuildList(items=[])
    params = _params(b)
    assert "WFItems" not in params


# ---------------------------------------------------------------------------
# One-item list
# ---------------------------------------------------------------------------


def test_one_item_list() -> None:
    """A single-item list emits WFItems as a one-element array."""
    b = BuildList(items=["Hello"])
    params = _params(b)

    assert params["WFItems"] == ["Hello"]
    assert len(params["WFItems"]) == 1


# ---------------------------------------------------------------------------
# Multi-item list
# ---------------------------------------------------------------------------


def test_multi_item_list_preserves_order() -> None:
    """Multi-item list emits items in insertion order.

    Matches the pattern from samples/decoded/set_weekend_chores.xml where
    WFItems is a plain <array> of <string> elements in the authored order.
    """
    items = ["Sweeping", "Mopping", "Vacuuming", "Dusting", "Washing"]
    b = BuildList(items=items)
    params = _params(b)

    assert params["WFItems"] == items


def test_chores_wire_format_equivalence() -> None:
    """Wire format matches the set_weekend_chores.xml corpus sample exactly.

    Sample UUID is 5ACF1422-8187-4840-9ACF-142281878840.
    We pin our own UUID to verify the rest of the envelope is correct.
    """
    chores = [
        "Sweeping",
        "Mopping",
        "Vacuuming",
        "Dusting",
        "Washing",
        "Change the bed",
        "Clean the bathroom",
        "Take out the recycling",
    ]
    b = BuildList(
        items=chores,
        uuid="5ACF1422-8187-4840-9ACF-142281878840",
    )
    action_dict = b.to_action_dict()

    assert action_dict["WFWorkflowActionIdentifier"] == "is.workflow.actions.list"
    params = action_dict["WFWorkflowActionParameters"]
    assert params["UUID"] == "5ACF1422-8187-4840-9ACF-142281878840"
    assert params["WFItems"] == chores


# ---------------------------------------------------------------------------
# Type validation — non-string items
# ---------------------------------------------------------------------------


def test_action_item_raises_schema_error() -> None:
    """Passing an Action as a list item raises SchemaError with guidance.

    Variable references cannot be individual list items in Apple's wire
    format — the WFItems array is always a plain <array> of <string>.
    """
    source = GetText(text="dynamic")
    b = BuildList(items=[source])  # ty: ignore[invalid-argument-type]  # intentional bad type
    with pytest.raises(SchemaError, match="plain strings"):
        b.to_action_dict()


def test_named_var_item_raises_schema_error() -> None:
    """Passing a NamedVar as a list item raises SchemaError."""
    var = NamedVar("MyVar")
    b = BuildList(items=[var])  # ty: ignore[invalid-argument-type]  # intentional bad type
    with pytest.raises(SchemaError, match="plain strings"):
        b.to_action_dict()


def test_integer_item_raises_schema_error() -> None:
    """Passing a non-string primitive raises SchemaError with the type name."""
    b = BuildList(items=[42])  # ty: ignore[invalid-argument-type]  # intentional bad type
    with pytest.raises(SchemaError, match="'int'"):
        b.to_action_dict()


# ---------------------------------------------------------------------------
# Identifier and registry
# ---------------------------------------------------------------------------


def test_identifier() -> None:
    """BuildList carries the correct Apple action identifier."""
    assert BuildList.identifier == "is.workflow.actions.list"


def test_default_output_name() -> None:
    """Default output name is 'List' — confirmed from downstream OutputName refs."""
    assert BuildList.default_output_name == "List"


def test_registered_in_registry() -> None:
    """BuildList appears in the action registry under the correct identifier."""
    identifiers = {entry["identifier"] for entry in list_actions()}
    assert "is.workflow.actions.list" in identifiers


# ---------------------------------------------------------------------------
# Output reference
# ---------------------------------------------------------------------------


def test_output_reference_uses_default_name() -> None:
    """output() produces a reference with name 'List' by default."""
    b = BuildList(items=["a", "b"])
    ref = b.output()
    param = ref.to_param()

    assert param["WFSerializationType"] == "WFTextTokenAttachment"
    assert param["Value"]["OutputUUID"] == b.uuid
    assert param["Value"]["OutputName"] == "List"
    assert param["Value"]["Type"] == "ActionOutput"


def test_output_reference_custom_name() -> None:
    """output('Chores') overrides the default output name in the reference."""
    b = BuildList(items=["Sweep"])
    ref = b.output("Chores")
    param = ref.to_param()

    assert param["Value"]["OutputName"] == "Chores"
