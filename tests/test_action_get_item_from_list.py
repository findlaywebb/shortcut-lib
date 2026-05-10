"""Tests for GetItemFromList — is.workflow.actions.getitemfromlist.

Corpus sources (3 appearances):
  - samples/decoded/dictionary.xml:185-204           (first-item default)
  - samples/decoded/tile_last_2_windows.xml:24-43    (first-item default)
  - samples/decoded/tile_last_2_windows.xml:70-93    (last-item + quirky WFItemIndex)
"""

from __future__ import annotations

import pytest

from shortcut_lib.schema.actions.get_item_from_list import (
    _VALID_SPECIFIERS,
    GetItemFromList,
)
from shortcut_lib.schema.base import SchemaError
from shortcut_lib.schema.registry import lookup
from shortcut_lib.schema.values import Output

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _params(action: GetItemFromList) -> dict:
    return action.to_action_dict()["WFWorkflowActionParameters"]


def _fake_output() -> Output:
    """Return a stable Output reference for testing WFInput emission."""
    return Output(uuid="A4FED113-114F-4E15-8F4D-ADA2BAC93FF3", name="Windows")


# ---------------------------------------------------------------------------
# Specifier defaults and wire-format omission
# ---------------------------------------------------------------------------


def test_first_item_is_default() -> None:
    """Default specifier is 'First Item' and WFItemSpecifier is omitted on wire.

    Corpus: dictionary.xml:185-204 and tile_last_2_windows.xml:24-43
    both have no WFItemSpecifier key — Apple omits the default.
    """
    params = _params(GetItemFromList(list_input=_fake_output()))
    assert "WFItemSpecifier" not in params


def test_non_default_specifier_is_emitted() -> None:
    """WFItemSpecifier appears for any specifier other than the default."""
    params = _params(GetItemFromList(list_input=_fake_output(), specifier="Last Item"))
    assert params["WFItemSpecifier"] == "Last Item"


def test_last_item_specifier() -> None:
    """'Last Item' specifier emits correctly."""
    params = _params(GetItemFromList(list_input=_fake_output(), specifier="Last Item"))
    assert params["WFItemSpecifier"] == "Last Item"
    assert "WFItemIndex" not in params
    assert "WFItemRangeStart" not in params


def test_random_item_specifier() -> None:
    """'Random Item' specifier emits correctly."""
    params = _params(
        GetItemFromList(list_input=_fake_output(), specifier="Random Item")
    )
    assert params["WFItemSpecifier"] == "Random Item"
    assert "WFItemIndex" not in params


# ---------------------------------------------------------------------------
# Item at Index
# ---------------------------------------------------------------------------


def test_item_at_index_emits_wf_item_index_as_string() -> None:
    """'Item at Index' emits WFItemIndex as a bare string, not an integer.

    observed_envelope_types.json lists WFItemIndex in bare_string_slots
    for this identifier — Apple stores the numeric value as a string.
    """
    params = _params(
        GetItemFromList(
            list_input=_fake_output(),
            specifier="Item at Index",
            item_index=3,
        )
    )
    assert params["WFItemSpecifier"] == "Item at Index"
    assert params["WFItemIndex"] == "3"
    assert isinstance(params["WFItemIndex"], str)


def test_item_at_index_requires_item_index() -> None:
    """'Item at Index' without item_index raises SchemaError at construction."""
    with pytest.raises(SchemaError, match="item_index is required"):
        GetItemFromList(
            list_input=_fake_output(),
            specifier="Item at Index",
        )


# ---------------------------------------------------------------------------
# Items in Range
# ---------------------------------------------------------------------------


def test_items_in_range_emits_range_keys() -> None:
    """'Items in Range' emits WFItemRangeStart and WFItemRangeEnd."""
    params = _params(
        GetItemFromList(
            list_input=_fake_output(),
            specifier="Items in Range",
            range_start=1,
            range_end=3,
        )
    )
    assert params["WFItemSpecifier"] == "Items in Range"
    assert params["WFItemRangeStart"] == 1
    assert params["WFItemRangeEnd"] == 3


def test_items_in_range_requires_both_bounds() -> None:
    """'Items in Range' without range_start or range_end raises SchemaError."""
    with pytest.raises(
        SchemaError, match="range_start and range_end are both required"
    ):
        GetItemFromList(
            list_input=_fake_output(),
            specifier="Items in Range",
            range_start=1,
        )

    with pytest.raises(
        SchemaError, match="range_start and range_end are both required"
    ):
        GetItemFromList(
            list_input=_fake_output(),
            specifier="Items in Range",
            range_end=3,
        )


# ---------------------------------------------------------------------------
# WFItemIndex quirk (confirmed from corpus)
# ---------------------------------------------------------------------------


def test_wf_item_index_emitted_alongside_last_item_specifier() -> None:
    """WFItemIndex is preserved on the wire even when specifier != 'Item at Index'.

    Confirmed by samples/decoded/tile_last_2_windows.xml:89-92: Apple wrote
    WFItemIndex='2' alongside WFItemSpecifier='Last Item'. This is an
    Apple UI artifact — the last-entered index value is preserved regardless
    of the active specifier. We match this behaviour for round-trip fidelity.
    """
    params = _params(
        GetItemFromList(
            list_input=_fake_output(),
            specifier="Last Item",
            item_index=2,
        )
    )
    assert params["WFItemSpecifier"] == "Last Item"
    assert params["WFItemIndex"] == "2"


def test_wf_item_index_not_emitted_when_none() -> None:
    """WFItemIndex is absent when item_index is not set."""
    params = _params(GetItemFromList(list_input=_fake_output(), specifier="Last Item"))
    assert "WFItemIndex" not in params


# ---------------------------------------------------------------------------
# WFInput wire format
# ---------------------------------------------------------------------------


def test_wf_input_emitted_as_token_attachment() -> None:
    """WFInput is a WFTextTokenAttachment envelope wrapping the output reference.

    Corpus: tile_last_2_windows.xml:29-43 — WFInput carries ActionOutput
    with the upstream Windows action's UUID and name.
    """
    out = _fake_output()
    params = _params(GetItemFromList(list_input=out))
    wf_input = params["WFInput"]
    assert wf_input["WFSerializationType"] == "WFTextTokenAttachment"
    assert wf_input["Value"]["OutputName"] == "Windows"
    assert wf_input["Value"]["OutputUUID"] == "A4FED113-114F-4E15-8F4D-ADA2BAC93FF3"
    assert wf_input["Value"]["Type"] == "ActionOutput"


def test_wf_input_omitted_when_none() -> None:
    """WFInput is absent from the wire dict when list_input is None."""
    params = _params(GetItemFromList())
    assert "WFInput" not in params


# ---------------------------------------------------------------------------
# Default output name
# ---------------------------------------------------------------------------


def test_default_output_name() -> None:
    """default_output_name is 'Item from List'.

    Confirmed from OutputName in downstream resizewindow action at
    samples/decoded/tile_last_2_windows.xml:57.
    """
    assert GetItemFromList.default_output_name == "Item from List"


def test_output_reference_uses_default_output_name() -> None:
    """action.output() uses 'Item from List' when no custom name is given."""
    action = GetItemFromList(list_input=_fake_output())
    out = action.output()
    assert out.name == "Item from List"


# ---------------------------------------------------------------------------
# Invalid specifier
# ---------------------------------------------------------------------------


def test_invalid_specifier_raises() -> None:
    """A bad specifier value raises SchemaError at construction."""
    with pytest.raises(SchemaError, match="not valid"):
        GetItemFromList(
            list_input=_fake_output(),
            specifier="Second Item",  # ty: ignore[invalid-argument-type]
        )


# ---------------------------------------------------------------------------
# Wire-format equivalence vs corpus
# ---------------------------------------------------------------------------


def test_corpus_dictionary_xml_appearance() -> None:
    """Reproduce dictionary.xml:185-204: only WFInput, no specifier, no index.

    The upstream 'choosefromlist' action's OutputUUID drives WFInput.
    """
    out = Output(
        uuid="27D23CDC-A759-4186-9843-888FCE78BD34",
        name="Selected Item",
    )
    action = GetItemFromList(
        uuid="2BF82F70-D4AC-4669-819B-81EAE96B6F93",
        list_input=out,
    )
    result = action.to_action_dict()
    assert result["WFWorkflowActionIdentifier"] == "is.workflow.actions.getitemfromlist"
    params = result["WFWorkflowActionParameters"]
    assert params["UUID"] == "2BF82F70-D4AC-4669-819B-81EAE96B6F93"
    assert params["WFInput"]["WFSerializationType"] == "WFTextTokenAttachment"
    assert (
        params["WFInput"]["Value"]["OutputUUID"]
        == "27D23CDC-A759-4186-9843-888FCE78BD34"
    )
    assert params["WFInput"]["Value"]["OutputName"] == "Selected Item"
    assert "WFItemSpecifier" not in params
    assert "WFItemIndex" not in params


def test_corpus_tile_last_2_windows_first_appearance() -> None:
    """Reproduce tile_last_2_windows.xml:24-43: first-item default, no specifier."""
    out = Output(
        uuid="A4FED113-114F-4E15-8F4D-ADA2BAC93FF3",
        name="Windows",
    )
    action = GetItemFromList(
        uuid="6B3F9798-9BAE-40B9-8691-1639191FBD4F",
        list_input=out,
    )
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["UUID"] == "6B3F9798-9BAE-40B9-8691-1639191FBD4F"
    assert "WFItemSpecifier" not in params
    assert "WFItemIndex" not in params


def test_corpus_tile_last_2_windows_second_appearance() -> None:
    """Reproduce tile_last_2_windows.xml:70-93: Last Item + WFItemIndex quirk.

    This is the key corpus evidence for the WFItemIndex quirk:
    Apple emitted WFItemIndex='2' alongside WFItemSpecifier='Last Item'.
    """
    out = Output(
        uuid="A4FED113-114F-4E15-8F4D-ADA2BAC93FF3",
        name="Windows",
    )
    action = GetItemFromList(
        uuid="D910CCF5-35EE-4225-ABE7-EA5FD8EFE90B",
        list_input=out,
        specifier="Last Item",
        item_index=2,
    )
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["UUID"] == "D910CCF5-35EE-4225-ABE7-EA5FD8EFE90B"
    assert params["WFItemSpecifier"] == "Last Item"
    assert params["WFItemIndex"] == "2"
    assert "WFItemRangeStart" not in params
    assert "WFItemRangeEnd" not in params


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_registered_by_identifier() -> None:
    """GetItemFromList is in the registry under the Apple identifier."""
    cls = lookup("is.workflow.actions.getitemfromlist")
    assert cls is GetItemFromList


def test_valid_specifiers_set() -> None:
    """All five expected specifier strings are in the valid set."""
    expected = {
        "First Item",
        "Last Item",
        "Random Item",
        "Item at Index",
        "Items in Range",
    }
    assert expected == _VALID_SPECIFIERS
