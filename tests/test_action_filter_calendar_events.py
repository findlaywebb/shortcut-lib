"""Tests for FilterCalendarEvents action schema.

Wire-format expectations are derived from three decoded samples:
- ``samples/decoded/daily_standup.xml`` (2 appearances, UUID indices 22 and 23)
- ``samples/decoded/running_late.xml``  (1 appearance)
- ``samples/decoded/dictionary.xml``    (1 bare appearance — no filter, no input)
"""

from __future__ import annotations

import shortcut_lib.schema.actions.filter_calendar_events  # noqa: F401 — trigger registration
from shortcut_lib.schema.actions.filter_calendar_events import (
    NEXT_7_DAYS_FILTER,
    FilterCalendarEvents,
)
from shortcut_lib.schema.registry import lookup
from shortcut_lib.schema.values import Output

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _params(action: FilterCalendarEvents) -> dict:
    """Extract WFWorkflowActionParameters from an action."""
    return action.to_action_dict()["WFWorkflowActionParameters"]


# ---------------------------------------------------------------------------
# Test 1 — bare invocation (dictionary.xml pattern: no filter, no input)
# ---------------------------------------------------------------------------


def test_bare_invocation_omits_filter_and_input() -> None:
    """FilterCalendarEvents() with no args emits only UUID.

    Mirrors the bare appearance in ``samples/decoded/dictionary.xml`` where
    the action carries no WFContentItemFilter and no WFContentItemInputParameter.
    """
    action = FilterCalendarEvents()
    d = action.to_action_dict()

    assert (
        d["WFWorkflowActionIdentifier"] == "is.workflow.actions.filter.calendarevents"
    )
    params = d["WFWorkflowActionParameters"]

    assert "WFContentItemFilter" not in params
    assert "WFContentItemInputParameter" not in params
    assert "UUID" in params


# ---------------------------------------------------------------------------
# Test 2 — filter only, no upstream input (running_late.xml pattern)
# ---------------------------------------------------------------------------


def test_filter_without_input_emits_wf_content_item_filter() -> None:
    """Providing a filter dict but no upstream input emits WFContentItemFilter only.

    Mirrors ``samples/decoded/running_late.xml`` where WFContentItemFilter is
    present but WFContentItemInputParameter is absent.
    """
    action = FilterCalendarEvents(content_item_filter=NEXT_7_DAYS_FILTER)
    params = _params(action)

    assert "WFContentItemFilter" in params
    assert "WFContentItemInputParameter" not in params

    filt = params["WFContentItemFilter"]
    assert filt["WFSerializationType"] == "WFContentPredicateTableTemplate"
    inner = filt["Value"]
    assert "WFActionParameterFilterPrefix" in inner
    assert "WFActionParameterFilterTemplates" in inner
    assert "WFContentPredicateBoundedDate" in inner


# ---------------------------------------------------------------------------
# Test 3 — filter + upstream input (daily_standup.xml pattern)
# ---------------------------------------------------------------------------


def test_filter_with_input_emits_both_parameters() -> None:
    """Filter + upstream input emits both WFContentItemFilter and WFContentItemInputParameter.

    Mirrors the first ``filter.calendarevents`` in ``daily_standup.xml`` (UUID
    CF17C893) where an upstream "Events" action output is piped in alongside
    the filter envelope.
    """
    upstream_uuid = "F0C1D259-8C6A-4F82-B3F9-0026EA4DD46A"
    upstream = Output(uuid=upstream_uuid, name="Events")
    action = FilterCalendarEvents(
        content_item_filter=NEXT_7_DAYS_FILTER,
        content_item_input=upstream,
    )
    params = _params(action)

    assert "WFContentItemFilter" in params
    assert "WFContentItemInputParameter" in params

    inp = params["WFContentItemInputParameter"]
    assert inp["WFSerializationType"] == "WFTextTokenAttachment"
    assert inp["Value"]["OutputUUID"] == upstream_uuid
    assert inp["Value"]["OutputName"] == "Events"
    assert inp["Value"]["Type"] == "ActionOutput"


# ---------------------------------------------------------------------------
# Test 4 — wire-format equivalence vs daily_standup.xml (second appearance)
# ---------------------------------------------------------------------------


def test_wire_format_equivalence_daily_standup_second() -> None:
    """Emitted shape matches the second filter.calendarevents in daily_standup.xml.

    That action (UUID 5EE01323) has:
      - WFActionParameterFilterPrefix = 1  (match ALL)
      - Two predicates: Start Date (bounded, next 7 days) + Is All Day (bool false)
      - WFContentPredicateBoundedDate = false
      - WFContentItemInputParameter pointing at UUID CF17C893 ("Calendar Events")
    """
    is_all_day_predicate = {
        "Bool": False,
        "Operator": 4,
        "Property": "Is All Day",
        "Removable": True,
        "VariableOverrides": {},
    }
    composite_filter: dict = {
        "Value": {
            "WFActionParameterFilterPrefix": 1,
            "WFActionParameterFilterTemplates": [
                {
                    "Bounded": True,
                    "Number": 7,
                    "Operator": 1002,
                    "Property": "Start Date",
                    "Removable": False,
                    "Unit": 16,
                    "VariableOverrides": {},
                },
                is_all_day_predicate,
            ],
            "WFContentPredicateBoundedDate": False,
        },
        "WFSerializationType": "WFContentPredicateTableTemplate",
    }

    upstream = Output(
        uuid="CF17C893-AB3F-435F-B01B-9B2E48A61B57",
        name="Calendar Events",
    )
    action = FilterCalendarEvents(
        uuid="5EE01323-C223-441F-A12A-70F07905DA0B",
        content_item_filter=composite_filter,
        content_item_input=upstream,
    )
    params = _params(action)

    # UUID round-trips.
    assert params["UUID"] == "5EE01323-C223-441F-A12A-70F07905DA0B"

    # Filter envelope.
    filt = params["WFContentItemFilter"]
    assert filt["WFSerializationType"] == "WFContentPredicateTableTemplate"
    inner = filt["Value"]
    assert inner["WFActionParameterFilterPrefix"] == 1
    assert inner["WFContentPredicateBoundedDate"] is False
    templates = inner["WFActionParameterFilterTemplates"]
    assert len(templates) == 2
    assert templates[0]["Property"] == "Start Date"
    assert templates[0]["Bounded"] is True
    assert templates[0]["Number"] == 7
    assert templates[1]["Property"] == "Is All Day"
    assert templates[1]["Bool"] is False

    # Input parameter.
    inp = params["WFContentItemInputParameter"]
    assert inp["WFSerializationType"] == "WFTextTokenAttachment"
    assert inp["Value"]["OutputUUID"] == "CF17C893-AB3F-435F-B01B-9B2E48A61B57"
    assert inp["Value"]["OutputName"] == "Calendar Events"


# ---------------------------------------------------------------------------
# Test 5 — NEXT_7_DAYS_FILTER constant is structurally valid
# ---------------------------------------------------------------------------


def test_next_7_days_filter_constant_structure() -> None:
    """NEXT_7_DAYS_FILTER has the correct WFContentPredicateTableTemplate structure."""
    assert (
        NEXT_7_DAYS_FILTER["WFSerializationType"] == "WFContentPredicateTableTemplate"
    )
    inner = NEXT_7_DAYS_FILTER["Value"]
    assert inner["WFActionParameterFilterPrefix"] == 1
    assert inner["WFContentPredicateBoundedDate"] is False
    templates = inner["WFActionParameterFilterTemplates"]
    assert len(templates) == 1
    t = templates[0]
    assert t["Property"] == "Start Date"
    assert t["Bounded"] is True
    assert t["Number"] == 7
    assert t["Operator"] == 1002
    assert t["Unit"] == 16


# ---------------------------------------------------------------------------
# Test 6 — registry lookup
# ---------------------------------------------------------------------------


def test_filter_calendar_events_registered() -> None:
    """FilterCalendarEvents is findable in the registry by its identifier."""
    cls = lookup("is.workflow.actions.filter.calendarevents")
    assert cls is FilterCalendarEvents


# ---------------------------------------------------------------------------
# Test 7 — default output name
# ---------------------------------------------------------------------------


def test_default_output_name() -> None:
    """default_output_name is 'Calendar Events' — Apple's UI label."""
    assert FilterCalendarEvents.default_output_name == "Calendar Events"


# ---------------------------------------------------------------------------
# Test 8 — output() for downstream chaining
# ---------------------------------------------------------------------------


def test_output_reference_for_downstream_chaining() -> None:
    """output() returns an Output with the action's UUID and a usable name.

    Tests that a FilterCalendarEvents result can be piped into the
    content_item_input of a second filter, as in daily_standup.xml.
    """
    first = FilterCalendarEvents(content_item_filter=NEXT_7_DAYS_FILTER)
    second = FilterCalendarEvents(
        content_item_filter=NEXT_7_DAYS_FILTER,
        content_item_input=first.output(),
    )
    params = _params(second)

    inp = params["WFContentItemInputParameter"]
    assert inp["WFSerializationType"] == "WFTextTokenAttachment"
    assert inp["Value"]["OutputUUID"] == first.uuid
    assert inp["Value"]["Type"] == "ActionOutput"


# ---------------------------------------------------------------------------
# Test 9 — passing a raw dict filter (corpus shape from running_late.xml)
# ---------------------------------------------------------------------------


def test_raw_dict_filter_with_enumeration_predicate() -> None:
    """A Calendar-name enumeration predicate passes through the filter field verbatim.

    Mirrors the first appearance in daily_standup.xml (UUID CF17C893) which has
    two Calendar enumeration predicates alongside the Start Date bounded predicate.
    """
    raw_filter: dict = {
        "Value": {
            "WFActionParameterFilterPrefix": 0,
            "WFActionParameterFilterTemplates": [
                {
                    "Bounded": True,
                    "Number": 7,
                    "Operator": 1002,
                    "Property": "Start Date",
                    "Removable": False,
                    "Unit": 16,
                    "VariableOverrides": {},
                },
                {
                    "Enumeration": "DeskConnect/Workflow Team",
                    "Operator": 4,
                    "Property": "Calendar",
                    "Removable": True,
                    "VariableOverrides": {},
                },
                {
                    "Enumeration": "matthew@deskconnect.com",
                    "Operator": 4,
                    "Property": "Calendar",
                    "Removable": True,
                    "VariableOverrides": {},
                },
            ],
            "WFContentPredicateBoundedDate": False,
        },
        "WFSerializationType": "WFContentPredicateTableTemplate",
    }
    action = FilterCalendarEvents(content_item_filter=raw_filter)
    params = _params(action)

    filt = params["WFContentItemFilter"]
    inner = filt["Value"]
    # Prefix 0 = match ANY.
    assert inner["WFActionParameterFilterPrefix"] == 0
    templates = inner["WFActionParameterFilterTemplates"]
    assert len(templates) == 3
    enum_predicates = [t for t in templates if "Enumeration" in t]
    assert len(enum_predicates) == 2
    calendar_names = {t["Enumeration"] for t in enum_predicates}
    assert calendar_names == {"DeskConnect/Workflow Team", "matthew@deskconnect.com"}


# ---------------------------------------------------------------------------
# Test 10 — identifier is correct
# ---------------------------------------------------------------------------


def test_identifier() -> None:
    """Class-level identifier matches Apple's wire format."""
    assert (
        FilterCalendarEvents.identifier == "is.workflow.actions.filter.calendarevents"
    )


# ---------------------------------------------------------------------------
# Test 11 — custom_output_name propagates to wire dict
# ---------------------------------------------------------------------------


def test_custom_output_name() -> None:
    """custom_output_name populates CustomOutputName in emitted dict."""
    action = FilterCalendarEvents(
        content_item_filter=NEXT_7_DAYS_FILTER,
        custom_output_name="Today's Meetings",
    )
    d = action.to_action_dict()
    assert d["WFWorkflowActionParameters"]["CustomOutputName"] == "Today's Meetings"


# ---------------------------------------------------------------------------
# Test 12 — content_item_filter=None skips the key (bare action)
# ---------------------------------------------------------------------------


def test_none_filter_skips_key() -> None:
    """Explicitly passing content_item_filter=None omits WFContentItemFilter."""
    action = FilterCalendarEvents(content_item_filter=None)
    params = _params(action)
    assert "WFContentItemFilter" not in params


# ---------------------------------------------------------------------------
# Test 13 — content_item_input=None skips the key
# ---------------------------------------------------------------------------


def test_none_input_skips_key() -> None:
    """Explicitly passing content_item_input=None omits WFContentItemInputParameter."""
    action = FilterCalendarEvents(
        content_item_filter=NEXT_7_DAYS_FILTER,
        content_item_input=None,
    )
    params = _params(action)
    assert "WFContentItemInputParameter" not in params
