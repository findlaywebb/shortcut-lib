"""GetDirections — show turn-by-turn directions in Apple Maps."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action, ParamValue, coerce_value
from shortcut_lib.schema.registry import register


@register
@dataclass
class GetDirections(Action):
    """Open Apple Maps and show directions to a destination.

    Maps to Apple's ``is.workflow.actions.getdirections`` action (labelled
    "Show Directions" or "Get Directions" in Shortcuts.app, depending on OS
    version).  The action opens the Maps app and starts navigation to the
    supplied destination.

    **Parameter key — WFDestination**

    Both corpus appearances use ``WFDestination`` as the sole parameter key.
    The slot serialises as a plain ``WFTextTokenAttachment`` envelope — the
    same pattern used by the sibling ``gettraveltime`` action.  ``coerce_value``
    is therefore the correct coercion helper, *not* ``coerce_text_field``.

    Note the key is **not** ``WFGetDistanceDestination`` (used by the
    ``getdistance`` sibling) — Apple uses inconsistent keys across the Maps
    family.  See the table below.

    **Map-family key comparison**

    +-------------------------------+-------------------+-----------------------+
    | Action                        | Destination key   | Source                |
    +===============================+===================+=======================+
    | searchmaps                    | ``WFInput``       | corpus x2             |
    +-------------------------------+-------------------+-----------------------+
    | getdirections (this action)   | ``WFDestination`` | corpus x2             |
    +-------------------------------+-------------------+-----------------------+
    | gettraveltime                 | ``WFDestination`` | corpus x3 (worktree)  |
    +-------------------------------+-------------------+-----------------------+
    | getdistance                   | ``WFGetDistance   | corpus x2 (worktree)  |
    |                               | Destination``     |                       |
    +-------------------------------+-------------------+-----------------------+

    **Fields not in the corpus**

    Neither a transport-mode override (e.g. ``WFTransportType`` / driving vs
    walking vs transit) nor a starting-point override appeared in the two
    corpus samples.  The ``gettraveltime`` sibling *does* support
    ``WFTransportType`` — it is plausible but unconfirmed for this action.
    Those fields are intentionally omitted here; add them only when corpus
    evidence or first-party documentation confirms the exact key names.

    **Source verification**

    All claims in this docstring are grounded in the decoded corpus:

    * ``WFDestination`` — present in both corpus appearances
      (``samples/decoded/dictionary.xml``, indices 104 and 321).
    * ``WFTextTokenAttachment`` serialisation — confirmed by both samples.
    * No ``WFTransportType``, ``WFFromAddress``, or other keys were observed.
    * ``data/jellycore_facts.json`` returns nothing for this identifier —
      jellycore carries no data for ``is.workflow.actions.getdirections``.

    Args:
        destination: The target location.  Pass an ``Action`` output (e.g.
            from a Search Maps or Get Contacts action), a ``Value`` object,
            a bare address string, or any ``ParamValue`` that resolves to a
            location at run-time.  Serialised as ``WFDestination`` with a
            ``WFTextTokenAttachment`` envelope.  When ``None`` the key is
            omitted, which Shortcuts.app treats as "no destination" and may
            prompt the user at run-time.
    """

    identifier: ClassVar[str] = "is.workflow.actions.getdirections"
    default_output_name: ClassVar[str] = "Maps"

    destination: ParamValue = None

    def _params(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.destination is not None:
            # WFDestination is a plain attachment slot — both corpus samples
            # emit a bare WFTextTokenAttachment envelope, not a
            # WFTextTokenString wrapper.  This matches the sibling
            # gettraveltime action's WFDestination slot exactly.
            out["WFDestination"] = coerce_value(self.destination)
        return out
