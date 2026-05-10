"""SetVolume — set the device output volume to a given level."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action, ParamValue, SchemaError, coerce_value
from shortcut_lib.schema.registry import register


@register
@dataclass
class SetVolume(Action):
    """Set the device's output volume to a specific level.

    Apple display name: "Set Volume".
    Identifier: ``is.workflow.actions.setvolume``.
    Minimum host: iOS 14.

    Corpus appearances: samples/decoded/dictionary.xml — two occurrences,
    both with empty ``WFWorkflowActionParameters`` (``<dict/>``), so
    ``WFVolume`` is optional at the wire level (Apple uses whatever the
    device last had).

    Args:
        volume: Target volume in the range ``0.0`` (mute) to ``1.0``
            (maximum). Wire key ``WFVolume`` (float or variable ref).
            Jellycore names the key ``WFVolume`` — this matches the
            WF-prefixed convention and is the expected wire key; corpus is
            silent (empty params) so no direct confirmation exists in the
            sample set. Omit to leave the device volume unchanged (Apple
            will open the action with its last-used value).

            When passing a variable reference, use an Action output or
            ``NamedVar`` — any value that ``coerce_value`` can turn into a
            ``WFTextTokenAttachment`` envelope.

    Returns:
        This action produces no output. ``default_output_name`` is not set.

    Wire-format notes:
        - Both corpus samples carry an empty params dict; ``WFVolume`` is
          therefore not required by iOS.
        - When present, ``WFVolume`` is expected to be a float (e.g.
          ``0.5``) or a variable-reference envelope. No Literal closed set
          is implied — the UI shows a continuous slider.
        - Volume is proportional (0.0-1.0), not a percentage integer.
          There is no separate ``Mute`` boolean in this action; use
          ``volume=0.0`` to silence the device.

    AppIntent-aliasing: jellycore lists the single parameter key as
    ``WFVolume`` — this is already WF-prefixed and aligns with the broader
    WF-key convention, so no aliasing inference is required.

    Validation:
        When a float is supplied we check ``0.0 ≤ volume ≤ 1.0`` and raise
        ``SchemaError`` if it falls outside that range.
    """

    identifier: ClassVar[str] = "is.workflow.actions.setvolume"

    volume: ParamValue = None

    def _params(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.volume is None:
            return out
        if isinstance(self.volume, float):
            if not (0.0 <= self.volume <= 1.0):
                raise SchemaError(
                    f"SetVolume.volume must be in [0.0, 1.0]; got {self.volume!r}"
                )
            out["WFVolume"] = self.volume
        elif isinstance(self.volume, int) and not isinstance(self.volume, bool):
            coerced: float = float(self.volume)
            if not (0.0 <= coerced <= 1.0):
                raise SchemaError(
                    f"SetVolume.volume must be in [0.0, 1.0]; got {self.volume!r}"
                )
            out["WFVolume"] = coerced
        else:
            out["WFVolume"] = coerce_value(self.volume)
        return out
