"""SearchMaps — open Apple Maps and run a search query."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action, ParamValue, coerce_value
from shortcut_lib.schema.registry import register


@register
@dataclass
class SearchMaps(Action):
    """Open Apple Maps and run a text or location search.

    Maps to Apple's ``is.workflow.actions.searchmaps`` action (labelled
    "Search in Maps" in Shortcuts.app).  The action opens the Maps app and
    performs a search for the supplied query — useful for looking up
    businesses, points of interest, or addresses.

    **Parameter key — WFInput**

    Both corpus appearances use ``WFInput`` as the sole parameter key.  The
    slot serialises as a plain ``WFTextTokenAttachment`` envelope — the same
    pattern used by the sibling ``getdirections`` action's ``WFDestination``
    slot and by ``GetDistance``'s ``WFGetDistanceDestination`` slot.
    ``coerce_value`` is therefore the correct coercion helper, *not*
    ``coerce_text_field``.

    Note that the key is ``WFInput``, **not** ``WFSearchTerm``.  The
    jellycore entry for this identifier is absent from
    ``data/jellycore_facts.json``; the key name is established solely from
    corpus evidence.

    **Map-family key comparison**

    +-------------------------------+-------------------+-----------------------+
    | Action                        | Destination key   | Source                |
    +===============================+===================+=======================+
    | searchmaps (this action)      | ``WFInput``       | corpus x2             |
    +-------------------------------+-------------------+-----------------------+
    | getdirections                 | ``WFDestination`` | corpus x2             |
    +-------------------------------+-------------------+-----------------------+
    | gettraveltime                 | ``WFDestination`` | corpus x3 (worktree)  |
    +-------------------------------+-------------------+-----------------------+
    | getdistance                   | ``WFGetDistance   | corpus x2 (worktree)  |
    |                               | Destination``     |                       |
    +-------------------------------+-------------------+-----------------------+

    Apple uses inconsistent key names across the Maps family — ``WFInput``
    here versus ``WFDestination`` in both ``getdirections`` and
    ``gettraveltime``.  Do not conflate them.

    **Fields not in the corpus**

    Neither a region/bounding-box override nor any additional display
    options appeared in the two corpus samples.  Those fields are omitted
    here.  Add only when corpus evidence or first-party documentation
    confirms the exact key name.

    **Source verification**

    All claims in this docstring are grounded in the decoded corpus:

    * ``WFInput`` — present in both corpus appearances
      (``samples/decoded/dictionary.xml``, indices 105 and 322).
    * ``WFTextTokenAttachment`` serialisation — confirmed by both samples.
    * No ``WFSearchTerm``, ``WFRegion``, or other keys were observed.
    * ``data/jellycore_facts.json`` returns nothing for this identifier —
      jellycore carries no data for ``is.workflow.actions.searchmaps``.

    Args:
        query: The search text or location value to pass to Maps.  Pass an
            ``Action`` output (e.g. from a previous Maps or Contacts action),
            a ``Value`` object, a bare address or search string, or any
            ``ParamValue`` that resolves to a string or location at run-time.
            Serialised as ``WFInput`` with a ``WFTextTokenAttachment``
            envelope.  When ``None`` the key is omitted, which Shortcuts.app
            treats as an empty search.
    """

    identifier: ClassVar[str] = "is.workflow.actions.searchmaps"
    default_output_name: ClassVar[str] = "Maps"

    query: ParamValue = None

    def _params(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.query is not None:
            # WFInput is a plain attachment slot — both corpus samples emit a
            # bare WFTextTokenAttachment envelope, not a WFTextTokenString
            # wrapper.  coerce_value is correct; coerce_text_field would
            # over-wrap.
            out["WFInput"] = coerce_value(self.query)
        return out
