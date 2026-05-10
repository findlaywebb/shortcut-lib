"""GetDistance — compute straight-line distance to a destination location."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action, ParamValue, coerce_value
from shortcut_lib.schema.registry import register


@register
@dataclass
class GetDistance(Action):
    """Get the straight-line distance from the current location to a destination.

    Maps to Apple's ``is.workflow.actions.getdistance`` action (labelled
    "Get Distance" in Shortcuts.app).

    The action measures the as-the-crow-flies distance between the device's
    current location and the provided destination.  Pass the output of a
    Maps or Contacts action, a variable containing a location, or any
    ``ParamValue`` that resolves to a location at run-time.

    **Parameter key — WFGetDistanceDestination**

    Both corpus appearances use ``WFGetDistanceDestination`` (not the bare
    ``WFDestination`` key used by the sibling ``gettraveltime`` action).
    The slot serialises as a plain ``WFTextTokenAttachment`` envelope, the
    same pattern seen in ``gettraveltime``'s destination slot.  ``coerce_value``
    is therefore the correct coercion helper — *not* ``coerce_text_field``.

    **Fields not in the corpus**

    Neither distance-unit selection (e.g. ``WFDistanceUnit``) nor a separate
    origin override appeared in the 2 corpus samples.  Apple's UI does expose
    a unit picker in some OS versions, but because no such key was observed in
    any decoded sample, those parameters are intentionally omitted here.  Add
    them only when corpus evidence or first-party documentation confirms the
    exact key name.

    **Source verification**

    All claims in this docstring are grounded in the decoded corpus:

    * ``WFGetDistanceDestination`` — present in both corpus appearances
      (``samples/decoded/dictionary.xml``, indices 112 and 317).
    * ``WFTextTokenAttachment`` serialisation — confirmed by both samples.
    * No ``WFDistanceUnit``, ``WFGetDistanceMode``, or ``WFFromAddress`` key
      was observed in either sample.
    * ``data/jellycore_facts.json`` returns ``null`` for this identifier —
      jellycore carries no data for ``is.workflow.actions.getdistance``.

    Args:
        destination: The target location.  Pass an ``Action`` output (e.g.
            from a Search Maps or Get Contacts action), a ``Value`` object,
            a bare address string, or any ``ParamValue`` that resolves to a
            location.  Serialised as ``WFGetDistanceDestination`` with a
            ``WFTextTokenAttachment`` envelope.  When ``None`` the key is
            omitted, which Shortcuts.app treats as "no location" and shows
            the prompt input at run-time.
    """

    identifier: ClassVar[str] = "is.workflow.actions.getdistance"
    default_output_name: ClassVar[str] = "Distance"

    destination: ParamValue = None

    def _params(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.destination is not None:
            # WFGetDistanceDestination is a plain attachment slot — both corpus
            # samples emit a bare WFTextTokenAttachment envelope (not a
            # WFTextTokenString wrapper), mirroring the WFDestination slot in
            # the sibling gettraveltime action.
            out["WFGetDistanceDestination"] = coerce_value(self.destination)
        return out
