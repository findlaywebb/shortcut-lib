"""GetUpcomingEvents — fetch upcoming calendar events."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Literal, get_args

from shortcut_lib.schema.base import Action, SchemaError
from shortcut_lib.schema.registry import register

# Confirmed from daily_standup.xml:34 (line 466: "Today").
# Apple surfaces "Today", "This Week", and "All" in the Shortcuts UI.
WFDateSpecifier = Literal["Today", "This Week", "All"]

_VALID_DATE_SPECIFIERS: frozenset[str] = frozenset(get_args(WFDateSpecifier))


@register
@dataclass
class GetUpcomingEvents(Action):
    """Fetch upcoming calendar events within a time window.

    Args:
        date_specifier: Time window for the query — "Today", "This Week",
            or "All". Corresponds to Apple's ``WFDateSpecifier`` key.
            Defaults to "Today".
        calendar: Calendar name to query. Empty string means all calendars
            (Apple's default). Corresponds to ``WFGetUpcomingItemCalendar``.
        count: Maximum number of events to return. Corresponds to
            ``WFGetUpcomingItemCount``. When ``None`` the key is omitted and
            Apple uses its own default.
    """

    identifier: ClassVar[str] = "is.workflow.actions.getupcomingevents"
    default_output_name: ClassVar[str] = "Upcoming Events"

    date_specifier: WFDateSpecifier = field(default="Today")
    calendar: str = field(default="")
    count: int | None = field(default=None)

    def __post_init__(self) -> None:
        if self.date_specifier not in _VALID_DATE_SPECIFIERS:
            raise SchemaError(
                f"date_specifier {self.date_specifier!r} is not valid. "
                f"Expected one of: {sorted(_VALID_DATE_SPECIFIERS)}"
            )
        if self.count is not None and self.count < 1:
            raise SchemaError(f"count must be a positive integer, got {self.count!r}")

    def _params(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "WFDateSpecifier": self.date_specifier,
            "WFGetUpcomingItemCalendar": self.calendar,
        }
        if self.count is not None:
            out["WFGetUpcomingItemCount"] = self.count
        return out
