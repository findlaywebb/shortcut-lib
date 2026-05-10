"""FilterCalendarEvents — query the calendar with optional filter predicates.

Apple identifier: ``is.workflow.actions.filter.calendarevents``.
Appears in Shortcuts.app as "Find Calendar Events".

**V1.5 design note — filter as raw dict pass-through**

The ``WFContentItemFilter`` parameter carries a ``WFContentPredicateTableTemplate``
envelope that contains an array of heterogeneous predicate dicts (bounded-date
predicates, enumeration predicates for Calendar name, bool predicates for
"Is All Day", etc.). Modelling each predicate type as a typed Python class is
valuable but is explicitly deferred to V2 — it would require understanding at
least five distinct predicate shapes across all of Apple's ``filter.*`` actions,
none of which have been cross-validated outside the four corpus appearances
collected for this action.

For V1.5 the ``content_item_filter`` field accepts the raw wire-format envelope
directly. Users who need a filter can copy the envelope from a decoded sample
(e.g. ``samples/decoded/daily_standup.xml``) or from the helper constant
``NEXT_7_DAYS_FILTER`` defined below for the extremely common "next N days" pattern.

The ``content_item_input`` field accepts any :class:`~shortcut_lib.schema.base.ParamValue`
(typically a previous action's output via ``action.output()``) and maps to the
Apple ``WFContentItemInputParameter`` slot, which feeds an existing collection
of calendar events into this filter step.

Observed corpus parameters (4 appearances, 3 files):
  - ``WFContentItemFilter``        — filter envelope (WFContentPredicateTableTemplate)
  - ``WFContentItemInputParameter`` — upstream event collection (WFTextTokenAttachment)
  - UUID                           — standard action UUID

No ``WFContentItemSortProperty``, ``WFContentItemSortOrder``, or
``WFContentItemLimitNumber`` keys were observed in any of the four corpus
samples.  Those keys may exist in richer shortcuts not present in this corpus;
they are not modelled here to avoid speculative fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action, ParamValue, coerce_value
from shortcut_lib.schema.registry import register

# ---------------------------------------------------------------------------
# Convenience constant — the most common "next 7 days" bounded-date filter
# observed in all three sample files that carry a filter (daily_standup.xml x2,
# running_late.xml x1).  The prefix=1 variant means "match ALL predicates";
# prefix=0 means "match ANY predicate".
#
# Shape reference (from daily_standup.xml, second appearance):
#   WFActionParameterFilterPrefix=1 (match ALL), WFActionParameterFilterTemplates
#   contains one bounded Start Date predicate, WFContentPredicateBoundedDate=false
# ---------------------------------------------------------------------------

NEXT_7_DAYS_FILTER: dict[str, Any] = {
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
            }
        ],
        "WFContentPredicateBoundedDate": False,
    },
    "WFSerializationType": "WFContentPredicateTableTemplate",
}
"""Wire-format envelope for "Start Date in the next 7 days (match ALL)"."""


@register
@dataclass
class FilterCalendarEvents(Action):
    """Query the calendar with optional filter predicates.

    Wraps ``is.workflow.actions.filter.calendarevents`` — Apple's
    "Find Calendar Events" action.

    Args:
        content_item_filter: The filter predicate envelope. Must be a dict in
            Apple's ``WFContentPredicateTableTemplate`` wire format, or ``None``
            to pass through without filtering (produces a bare action with only
            a UUID, as in ``samples/decoded/dictionary.xml``). Use the
            ``NEXT_7_DAYS_FILTER`` constant as a starting point for the common
            "next 7 days" pattern, or copy from a decoded sample.
        content_item_input: Optional upstream collection of calendar events to
            filter. Pass a previous action's output (e.g. ``get_events.output()``
            or ``Output(uuid=..., name="Events")``). When ``None`` the action
            reads from the clipboard / implicit input, which is typical for the
            first step in a calendar workflow.
    """

    identifier: ClassVar[str] = "is.workflow.actions.filter.calendarevents"
    default_output_name: ClassVar[str] = "Calendar Events"

    content_item_filter: dict[str, Any] | None = field(default=None)
    content_item_input: ParamValue = None

    def _params(self) -> dict[str, Any]:
        """Return the WF parameter dict for the Find Calendar Events action."""
        out: dict[str, Any] = {}

        if self.content_item_filter is not None:
            out["WFContentItemFilter"] = self.content_item_filter

        if self.content_item_input is not None:
            out["WFContentItemInputParameter"] = coerce_value(self.content_item_input)

        return out
