"""Dictionary — build a structured key/value dictionary literal.

Apple identifier: ``is.workflow.actions.dictionary``.

The action creates a ``WFDictionaryFieldValue``-serialised dict. Each
entry is a ``WFDictionaryFieldValueItem`` with:

- ``WFItemType`` (int enum) — controls how the value is serialised.
- ``WFKey``  — always a ``WFTextTokenString`` (plain or templated).
- ``WFValue`` — shape depends on ``WFItemType``.

``WFItemType`` mapping (confirmed 0 from samples; 1-5 from Apple DSL):

  | Code | Python type          | Shortcuts label |
  |------|----------------------|-----------------|
  |  0   | str / Text / Value   | Text            |
  |  1   | str (URL)            | URL             |
  |  2   | int / float          | Number          |
  |  3   | dict                 | Dictionary      |
  |  4   | list                 | Array           |
  |  5   | bool                 | Boolean         |
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action, SchemaError, Value, coerce_value
from shortcut_lib.schema.registry import register

# WFItemType integer codes
_TYPE_TEXT = 0
_TYPE_URL = 1
_TYPE_NUMBER = 2
_TYPE_DICTIONARY = 3
_TYPE_ARRAY = 4
_TYPE_BOOLEAN = 5


def _text_token_string(s: str) -> dict[str, Any]:
    """Wrap a plain string as a WFTextTokenString value."""
    return {
        "Value": {"string": s, "attachmentsByRange": {}},
        "WFSerializationType": "WFTextTokenString",
    }


def _detect_item_type(value: object) -> int:
    """Return WFItemType code for *value*.

    Args:
        value: Python value to classify.

    Returns:
        WFItemType integer.

    Raises:
        SchemaError: if the value type is not supported.
    """
    # bool must come before int because bool is a subclass of int.
    if isinstance(value, bool):
        return _TYPE_BOOLEAN
    if isinstance(value, int | float):
        return _TYPE_NUMBER
    if isinstance(value, dict):
        return _TYPE_DICTIONARY
    if isinstance(value, list):
        return _TYPE_ARRAY
    if isinstance(value, str):
        return _TYPE_TEXT
    # Action, Output, Text, MagicVar, NamedVar → text token attachment → Text
    if isinstance(value, Action | Value):
        return _TYPE_TEXT
    raise SchemaError(
        f"Dictionary entry value of type {type(value).__name__!r} is not "
        "supported. Use str, int, float, bool, dict, list, or a Value/Action."
    )


def _encode_key(key: str) -> dict[str, Any]:
    """Encode a dict key as a WFTextTokenString."""
    return _text_token_string(key)


def _encode_value(value: object, item_type: int) -> Any:
    """Encode an entry value for the given WFItemType.

    Args:
        value: Python value to encode.
        item_type: WFItemType code.

    Returns:
        Wire-format value dict (or scalar for numbers/booleans).
    """
    if item_type == _TYPE_TEXT:
        coerced = coerce_value(value)
        # If coerce_value produced a plain str, wrap it as WFTextTokenString.
        if isinstance(coerced, str):
            return _text_token_string(coerced)
        # Action/Value already produce the right envelope.
        return coerced
    if item_type == _TYPE_NUMBER:
        # Numbers are stored as WFTextTokenString containing the numeric string.
        return _text_token_string(str(value))
    if item_type == _TYPE_BOOLEAN:
        # Booleans are stored as WFTextTokenString "true" / "false".
        return _text_token_string("true" if value else "false")
    if item_type == _TYPE_DICTIONARY:
        # Nested dict — re-encode recursively as WFDictionaryFieldValue.
        if not isinstance(value, dict):
            raise SchemaError(f"_TYPE_DICTIONARY but value is {type(value).__name__}")
        items = [_encode_entry(str(k), v) for k, v in value.items()]
        return {
            "Value": {"WFDictionaryFieldValueItems": items},
            "WFSerializationType": "WFDictionaryFieldValue",
        }
    if item_type == _TYPE_ARRAY:
        # Arrays stored as WFTextTokenString of each element joined by newlines
        # (Shortcuts' native list-to-text serialisation for array entries).
        if not isinstance(value, list):
            raise SchemaError(f"_TYPE_ARRAY but value is {type(value).__name__}")
        return _text_token_string("\n".join(str(el) for el in value))
    if item_type == _TYPE_URL:
        return _text_token_string(str(value))
    raise SchemaError(f"Unhandled WFItemType {item_type}")  # pragma: no cover


def _encode_entry(key: str, value: object) -> dict[str, Any]:
    """Encode a single key/value pair as a WFDictionaryFieldValueItem."""
    item_type = _detect_item_type(value)
    return {
        "WFItemType": item_type,
        "WFKey": _encode_key(key),
        "WFValue": _encode_value(value, item_type),
    }


@register
@dataclass
class Dictionary(Action):
    """Create a dictionary (key/value map) literal.

    Auto-detects value types: str→Text, int/float→Number, bool→Boolean,
    dict→Dictionary, list→Array. Pass an Action or Value for a variable
    reference (encoded as Text).

    Args:
        entries: List of (key, value) tuples. Keys are always strings.
            Values may be Python primitives or Action/Value references.

    Example::

        d = Dictionary(entries=[
            ("name", "Alice"),
            ("age", 30),
            ("active", True),
        ])
    """

    identifier: ClassVar[str] = "is.workflow.actions.dictionary"
    default_output_name: ClassVar[str] = "Dictionary"

    entries: list[tuple[str, Any]] = field(default_factory=list)

    def _params(self) -> dict[str, Any]:
        """Return WFItems as a WFDictionaryFieldValue-serialised parameter.

        Apple's Shortcuts.app omits ``WFItems`` entirely for an empty
        dictionary (verified via ``samples/decoded/dictionary.xml``);
        we match that to keep wire-format equivalence with GUI-authored
        shortcuts.
        """
        if not self.entries:
            return {}
        items = [_encode_entry(key, value) for key, value in self.entries]
        return {
            "WFItems": {
                "Value": {"WFDictionaryFieldValueItems": items},
                "WFSerializationType": "WFDictionaryFieldValue",
            }
        }
