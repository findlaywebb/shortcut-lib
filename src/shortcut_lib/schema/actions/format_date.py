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
    """Format a date as a string using a date/time style or custom pattern.

    Args:
        input: Date to format. Pass an Action, Output, MagicVar (e.g.
            CurrentDate), or any Value. Corresponds to Apple's ``WFDate``
            parameter; the name ``input`` matches the library convention.
        date_style: One of "None", "Short", "Medium", "Long", "Custom",
            "Relative", "RFC 2822", "ISO 8601". Defaults to "Short".
        time_style: One of "None", "Short", "Medium", "Long". Optional;
            when omitted the key is excluded from the emitted dict.
        custom_format: Format string (e.g. ``"yyyy-MM-dd"``) used only
            when ``date_style`` is "Custom". Required in that case.
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
