"""Count — count the number of items, characters, words, sentences, or lines."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Literal, get_args

from shortcut_lib.schema.base import Action, ParamValue, SchemaError, coerce_value
from shortcut_lib.schema.registry import register

# Closed set of count-type strings shown in Shortcuts.app's Count action.
# "Items" verified via samples/decoded/combine_screenshots_and_share.xml
# (WFCountType = "Items"). The remaining values are Jellycore-documented;
# no corpus sample yet — flag if observed wire values differ.
WFCountType = Literal["Items", "Characters", "Words", "Sentences", "Lines"]

_VALID_COUNT_TYPES: frozenset[str] = frozenset(get_args(WFCountType))


@register
@dataclass
class Count(Action):
    """Count items, characters, words, sentences, or lines in the input.

    Wire-format notes (verified against corpus samples):

    - ``Input`` — the value to count (WFTextTokenAttachment envelope).
      Note: Apple uses ``Input`` (not ``WFInput``) for this action.
    - ``WFCountType`` — always emitted. Apple emits "Items" explicitly in
      samples/decoded/combine_screenshots_and_share.xml; the dictionary.xml
      sample omits it (carrying the default), but we emit it unconditionally
      for clarity.

    Args:
        input: The value to count. Pass an Action, Output, NamedVar, or
            any Value. Corresponds to Apple's ``Input`` parameter.
        count_type: One of "Items", "Characters", "Words", "Sentences",
            "Lines". Defaults to "Items".

    Divergence from Jellycore: Jellycore lists ``type`` as the count-type
    key; the real Apple plist key is ``WFCountType``.
    """

    identifier: ClassVar[str] = "is.workflow.actions.count"
    default_output_name: ClassVar[str] = "Count"

    input: ParamValue = None
    count_type: WFCountType = field(default="Items")

    def __post_init__(self) -> None:
        if self.count_type not in _VALID_COUNT_TYPES:
            raise SchemaError(
                f"count_type {self.count_type!r} is not valid. "
                f"Expected one of: {sorted(_VALID_COUNT_TYPES)}"
            )

    def _params(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.input is not None:
            out["Input"] = coerce_value(self.input)
        out["WFCountType"] = self.count_type
        return out
