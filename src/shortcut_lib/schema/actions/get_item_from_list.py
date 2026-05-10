"""GetItemFromList — retrieve one or more items from a list by position.

Apple identifier: ``is.workflow.actions.getitemfromlist``.
Apple display name: **Get Item from List**.

Natural pair with ``BuildList`` (``is.workflow.actions.list``) — build a
list with BuildList, then pull items out with this action.

Wire format
-----------
``WFInput`` carries the list as a ``WFTextTokenAttachment`` envelope
(single action-output reference). ``WFItemSpecifier`` and ``WFItemIndex``
are **bare strings** in the plist (confirmed in
``data/observed_envelope_types.json`` — both appear in the
``bare_string_slots`` entry for this identifier).

Corpus evidence
---------------
Three appearances across two samples:

1. ``samples/decoded/dictionary.xml:185-204``
   Only ``WFInput`` present; no ``WFItemSpecifier``, no ``WFItemIndex``.
   Apple's default specifier ("First Item") is omitted from the wire, so
   this action fetches the first item of the upstream output.

2. ``samples/decoded/tile_last_2_windows.xml:24-43``
   Same minimal form — only ``WFInput``. Another "First Item" default.

3. ``samples/decoded/tile_last_2_windows.xml:70-93``
   ``WFInput`` + ``WFItemIndex: "2"`` + ``WFItemSpecifier: "Last Item"``.

``WFItemIndex`` quirk (confirmed)
----------------------------------
Appearance #3 in the corpus shows ``WFItemIndex: "2"`` present alongside
``WFItemSpecifier: "Last Item"`` — the index is **not** "Item at Index".
This directly confirms the open V1.5 question recorded in
``docs/architecture-review/v15-reviews/_SUMMARY.md``:

  *"WFItemIndex without WFItemSpecifier Apple quirk on GetItemFromList —
  needs a fresh sample to confirm."*

Apple writes whatever numeric index was last entered in the UI regardless
of whether the selected specifier actually uses it. This is purely a
round-trip artifact; the value is silently ignored at runtime when the
specifier is not "Item at Index". ``GetItemFromList._params()`` mimics
Apple's behaviour by including ``WFItemIndex`` whenever it is set,
irrespective of specifier, so that a round-trip through ``from_workflow``
and ``to_actions`` produces a byte-identical plist.

Jellycore note
--------------
``jq '.["is.workflow.actions.getitemfromlist"]' data/jellycore_facts.json``
returns ``null`` — jellycore has no entry for this action. All type
evidence is derived from the three corpus appearances and
``data/observed_envelope_types.json``.

Args
----
WFInput (``list_input``)
    The list to draw from. Pass an ``Action`` whose output is a list, an
    ``Output`` reference, or any ``Value``. Emitted as a
    ``WFTextTokenAttachment`` envelope. Required.

WFItemSpecifier (``specifier``)
    Which item(s) to retrieve. One of:

    - ``"First Item"`` (default) — first element; ``WFItemSpecifier``
      **omitted** from the wire when this is the specifier (Apple's
      GUI-default omission, confirmed appearances #1 and #2).
    - ``"Last Item"``
    - ``"Random Item"``
    - ``"Item at Index"`` — uses ``item_index``; 1-based per Apple's UI.
    - ``"Items in Range"`` — uses ``range_start`` and ``range_end``.

WFItemIndex (``item_index``)
    1-based integer index. Required when ``specifier="Item at Index"``.
    Apple may also emit it alongside other specifiers (corpus quirk above);
    we preserve it on the wire when set, regardless of specifier. Stored
    and emitted as a bare string per ``observed_envelope_types.json``.

WFItemRangeStart (``range_start``)
    1-based start of range. Required when ``specifier="Items in Range"``.

WFItemRangeEnd (``range_end``)
    1-based end of range. Required when ``specifier="Items in Range"``.

Returns
-------
"Item from List" (confirmed from ``OutputName`` in downstream actions in
``samples/decoded/tile_last_2_windows.xml:57``) — the matching item(s).
When specifier is "Items in Range" the output is a sub-list.

Cross-references
----------------
- :class:`~shortcut_lib.schema.actions.list.BuildList` — create the list
  this action reads from.
- :class:`~shortcut_lib.schema.actions.choose_from_list.ChooseFromList` —
  present a list to the user interactively.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Literal, get_args

from shortcut_lib.schema.base import Action, ParamValue, SchemaError, coerce_value
from shortcut_lib.schema.registry import register

# Closed set of specifier strings as displayed in Shortcuts.app.
WFItemSpecifier = Literal[
    "First Item",
    "Last Item",
    "Random Item",
    "Item at Index",
    "Items in Range",
]
_VALID_SPECIFIERS: frozenset[str] = frozenset(get_args(WFItemSpecifier))

# Apple omits WFItemSpecifier on the wire when the default is selected.
_DEFAULT_SPECIFIER = "First Item"


@register
@dataclass
class GetItemFromList(Action):
    """Retrieve one or more items from a list by position.

    Apple display name: Get Item from List
    (``is.workflow.actions.getitemfromlist``).

    Natural pair with :class:`~shortcut_lib.schema.actions.list.BuildList`
    — build a list there, then pull items out here.

    Args:
        list_input: The list to draw from. Pass any Action, Output, or
            Value whose result is a list.
        specifier: Which item(s) to retrieve. Defaults to "First Item".
            Use "Item at Index" with ``item_index``; "Items in Range" with
            ``range_start`` / ``range_end``.
        item_index: 1-based index. Required for "Item at Index". May also
            be set alongside other specifiers — Apple preserves the last
            UI value on the wire (see module docstring quirk note).
        range_start: 1-based range start. Required for "Items in Range".
        range_end: 1-based range end. Required for "Items in Range".

    Example — first item (default)::

        from shortcut_lib.schema.actions.get_item_from_list import (
            GetItemFromList,
        )
        first = GetItemFromList(list_input=my_list_action)

    Example — item at index::

        second = GetItemFromList(
            list_input=my_list_action,
            specifier="Item at Index",
            item_index=2,
        )

    Example — last item::

        last = GetItemFromList(
            list_input=my_list_action,
            specifier="Last Item",
        )
    """

    identifier: ClassVar[str] = "is.workflow.actions.getitemfromlist"
    default_output_name: ClassVar[str] = "Item from List"

    list_input: ParamValue = None
    specifier: WFItemSpecifier = "First Item"
    item_index: int | None = None
    range_start: int | None = None
    range_end: int | None = None

    def __post_init__(self) -> None:
        """Validate specifier set and cross-field constraints."""
        if self.specifier not in _VALID_SPECIFIERS:
            raise SchemaError(
                f"GetItemFromList.specifier {self.specifier!r} is not valid. "
                f"Expected one of: {sorted(_VALID_SPECIFIERS)}"
            )
        if self.specifier == "Item at Index" and self.item_index is None:
            raise SchemaError(
                "GetItemFromList: item_index is required when specifier='Item at Index'"
            )
        if self.specifier == "Items in Range" and (
            self.range_start is None or self.range_end is None
        ):
            raise SchemaError(
                "GetItemFromList: range_start and range_end are both "
                "required when specifier='Items in Range'"
            )

    def _params(self) -> dict[str, Any]:
        """Emit WFInput, WFItemSpecifier, and optional index/range fields.

        Omission rules (matching Apple GUI output):
        - ``WFItemSpecifier`` is omitted when specifier is "First Item"
          (corpus appearances #1 and #2).
        - ``WFItemIndex`` is included whenever ``item_index`` is set —
          even if the specifier is not "Item at Index" — because Apple
          itself does this (corpus appearance #3: "Last Item" + index 2).
          This preserves round-trip equivalence.
        - ``WFItemRangeStart`` / ``WFItemRangeEnd`` are included only when
          specifier is "Items in Range".
        """
        out: dict[str, Any] = {}
        if self.list_input is not None:
            out["WFInput"] = coerce_value(self.list_input)
        # Omit for the default specifier to match Apple's wire format.
        if self.specifier != _DEFAULT_SPECIFIER:
            out["WFItemSpecifier"] = self.specifier
        # Preserve WFItemIndex whenever set — Apple emits it irrespective of
        # specifier (confirmed: tile_last_2_windows.xml:89-92).
        if self.item_index is not None:
            out["WFItemIndex"] = str(self.item_index)
        if self.specifier == "Items in Range":
            if self.range_start is not None:
                out["WFItemRangeStart"] = self.range_start
            if self.range_end is not None:
                out["WFItemRangeEnd"] = self.range_end
        return out
