"""Tests for Dictionary — is.workflow.actions.dictionary."""

from __future__ import annotations

from shortcut_lib.schema.actions.dictionary import Dictionary
from shortcut_lib.schema.actions.get_text import GetText
from shortcut_lib.schema.registry import list_actions
from shortcut_lib.schema.values import NamedVar

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _params(d: Dictionary) -> dict:
    return d.to_action_dict()["WFWorkflowActionParameters"]


def _items(d: Dictionary) -> list[dict]:
    wf_items = _params(d)["WFItems"]
    assert wf_items["WFSerializationType"] == "WFDictionaryFieldValue"
    return wf_items["Value"]["WFDictionaryFieldValueItems"]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_dictionary_with_string_values() -> None:
    """String entries emit WFItemType 0 and WFTextTokenString values."""
    d = Dictionary(entries=[("greeting", "hello"), ("farewell", "bye")])
    result = d.to_action_dict()

    assert result["WFWorkflowActionIdentifier"] == "is.workflow.actions.dictionary"
    items = _items(d)
    assert len(items) == 2

    first = items[0]
    assert first["WFItemType"] == 0  # Text
    # Key
    assert first["WFKey"]["WFSerializationType"] == "WFTextTokenString"
    assert first["WFKey"]["Value"]["string"] == "greeting"
    # Value
    assert first["WFValue"]["WFSerializationType"] == "WFTextTokenString"
    assert first["WFValue"]["Value"]["string"] == "hello"

    second = items[1]
    assert second["WFKey"]["Value"]["string"] == "farewell"
    assert second["WFValue"]["Value"]["string"] == "bye"


def test_dictionary_with_mixed_types() -> None:
    """String, int, and bool entries map to WFItemType 0, 2, and 5."""
    d = Dictionary(
        entries=[
            ("label", "Alice"),  # str → 0
            ("count", 42),  # int → 2
            ("active", True),  # bool → 5 (must be before int check)
            ("ratio", 3.14),  # float → 2
        ]
    )
    items = _items(d)
    assert len(items) == 4

    # str → Text (0)
    assert items[0]["WFItemType"] == 0
    assert items[0]["WFValue"]["WFSerializationType"] == "WFTextTokenString"
    assert items[0]["WFValue"]["Value"]["string"] == "Alice"

    # int → Number (2)
    assert items[1]["WFItemType"] == 2
    assert items[1]["WFValue"]["WFSerializationType"] == "WFTextTokenString"
    assert items[1]["WFValue"]["Value"]["string"] == "42"

    # bool → Boolean (5)
    assert items[2]["WFItemType"] == 5
    assert items[2]["WFValue"]["WFSerializationType"] == "WFTextTokenString"
    assert items[2]["WFValue"]["Value"]["string"] == "true"

    # float → Number (2)
    assert items[3]["WFItemType"] == 2
    assert items[3]["WFValue"]["Value"]["string"] == "3.14"


def test_dictionary_with_variable_value() -> None:
    """Passing an Action as a value chains to its output reference correctly."""
    source = GetText(text="dynamic value")
    d = Dictionary(entries=[("key", source)])

    items = _items(d)
    assert len(items) == 1

    entry = items[0]
    assert entry["WFItemType"] == 0  # variable → Text

    # The value should be a WFTextTokenAttachment referencing the action's UUID.
    wf_value = entry["WFValue"]
    assert wf_value["WFSerializationType"] == "WFTextTokenAttachment"
    inner = wf_value["Value"]
    assert inner["Type"] == "ActionOutput"
    assert inner["OutputUUID"] == source.uuid
    assert inner["OutputName"] == "Text"


def test_dictionary_empty() -> None:
    """An empty Dictionary still emits WFItems with an empty items list."""
    d = Dictionary()
    items = _items(d)
    assert items == []


def test_dictionary_with_nested_dict() -> None:
    """A dict value emits WFItemType 3 and a nested WFDictionaryFieldValue."""
    d = Dictionary(entries=[("meta", {"x": "1", "y": "2"})])
    items = _items(d)

    assert items[0]["WFItemType"] == 3  # Dictionary

    nested = items[0]["WFValue"]
    assert nested["WFSerializationType"] == "WFDictionaryFieldValue"
    nested_items = nested["Value"]["WFDictionaryFieldValueItems"]
    assert len(nested_items) == 2
    assert nested_items[0]["WFKey"]["Value"]["string"] == "x"


def test_dictionary_with_named_var_value() -> None:
    """A NamedVar value is encoded as a WFTextTokenAttachment (Type=Variable)."""
    var = NamedVar("MyVar")
    d = Dictionary(entries=[("ref", var)])
    items = _items(d)

    entry = items[0]
    assert entry["WFItemType"] == 0  # Text
    wf_value = entry["WFValue"]
    assert wf_value["WFSerializationType"] == "WFTextTokenAttachment"
    assert wf_value["Value"]["Type"] == "Variable"
    assert wf_value["Value"]["VariableName"] == "MyVar"


def test_dictionary_registered() -> None:
    """Dictionary appears in the action registry with the correct identifier."""
    identifiers = {entry["identifier"] for entry in list_actions()}
    assert "is.workflow.actions.dictionary" in identifiers
