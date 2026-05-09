"""TextSplit — split text into a list on a chosen separator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Literal, get_args

from shortcut_lib.schema.base import Action, ParamValue, SchemaError, coerce_value
from shortcut_lib.schema.registry import register

# Closed set of separator strings shown in Shortcuts.app's Split Text dropdown.
WFTextSeparator = Literal["New Lines", "Spaces", "Every Character", "Custom"]
_VALID_SEPARATORS: frozenset[str] = frozenset(get_args(WFTextSeparator))


@register
@dataclass
class TextSplit(Action):
    """Split text into a list using the given separator.

    Args:
        input: The text to split. Pass an Action to chain off its output,
            a literal string, or any Value.
        separator: One of "New Lines", "Spaces", "Every Character", or
            "Custom". Defaults to "New Lines".
        custom_separator: The delimiter string. Required when
            ``separator`` is "Custom"; ignored otherwise.
        show_text: UI-only toggle. Apple emits ``Show-text: True`` when
            the "Show Text" toggle is visible in the editor. No runtime
            semantic effect; opt-in to match real samples.
    """

    identifier: ClassVar[str] = "is.workflow.actions.text.split"
    default_output_name: ClassVar[str] = "Split Text"

    input: ParamValue = None
    separator: WFTextSeparator = "New Lines"
    custom_separator: str | None = None
    show_text: bool | None = None

    def __post_init__(self) -> None:
        if self.separator not in _VALID_SEPARATORS:
            raise SchemaError(
                f"TextSplit.separator {self.separator!r} is not valid. "
                f"Expected one of: {sorted(_VALID_SEPARATORS)}"
            )

    def _params(self) -> dict[str, Any]:
        """Emit ``text``, ``separator``, and optionally ``WFTextCustomSeparator``."""
        if self.separator == "Custom" and self.custom_separator is None:
            raise SchemaError(
                "TextSplit: custom_separator is required when separator == 'Custom'"
            )
        out: dict[str, Any] = {}
        if self.input is not None:
            out["text"] = coerce_value(self.input)
        # Apple omits the separator key for the default "New Lines"; five
        # corpus samples confirm (e.g. samples/decoded/batch_add_reminders.xml:9).
        if self.separator != "New Lines":
            out["separator"] = self.separator
        if self.separator == "Custom":
            out["WFTextCustomSeparator"] = self.custom_separator
        if self.show_text is not None:
            out["Show-text"] = self.show_text
        return out
