"""SetDoNotDisturb — enable, disable, or toggle a Focus / DND session."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action, ParamValue, coerce_value
from shortcut_lib.schema.registry import register


@register
@dataclass
class SetDoNotDisturb(Action):
    """Enable, disable, or time-bound a Focus / Do Not Disturb session.

    Apple display name: "Set Focus" (was "Set Do Not Disturb" on iOS 14).
    Identifier: ``is.workflow.actions.dnd.set``.
    Minimum host: iOS 14.

    Corpus appearances: samples/decoded/start_pomodoro.xml (rich params),
    samples/decoded/dictionary.xml (empty dict — all keys optional).

    Args:
        enabled: Whether to turn the focus on (``1``/``True``) or off
            (``0``/``False``). Wire key ``Enabled`` (integer 0/1).
            Omit to use Apple's default (toggle). Note: jellycore lists
            the key as ``Enabled`` (confirmed against corpus).
        assertion_type: When to end the focus session. Observed corpus
            value is ``"Time"`` (wire key ``AssertionType``). Other values
            Apple may accept include ``"Event"`` and ``"Indefinitely"`` but
            are not confirmed in this corpus. Omit to let Apple choose.
        focus_modes: A dict with ``DisplayString`` (human label) and
            ``Identifier`` (reverse-DNS bundle ID, e.g.
            ``"com.apple.focus.work"``) selecting which Focus preset to
            activate. Wire key ``FocusModes``. Omit to act on the most
            recently used Focus or Do Not Disturb.

            Example (from start_pomodoro.xml)::

                {
                    "DisplayString": "Work",
                    "Identifier": "com.apple.focus.work",
                }

        until: A date/time value ending the session. Accepts an Action
            output (chained), ``NamedVar``, or ``Text`` reference. Wire
            key ``Time`` — emitted as a ``WFTextTokenString`` envelope
            when a variable reference is passed. Omit for indefinite or
            event-based sessions.
        event: An event-based end trigger. Accepts an Action output or
            variable reference. Wire key ``Event`` — emitted as a
            ``WFTextTokenAttachment`` envelope (single variable-ref slot).
            From start_pomodoro.xml both ``Time`` and ``Event`` carried the
            same ``ActionOutput`` ref (``"Break End Time"``); the
            relationship between the two is unclear — pass both when
            reproducing that exact wire shape.

    Returns:
        This action produces no output UUID. ``default_output_name`` is
        not set; ``output()`` returns the UUID-keyed reference anyway,
        but Shortcuts.app will not surface it as a magic variable.

    Wire-format notes:
        - Empty ``WFWorkflowActionParameters`` (``<dict/>``) is valid and
          observed in dictionary.xml (both corpus appearances #1 and #2
          are bare; only start_pomodoro.xml carries the full param set).
        - ``Enabled`` is an integer 1/0, not a boolean string.
        - ``FocusModes`` is a plain dict, not a WF envelope.
        - ``Time`` is a ``WFTextTokenString`` (multi-char template); even
          a single variable-ref slot uses the templated envelope here, not
          ``WFTextTokenAttachment``.
        - ``Event`` is a ``WFTextTokenAttachment`` (single-var slot).

    AppIntent-aliasing: jellycore lists the single parameter key as
    ``Enabled`` — this matches the corpus wire key exactly (no WF prefix),
    confirming it is *not* aliased to a WF-prefixed name. All other param
    keys (``AssertionType``, ``FocusModes``, ``Time``, ``Event``) come
    from corpus observation only.
    """

    identifier: ClassVar[str] = "is.workflow.actions.dnd.set"

    enabled: bool | None = None
    assertion_type: str | None = None
    focus_modes: dict[str, str] | None = None
    until: ParamValue = field(default=None)
    event: ParamValue = field(default=None)

    def _params(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.enabled is not None:
            out["Enabled"] = 1 if self.enabled else 0
        if self.assertion_type is not None:
            out["AssertionType"] = self.assertion_type
        if self.focus_modes is not None:
            out["FocusModes"] = self.focus_modes
        if self.until is not None:
            # Apple wraps the time ref in a WFTextTokenString (observed in
            # start_pomodoro.xml even for a single ActionOutput attachment).
            coerced = coerce_value(self.until)
            if (
                isinstance(coerced, dict)
                and coerced.get("WFSerializationType") == "WFTextTokenAttachment"
            ):
                # Rewrap as one-attachment WFTextTokenString per wire format.
                out["Time"] = {
                    "Value": {
                        "string": "￼",
                        "attachmentsByRange": {"{0, 1}": coerced["Value"]},
                    },
                    "WFSerializationType": "WFTextTokenString",
                }
            else:
                out["Time"] = coerced
        if self.event is not None:
            out["Event"] = coerce_value(self.event)
        return out
