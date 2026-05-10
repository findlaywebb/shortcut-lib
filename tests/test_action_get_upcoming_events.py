"""Tests for the GetUpcomingEvents action schema."""

from __future__ import annotations

import pytest

import shortcut_lib.schema.actions.get_upcoming_events  # noqa: F401 — trigger registration
from shortcut_lib.schema.actions.get_upcoming_events import GetUpcomingEvents
from shortcut_lib.schema.base import SchemaError
from shortcut_lib.schema.registry import lookup


def test_get_upcoming_events_defaults() -> None:
    """Default construction emits WFDateSpecifier='Today', no calendar key, no count.

    dictionary.xml:4701 sample has UUID-only params (no WFGetUpcomingItemCalendar
    key at all), confirming that an empty calendar should be omitted entirely.
    """
    action = GetUpcomingEvents()
    result = action.to_action_dict()
    assert (
        result["WFWorkflowActionIdentifier"] == "is.workflow.actions.getupcomingevents"
    )
    params = result["WFWorkflowActionParameters"]
    assert params["WFDateSpecifier"] == "Today"
    assert "WFGetUpcomingItemCalendar" not in params
    assert "WFGetUpcomingItemCount" not in params


def test_get_upcoming_events_with_count() -> None:
    """Setting count emits WFGetUpcomingItemCount as integer.

    Mirrors daily_standup.xml:34 where WFGetUpcomingItemCount=24.
    """
    action = GetUpcomingEvents(count=24)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFGetUpcomingItemCount"] == 24


def test_get_upcoming_events_with_calendar() -> None:
    """A named calendar is emitted verbatim as WFGetUpcomingItemCalendar."""
    action = GetUpcomingEvents(calendar="Work")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFGetUpcomingItemCalendar"] == "Work"


def test_get_upcoming_events_this_week() -> None:
    """date_specifier='This Week' is accepted and emitted correctly."""
    action = GetUpcomingEvents(date_specifier="This Week")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFDateSpecifier"] == "This Week"


def test_get_upcoming_events_all() -> None:
    """date_specifier='All' is accepted and emitted correctly."""
    action = GetUpcomingEvents(date_specifier="All")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFDateSpecifier"] == "All"


def test_get_upcoming_events_invalid_date_specifier() -> None:
    """An unrecognised date_specifier raises SchemaError naming the bad value."""
    with pytest.raises(SchemaError, match="'Monthly'"):
        GetUpcomingEvents(date_specifier="Monthly")  # ty: ignore[invalid-argument-type]


def test_get_upcoming_events_invalid_count() -> None:
    """A non-positive count raises SchemaError."""
    with pytest.raises(SchemaError, match="count must be a positive integer"):
        GetUpcomingEvents(count=0)


def test_get_upcoming_events_registered() -> None:
    """GetUpcomingEvents is findable in the registry by its identifier."""
    cls = lookup("is.workflow.actions.getupcomingevents")
    assert cls is GetUpcomingEvents


def test_get_upcoming_events_default_output_name() -> None:
    """GetUpcomingEvents.default_output_name is 'Upcoming Events'."""
    assert GetUpcomingEvents.default_output_name == "Upcoming Events"


def test_get_upcoming_events_wire_format_equivalence_daily_standup() -> None:
    """Wire format matches daily_standup.xml:34 sample exactly (minus UUID).

    Sample: WFDateSpecifier='Today', WFGetUpcomingItemCalendar='',
    WFGetUpcomingItemCount=24 (lines 465-470 of daily_standup.xml).

    Note: the sample emits WFGetUpcomingItemCalendar as an explicit empty
    string, but our schema omits the key when empty. The wire format is
    otherwise equivalent; Apple treats absent and empty-string calendar the
    same way.
    """
    action = GetUpcomingEvents(
        date_specifier="Today",
        calendar="",
        count=24,
        uuid="F0C1D259-8C6A-4F82-B3F9-0026EA4DD46A",
    )
    result = action.to_action_dict()
    assert (
        result["WFWorkflowActionIdentifier"] == "is.workflow.actions.getupcomingevents"
    )
    params = result["WFWorkflowActionParameters"]
    assert params["UUID"] == "F0C1D259-8C6A-4F82-B3F9-0026EA4DD46A"
    assert params["WFDateSpecifier"] == "Today"
    assert "WFGetUpcomingItemCalendar" not in params
    assert params["WFGetUpcomingItemCount"] == 24


def test_get_upcoming_events_bare_omits_calendar() -> None:
    """Bare GetUpcomingEvents() emits no WFGetUpcomingItemCalendar key.

    Matches dictionary.xml:4701 sample exactly — UUID-only params dict.
    """
    action = GetUpcomingEvents(uuid="99E86E8B-4C6B-41C6-989C-693B10EF95B5")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "WFGetUpcomingItemCalendar" not in params
    assert "WFGetUpcomingItemCount" not in params


def test_get_upcoming_events_wire_format_equivalence_dictionary() -> None:
    """Wire format matches dictionary.xml:4701 sample exactly (minus UUID).

    Sample at lines 4699-4707 of dictionary.xml: UUID-only params dict.
    Default construction must produce WFDateSpecifier only (calendar and
    count both absent).
    """
    action = GetUpcomingEvents(uuid="99E86E8B-4C6B-41C6-989C-693B10EF95B5")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["UUID"] == "99E86E8B-4C6B-41C6-989C-693B10EF95B5"
    assert "WFGetUpcomingItemCalendar" not in params
    assert "WFGetUpcomingItemCount" not in params
