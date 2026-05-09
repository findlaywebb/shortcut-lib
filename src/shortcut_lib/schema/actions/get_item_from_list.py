"""GetItemFromList — retrieve one or more items from a list by position."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Literal, get_args

from shortcut_lib.schema.base import (
    Action,
    ParamValue,
    SchemaError,
    coerce_value,
)
from shortcut_lib.schema.registry import register

# Closed set of item-specifier strings shown in Shortcuts.app's Get Item
# From List action. Confirmed against Apple's plist wire format:
#   - "Last Item" + WFItemIndex verified in samples/decoded/tile_last_2_windows.xml
#   - "First Item" (default) verified in samples/decoded/dictionary.xml and
#     samples/decoded/tile_last_2_windows.xml (no key present ⇒ default)
# "Random Item", "Item At Index", and "Item Range" are Jellycore-documented
# and Literal-typed; no corpus sample yet — flag if observed wire values differ.
WFItemSpecifier = Literal[
    "First Item", "Last Item", "Random Item", "Item At Index", "Item Range"
]

_VALID_SPECIFIERS: frozenset[str] = frozenset(get_args(WFItemSpecifier))


@register
@dataclass
class GetItemFromList(Action):
    """Get an item or range of items from a list by position.

    Prefer the type-specific factory methods — they expose only the
    parameters valid for that specifier, so an invalid combination is a
    ``TypeError`` at the call site rather than a ``SchemaError`` after
    construction::

        first  = GetItemFromList.first(list_input=my_list)
        last   = GetItemFromList.last(list_input=my_list)
        rnd    = GetItemFromList.random(list_input=my_list)
        at     = GetItemFromList.at_index(list_input=my_list, index=3)
        rng    = GetItemFromList.range(list_input=my_list, range_start=1, range_end=3)

    The direct constructor is preserved for runtime-determined specifiers.

    Wire-format notes (verified against corpus samples):

    - ``WFInput`` — the list to pick from (WFTextTokenAttachment envelope).
    - ``WFItemSpecifier`` — omitted when "First Item" (Apple default).
    - ``WFItemIndex`` — only emitted for "Item At Index".
    - ``WFItemRangeStart`` / ``WFItemRangeEnd`` — only emitted for "Item Range".

    Divergence from Jellycore: Jellycore lists ``type`` as the specifier
    key; the real Apple plist key is ``WFItemSpecifier``.
    """

    identifier: ClassVar[str] = "is.workflow.actions.getitemfromlist"
    default_output_name: ClassVar[str] = "Item from List"

    input: ParamValue = None
    specifier: WFItemSpecifier = field(default="First Item")
    index: ParamValue = None  # only when specifier="Item At Index"
    range_start: ParamValue = None  # only when specifier="Item Range"
    range_end: ParamValue = None  # only when specifier="Item Range"

    def __post_init__(self) -> None:
        if self.specifier not in _VALID_SPECIFIERS:
            raise SchemaError(
                f"specifier {self.specifier!r} is not valid. "
                f"Expected one of: {sorted(_VALID_SPECIFIERS)}"
            )
        if self.specifier == "Item At Index" and self.index is None:
            raise SchemaError('index must be set when specifier is "Item At Index".')
        if self.specifier == "Item Range" and (
            self.range_start is None or self.range_end is None
        ):
            raise SchemaError(
                "range_start and range_end must both be set when "
                'specifier is "Item Range".'
            )
        # Fields only valid for their respective specifier
        if self.specifier not in ("Item At Index",) and self.index is not None:
            raise SchemaError(
                'index only applies to specifier="Item At Index"; '
                f"got specifier={self.specifier!r}."
            )
        if self.specifier != "Item Range" and (
            self.range_start is not None or self.range_end is not None
        ):
            raise SchemaError(
                'range_start and range_end only apply to specifier="Item Range"; '
                f"got specifier={self.specifier!r}."
            )

    def _params(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.input is not None:
            out["WFInput"] = coerce_value(self.input)
        if self.specifier != "First Item":
            out["WFItemSpecifier"] = self.specifier
        if self.specifier == "Item At Index" and self.index is not None:
            out["WFItemIndex"] = coerce_value(self.index)
        if self.specifier == "Item Range":
            if self.range_start is not None:
                out["WFItemRangeStart"] = coerce_value(self.range_start)
            if self.range_end is not None:
                out["WFItemRangeEnd"] = coerce_value(self.range_end)
        return out

    # ------------------------------------------------------------------
    # Factory methods — preferred over the direct constructor
    # ------------------------------------------------------------------

    @classmethod
    def first(
        cls,
        *,
        list_input: ParamValue = None,
    ) -> GetItemFromList:
        """Return a GetItemFromList configured to fetch the first item."""
        return cls(input=list_input, specifier="First Item")

    @classmethod
    def last(
        cls,
        *,
        list_input: ParamValue = None,
    ) -> GetItemFromList:
        """Return a GetItemFromList configured to fetch the last item."""
        return cls(input=list_input, specifier="Last Item")

    @classmethod
    def random(
        cls,
        *,
        list_input: ParamValue = None,
    ) -> GetItemFromList:
        """Return a GetItemFromList configured to fetch a random item."""
        return cls(input=list_input, specifier="Random Item")

    @classmethod
    def at_index(
        cls,
        *,
        list_input: ParamValue = None,
        index: ParamValue,
    ) -> GetItemFromList:
        """Return a GetItemFromList configured to fetch the item at ``index``."""
        return cls(input=list_input, specifier="Item At Index", index=index)

    @classmethod
    def range(
        cls,
        *,
        list_input: ParamValue = None,
        range_start: ParamValue,
        range_end: ParamValue,
    ) -> GetItemFromList:
        """Return a GetItemFromList configured to fetch items in a range."""
        return cls(
            input=list_input,
            specifier="Item Range",
            range_start=range_start,
            range_end=range_end,
        )
