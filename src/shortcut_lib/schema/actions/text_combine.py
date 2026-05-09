"""TextCombine — combine a list of text items into a single string."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Literal, get_args

from shortcut_lib.schema.base import Action, ParamValue, SchemaError, coerce_value
from shortcut_lib.schema.registry import register

# Closed set of separator strings shown in Shortcuts.app's Combine Text
# dropdown.  Mirrors TextSplit except "Every Character" is absent — that
# separator is split-only and has no combine equivalent.
#
# Wire format uses the key ``WFTextSeparator`` (same as text.split).
# jellycore_facts.json lists ``combine`` as a parameter key; this appears to be
# a stale / internal label.  Five corpus samples all use ``WFTextSeparator``.
WFTextCombineSeparator = Literal["New Lines", "Spaces", "Custom"]
_VALID_SEPARATORS: frozenset[str] = frozenset(get_args(WFTextCombineSeparator))


@register
@dataclass
class TextCombine(Action):
    """Combine a list of text items into a single string.

    Wraps ``is.workflow.actions.text.combine``.  The inverse of TextSplit.

    Wire-format notes (5 corpus samples):
    - ``text`` slot uses ``WFTextTokenAttachment`` envelope (same as TextSplit).
    - Separator wire key is ``WFTextSeparator`` (same as TextSplit).
    - Apple omits ``WFTextSeparator`` when using the default "New Lines"
      (dictionary.xml has no key; daily_standup.xml writes it explicitly —
      both are valid; we default-omit for minimal output, matching TextSplit).
    - Custom delimiter uses ``WFTextCustomSeparator`` (same key as TextSplit).
    - ``Show-text`` boolean appears in sort_lines.xml — mirrored here.

    Args:
        input: The list of text items to combine.  Pass an Action to chain
            off its output, a literal string, or any Value.
        separator: One of "New Lines", "Spaces", or "Custom".
            Defaults to "New Lines".
        custom_separator: The delimiter string when separator="Custom";
            ignored otherwise.  Required when separator is "Custom".
        show_text: Mirror of the Shortcuts.app "Show Text" toggle.
            None omits the key entirely (most common case).
    """

    identifier: ClassVar[str] = "is.workflow.actions.text.combine"
    default_output_name: ClassVar[str] = "Combined Text"

    input: ParamValue = None
    separator: WFTextCombineSeparator = "New Lines"
    custom_separator: str | None = None
    show_text: bool | None = None

    def __post_init__(self) -> None:
        if self.separator not in _VALID_SEPARATORS:
            raise SchemaError(
                f"TextCombine.separator {self.separator!r} is not valid. "
                f"Expected one of: {sorted(_VALID_SEPARATORS)}"
            )

    def _params(self) -> dict[str, Any]:
        """Emit ``text``, ``WFTextSeparator``, and optionally ``WFTextCustomSeparator``.

        Apple omits ``WFTextSeparator`` for the default "New Lines" (confirmed
        by dictionary.xml which has no separator key).  We match that behaviour.
        """
        if self.separator == "Custom" and self.custom_separator is None:
            raise SchemaError(
                "TextCombine: custom_separator is required when separator == 'Custom'"
            )
        out: dict[str, Any] = {}
        if self.show_text is not None:
            out["Show-text"] = self.show_text
        if self.input is not None:
            out["text"] = coerce_value(self.input)
        # Apple omits WFTextSeparator for the default "New Lines"; omit to
        # match (dictionary.xml confirms: no separator key in that sample).
        if self.separator != "New Lines":
            out["WFTextSeparator"] = self.separator
        if self.separator == "Custom":
            out["WFTextCustomSeparator"] = self.custom_separator
        return out
