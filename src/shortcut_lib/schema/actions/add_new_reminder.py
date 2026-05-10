"""AddNewReminder — create a Reminders.app reminder from a Shortcut.

Sample-grounded implementation across 5 corpus appearances:
  batch_add_reminders.xml   (actions 2 and 12)
  set_weekend_chores.xml    (action 3)
  add_expiry_reminder.xml   (action 3)

Examples::

    # Minimal — title only.
    from shortcut_lib.schema.actions.add_new_reminder import AddNewReminder
    from shortcut_lib.schema.values import RepeatItem

    r = AddNewReminder(title=RepeatItem)

    # Full — timed alert with list, notes, URL, and parent task.
    from shortcut_lib.schema.values import Ask, Output, Text

    alert_time = Output(uuid="73F52A62-...", name="Ask for Input")
    r = AddNewReminder(
        title=Text("{item} is expiring!", substitutions={"item": RepeatItem}),
        calendar="Reminders",
        notes="Check expiry date",
        alert_enabled="Alert",
        alert_condition="At Time",
        alert_custom_time=alert_time,
        url="https://example.com",
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Literal, get_args

from shortcut_lib.schema.base import (
    Action,
    ParamValue,
    SchemaError,
    coerce_text_field,
    coerce_value,
)
from shortcut_lib.schema.registry import register

# Closed set confirmed from 5 corpus samples.
# "When I Arrive" observed in batch_add_reminders (actions 2, 12).
# "At Time"       observed in set_weekend_chores (action 3) and
#                 add_expiry_reminder (action 3).
# "When I Leave"  — symmetric with "When I Arrive"; not observed in corpus
#                   (inferred by symmetry).
WFAlertCondition = Literal["At Time", "When I Arrive", "When I Leave"]

# String-valued alert toggle observed in samples.
# "Alert"    — set_weekend_chores action 3, add_expiry_reminder action 3.
# "No Alert" — batch_add_reminders action 12.
# Absence    — batch_add_reminders action 2 (key omitted entirely).
WFAlertEnabled = Literal["Alert", "No Alert"]

_VALID_ALERT_CONDITIONS: frozenset[str] = frozenset(get_args(WFAlertCondition))
_VALID_ALERT_ENABLED: frozenset[str] = frozenset(get_args(WFAlertEnabled))


@register
@dataclass
class AddNewReminder(Action):
    """Add a new reminder to Reminders.app.

    ``WFCalendarItemTitle`` is the only field that Apple requires to produce a
    meaningful reminder. All other fields are optional. Parameters that carry
    empty-string values in the samples (e.g. ``WFCalendarItemNotes`` and
    ``WFURL``) are emitted when provided as ``""`` to match Apple's wire
    format — pass ``None`` to omit the key entirely.

    ``WFAlertCustomTime`` is only meaningful when ``alert_condition`` is
    "At Time".  ``WFAlertLocationRadius`` (a ``WFQuantityFieldValue`` dict) is
    only meaningful with "When I Arrive"/"When I Leave".  Neither relationship
    is enforced by the schema because samples show the ``WFAlertCondition`` key
    present independently of the alert-enabled state (batch_add_reminders
    action 2 carries ``WFAlertCondition`` but no ``WFAlertEnabled``).

    ``WFFlag`` (flagged/unflagged boolean) was observed in
    batch_add_reminders action 2 (``false``); it is V1-optional and
    modelled here as ``flag``.

    ``WFParentTask`` links a sub-reminder to a parent (WFTextTokenAttachment
    envelope pointing at a prior ``AddNewReminder`` output). Pass the parent
    ``AddNewReminder`` instance directly via :meth:`Action.output`.

    Args:
        title: Reminder title (WFCalendarItemTitle). Required; a plain
            string, Text template, NamedVar, or Output reference.
        calendar: Reminders list name (WFCalendarItemCalendar). Bare string
            ("Shopping", "Chores") as seen in all three samples that set it.
            Pass ``None`` to let Reminders.app use its default list.
        notes: Body text (WFCalendarItemNotes). Empty string observed in
            batch_add_reminders and set_weekend_chores; ``None`` omits the key.
        alert_enabled: "Alert" to enable, "No Alert" to disable. Omit the
            key (pass ``None``) to leave it at system default.
        alert_condition: When to alert — "At Time", "When I Arrive", or
            "When I Leave". Omit when no alert is configured.
        alert_custom_time: Date/time value for "At Time" alerts
            (WFAlertCustomTime). Accepts an Action output, Output, or any
            date-valued ParamValue. Emitted as WFTextTokenString.
        alert_location_radius: Pre-built WFQuantityFieldValue dict for
            location-based alert radius. Pass the raw wire dict. Observed
            only in batch_add_reminders action 2.
        url: URL to attach (WFURL). Empty string emitted when ``""``;
            ``None`` omits the key.
        flag: WFFlag boolean. ``False`` observed in batch_add_reminders
            action 2; ``None`` omits the key.
        parent_task: Parent reminder reference (WFParentTask). Pass the
            preceding ``AddNewReminder`` action directly; its output is
            coerced to a WFTextTokenAttachment. Emitting a parent links
            the new reminder as a sub-task.
    """

    identifier: ClassVar[str] = "is.workflow.actions.addnewreminder"
    default_output_name: ClassVar[str] = "New Reminder"

    title: ParamValue = field(default=None)
    calendar: str | None = field(default=None)
    notes: str | None = field(default=None)
    alert_enabled: WFAlertEnabled | None = field(default=None)
    alert_condition: WFAlertCondition | None = field(default=None)
    alert_custom_time: ParamValue = field(default=None)
    alert_location_radius: dict[str, Any] | None = field(default=None)
    url: str | None = field(default=None)
    flag: bool | None = field(default=None)
    parent_task: ParamValue = field(default=None)

    def __post_init__(self) -> None:
        if self.title is None:
            raise SchemaError(
                "AddNewReminder requires a title (WFCalendarItemTitle). "
                "Pass a string, Text template, NamedVar, or Output. Example: "
                'AddNewReminder(title="Buy milk")'
            )
        if (
            self.alert_enabled is not None
            and self.alert_enabled not in _VALID_ALERT_ENABLED
        ):
            raise SchemaError(
                f"alert_enabled {self.alert_enabled!r} is not valid. "
                f"Expected one of: {sorted(_VALID_ALERT_ENABLED)}"
            )
        if (
            self.alert_condition is not None
            and self.alert_condition not in _VALID_ALERT_CONDITIONS
        ):
            raise SchemaError(
                f"alert_condition {self.alert_condition!r} is not valid. "
                f"Expected one of: {sorted(_VALID_ALERT_CONDITIONS)}"
            )

    def _params(self) -> dict[str, Any]:
        out: dict[str, Any] = {}

        # WFCalendarItemTitle — required; WFTextTokenString slot.
        out["WFCalendarItemTitle"] = coerce_text_field(self.title)

        # WFCalendarItemCalendar — bare string; omit when None.
        if self.calendar is not None:
            out["WFCalendarItemCalendar"] = self.calendar

        # WFCalendarItemNotes — emit empty string when provided as "".
        if self.notes is not None:
            out["WFCalendarItemNotes"] = self.notes

        # WFAlertEnabled — string "Alert" / "No Alert" or absent.
        if self.alert_enabled is not None:
            out["WFAlertEnabled"] = self.alert_enabled

        # WFAlertCondition — present independently of WFAlertEnabled in samples.
        if self.alert_condition is not None:
            out["WFAlertCondition"] = self.alert_condition

        # WFAlertCustomTime — WFTextTokenString; relevant for "At Time".
        if self.alert_custom_time is not None:
            out["WFAlertCustomTime"] = coerce_text_field(self.alert_custom_time)

        # WFAlertLocationRadius — raw WFQuantityFieldValue dict; relevant for
        # location-based conditions ("When I Arrive" / "When I Leave").
        if self.alert_location_radius is not None:
            out["WFAlertLocationRadius"] = self.alert_location_radius

        # WFURL — bare string; emit empty string when provided as "".
        if self.url is not None:
            out["WFURL"] = self.url

        # WFFlag — bool; omit when None.
        if self.flag is not None:
            out["WFFlag"] = self.flag

        # WFParentTask — WFTextTokenAttachment; links as a sub-task.
        if self.parent_task is not None:
            out["WFParentTask"] = coerce_value(self.parent_task)

        return out
