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
    """Split Text — split text into a list on a chosen separator.

    Wraps ``is.workflow.actions.text.split``. Breaks a text string into a
    list of substrings. The separator key is omitted for the default
    ``"New Lines"`` mode — matching Apple's wire-format convention.

    Args:
        input: The text to split (``text``). Pass an
            :class:`~shortcut_lib.schema.base.Action` to chain off its
            output, a literal string, or any
            :class:`~shortcut_lib.schema.base.Value`. Omitted when ``None``.
        separator: The split mode (``separator``). One of ``"New Lines"``
            (default), ``"Spaces"``, ``"Every Character"``, or
            ``"Custom"``. Apple omits the plist key for ``"New Lines"`` —
            the default; all other values are emitted explicitly. Raises
            :class:`~shortcut_lib.schema.base.SchemaError` for unknown values.
        custom_separator: The delimiter string
            (``WFTextCustomSeparator``). Required when ``separator`` is
            ``"Custom"``; raises
            :class:`~shortcut_lib.schema.base.SchemaError` at emit time if
            missing. Ignored for all other separator modes.

    Returns:
        The list of split substrings (output name: "Split Text").

    Quirks:
        The Python field is named ``input`` (library convention) but the
        plist key is ``text`` (camelCase AppIntent convention) — a
        wire-key mismatch.

    Sample citations:
        samples/decoded/batch_add_reminders.xml:190 — ``"New Lines"``
        default (no separator key emitted).
        samples/decoded/dictionary.xml:794 — explicit separator value.
    """

    identifier: ClassVar[str] = "is.workflow.actions.text.split"
    default_output_name: ClassVar[str] = "Split Text"

    input: ParamValue = None
    separator: WFTextSeparator = "New Lines"
    custom_separator: str | None = None

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
        return out
