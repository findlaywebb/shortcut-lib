"""Tests for the GetItemFromList action schema."""

from __future__ import annotations

import pytest

from shortcut_lib.schema.actions.get_item_from_list import GetItemFromList
from shortcut_lib.schema.base import SchemaError
from shortcut_lib.schema.registry import list_actions, lookup

# ---------------------------------------------------------------------------
# Default / First Item
# ---------------------------------------------------------------------------


def test_first_item_default_specifier() -> None:
    """Default specifier is 'First Item'; WFItemSpecifier omitted from wire format.

    Confirmed: samples/decoded/dictionary.xml and tile_last_2_windows.xml
    both have a getitemfromlist block with no WFItemSpecifier key, meaning
    Shortcuts.app treats absence as 'First Item'.
    """
    action = GetItemFromList()
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "WFItemSpecifier" not in params
    assert "WFItemIndex" not in params
    assert "WFItemRangeStart" not in params
    assert "WFItemRangeEnd" not in params


def test_first_item_factory() -> None:
    """GetItemFromList.first() omits WFItemSpecifier key."""
    params = GetItemFromList.first().to_action_dict()["WFWorkflowActionParameters"]
    assert "WFItemSpecifier" not in params


def test_first_item_explicit_specifier_omits_key() -> None:
    """Explicitly passing specifier='First Item' still omits WFItemSpecifier."""
    params = GetItemFromList(specifier="First Item").to_action_dict()[
        "WFWorkflowActionParameters"
    ]
    assert "WFItemSpecifier" not in params


# ---------------------------------------------------------------------------
# Last Item
# ---------------------------------------------------------------------------


def test_last_item_emits_specifier() -> None:
    """'Last Item' specifier emits WFItemSpecifier = 'Last Item'.

    Confirmed: samples/decoded/tile_last_2_windows.xml contains
    WFItemSpecifier = 'Last Item'.
    """
    params = GetItemFromList(specifier="Last Item").to_action_dict()[
        "WFWorkflowActionParameters"
    ]
    assert params["WFItemSpecifier"] == "Last Item"
    assert "WFItemIndex" not in params


def test_last_item_factory() -> None:
    """GetItemFromList.last() sets WFItemSpecifier = 'Last Item'."""
    params = GetItemFromList.last().to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFItemSpecifier"] == "Last Item"


# ---------------------------------------------------------------------------
# Random Item
# ---------------------------------------------------------------------------


def test_random_item_emits_specifier() -> None:
    """'Random Item' specifier emits WFItemSpecifier = 'Random Item'."""
    params = GetItemFromList(specifier="Random Item").to_action_dict()[
        "WFWorkflowActionParameters"
    ]
    assert params["WFItemSpecifier"] == "Random Item"
    assert "WFItemIndex" not in params


def test_random_item_factory() -> None:
    """GetItemFromList.random() sets WFItemSpecifier = 'Random Item'."""
    params = GetItemFromList.random().to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFItemSpecifier"] == "Random Item"


# ---------------------------------------------------------------------------
# Item At Index
# ---------------------------------------------------------------------------


def test_at_index_emits_specifier_and_index() -> None:
    """'Item At Index' emits WFItemSpecifier and WFItemIndex."""
    params = GetItemFromList(specifier="Item At Index", index=3).to_action_dict()[
        "WFWorkflowActionParameters"
    ]
    assert params["WFItemSpecifier"] == "Item At Index"
    assert params["WFItemIndex"] == 3


def test_at_index_factory() -> None:
    """GetItemFromList.at_index() sets specifier and index."""
    params = GetItemFromList.at_index(index=2).to_action_dict()[
        "WFWorkflowActionParameters"
    ]
    assert params["WFItemSpecifier"] == "Item At Index"
    assert params["WFItemIndex"] == 2


def test_at_index_without_index_raises() -> None:
    """specifier='Item At Index' without index raises SchemaError."""
    with pytest.raises(SchemaError, match="index must be set"):
        GetItemFromList(specifier="Item At Index")


def test_index_on_wrong_specifier_raises() -> None:
    """Passing index with specifier != 'Item At Index' raises SchemaError."""
    with pytest.raises(SchemaError, match="only applies to specifier"):
        GetItemFromList(specifier="Last Item", index=1)


# ---------------------------------------------------------------------------
# Item Range
# ---------------------------------------------------------------------------


def test_item_range_emits_specifier_and_range() -> None:
    """'Item Range' emits WFItemSpecifier, WFItemRangeStart, WFItemRangeEnd."""
    params = GetItemFromList(
        specifier="Item Range", range_start=1, range_end=5
    ).to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFItemSpecifier"] == "Item Range"
    assert params["WFItemRangeStart"] == 1
    assert params["WFItemRangeEnd"] == 5


def test_item_range_factory() -> None:
    """GetItemFromList.range() sets specifier and both range bounds."""
    params = GetItemFromList.range(range_start=2, range_end=4).to_action_dict()[
        "WFWorkflowActionParameters"
    ]
    assert params["WFItemSpecifier"] == "Item Range"
    assert params["WFItemRangeStart"] == 2
    assert params["WFItemRangeEnd"] == 4


def test_item_range_missing_start_raises() -> None:
    """specifier='Item Range' with range_end but no range_start raises SchemaError."""
    with pytest.raises(SchemaError, match="range_start and range_end must both be set"):
        GetItemFromList(specifier="Item Range", range_end=5)


def test_item_range_missing_end_raises() -> None:
    """specifier='Item Range' with range_start but no range_end raises SchemaError."""
    with pytest.raises(SchemaError, match="range_start and range_end must both be set"):
        GetItemFromList(specifier="Item Range", range_start=1)


def test_range_fields_on_wrong_specifier_raises() -> None:
    """Passing range fields with a non-range specifier raises SchemaError."""
    with pytest.raises(SchemaError, match='only apply to specifier="Item Range"'):
        GetItemFromList(specifier="First Item", range_start=1, range_end=3)


# ---------------------------------------------------------------------------
# Input field wiring
# ---------------------------------------------------------------------------


def test_input_none_omits_wfinput() -> None:
    """When input is None, WFInput is absent from emitted params."""
    params = GetItemFromList(specifier="Last Item").to_action_dict()[
        "WFWorkflowActionParameters"
    ]
    assert "WFInput" not in params


def test_input_action_ref_emitted() -> None:
    """An Action reference in input emits a WFTextTokenAttachment envelope."""
    from shortcut_lib.schema.actions.get_clipboard import GetClipboard

    src = GetClipboard()
    params = GetItemFromList(input=src, specifier="Last Item").to_action_dict()[
        "WFWorkflowActionParameters"
    ]
    assert params["WFInput"]["WFSerializationType"] == "WFTextTokenAttachment"
    assert params["WFInput"]["Value"]["OutputUUID"] == src.uuid


# ---------------------------------------------------------------------------
# Invalid specifier
# ---------------------------------------------------------------------------


def test_invalid_specifier_raises() -> None:
    """An unrecognised specifier raises SchemaError naming the bad value."""
    with pytest.raises(SchemaError, match="'Nth Item'"):
        GetItemFromList(
            specifier="Nth Item"  # ty: ignore[invalid-argument-type]
        )


# ---------------------------------------------------------------------------
# Registry + metadata
# ---------------------------------------------------------------------------


def test_get_item_from_list_registered() -> None:
    """GetItemFromList is findable in the registry by its identifier."""
    cls = lookup("is.workflow.actions.getitemfromlist")
    assert cls is GetItemFromList


def test_get_item_from_list_in_list_actions() -> None:
    """GetItemFromList appears in list_actions() output."""
    identifiers = [a["identifier"] for a in list_actions()]
    assert "is.workflow.actions.getitemfromlist" in identifiers


def test_default_output_name() -> None:
    """default_output_name matches Apple's wire value seen in tile_last_2_windows.xml."""
    assert GetItemFromList.default_output_name == "Item from List"


# ---------------------------------------------------------------------------
# Equivalence: factory vs direct constructor
# ---------------------------------------------------------------------------


def test_last_factory_equals_direct() -> None:
    """Factory params are identical to direct constructor for 'Last Item'."""
    via_factory = GetItemFromList.last(list_input=None).to_action_dict()[
        "WFWorkflowActionParameters"
    ]
    via_direct = GetItemFromList(specifier="Last Item").to_action_dict()[
        "WFWorkflowActionParameters"
    ]
    via_factory.pop("UUID", None)
    via_direct.pop("UUID", None)
    assert via_factory == via_direct


def test_at_index_factory_equals_direct() -> None:
    """at_index() factory params match direct constructor."""
    via_factory = GetItemFromList.at_index(index=5).to_action_dict()[
        "WFWorkflowActionParameters"
    ]
    via_direct = GetItemFromList(specifier="Item At Index", index=5).to_action_dict()[
        "WFWorkflowActionParameters"
    ]
    via_factory.pop("UUID", None)
    via_direct.pop("UUID", None)
    assert via_factory == via_direct
