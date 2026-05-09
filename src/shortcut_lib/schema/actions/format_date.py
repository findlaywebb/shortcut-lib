"""FormatDate — convert a date to a formatted string."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Literal, get_args

from shortcut_lib.schema.base import (
    Action,
    ParamValue,
    SchemaError,
    coerce_text_field,
)
from shortcut_lib.schema.registry import register

# Closed set of date/time style strings shown in Shortcuts.app's Format Date
# action dropdowns. Confirmed against Apple's plist wire format.
WFDateStyle = Literal[
    "None", "Short", "Medium", "Long", "Custom", "Relative", "RFC 2822", "ISO 8601"
]
WFTimeStyle = Literal["None", "Short", "Medium", "Long"]

_VALID_DATE_STYLES: frozenset[str] = frozenset(get_args(WFDateStyle))
_VALID_TIME_STYLES: frozenset[str] = frozenset(get_args(WFTimeStyle))


@register
@dataclass
class FormatDate(Action):
    """Format Date — convert a date to a formatted string.

    Wraps ``is.workflow.actions.format.date``. Takes a date value and
    returns a string representation using a built-in style or a custom
    Unicode date-format pattern.

    Args:
        input: Date to format (``WFDate``). Pass an
            :class:`~shortcut_lib.schema.base.Action`, an
            :class:`~shortcut_lib.schema.values.Output`, a magic variable
            (e.g. ``CurrentDate``), or any
            :class:`~shortcut_lib.schema.base.Value`. This slot is a
            ``WFTextTokenString`` — a bare ``WFTextTokenAttachment``
            produces an empty string at runtime. Omitted when ``None``.
        date_style: How the date part is formatted (``WFDateFormatStyle``).
            One of ``"None"``, ``"Short"``, ``"Medium"``, ``"Long"``,
            ``"Custom"``, ``"Relative"``, ``"RFC 2822"``, ``"ISO 8601"``.
            Defaults to ``"Short"``. Raises
            :class:`~shortcut_lib.schema.base.SchemaError` for unknown values.
        time_style: How the time part is formatted (``WFTimeFormatStyle``).
            One of ``"None"``, ``"Short"``, ``"Medium"``, ``"Long"``.
            Omitted from the plist when ``None`` — Apple applies its own
            default in that case.
        custom_format: Unicode date-format string, e.g. ``"yyyy-MM-dd HH:mm"``
            (``WFDateFormat``). Required when ``date_style="Custom"``;
            ignored otherwise. Raises
            :class:`~shortcut_lib.schema.base.SchemaError` if
            ``date_style="Custom"`` and this is empty.

    Returns:
        The formatted date string (output name: "Formatted Date").

    Sample citations:
        samples/decoded/dictionary.xml:491 — Short date_style, no time_style.
        samples/decoded/rename_files.xml:693 — custom format with time.
        samples/decoded/daily_standup.xml:879 — ISO 8601 style.
    """

    identifier: ClassVar[str] = "is.workflow.actions.format.date"
    default_output_name: ClassVar[str] = "Formatted Date"

    input: ParamValue = None
    date_style: WFDateStyle = field(default="Short")
    time_style: WFTimeStyle | None = field(default=None)
    custom_format: str | None = field(default=None)

    def __post_init__(self) -> None:
        if self.date_style not in _VALID_DATE_STYLES:
            raise SchemaError(
                f"date_style {self.date_style!r} is not valid. "
                f"Expected one of: {sorted(_VALID_DATE_STYLES)}"
            )
        if self.time_style is not None and self.time_style not in _VALID_TIME_STYLES:
            raise SchemaError(
                f"time_style {self.time_style!r} is not valid. "
                f"Expected one of: {sorted(_VALID_TIME_STYLES)}"
            )
        if self.date_style == "Custom" and not self.custom_format:
            raise SchemaError(
                'custom_format must be set when date_style is "Custom". '
                'Example: custom_format="yyyy-MM-dd"'
            )

    def _params(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.input is not None:
            # WFDate is a WFTextTokenString slot — a bare WFTextTokenAttachment
            # imports as no-input and produces an empty formatted string.
            out["WFDate"] = coerce_text_field(self.input)
        out["WFDateFormatStyle"] = self.date_style
        if self.time_style is not None:
            out["WFTimeFormatStyle"] = self.time_style
        if self.date_style == "Custom" and self.custom_format:
            out["WFDateFormat"] = self.custom_format
        return out
