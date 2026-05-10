"""FormatNumber — format a number as a string in Shortcuts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action, ParamValue, coerce_value
from shortcut_lib.schema.registry import register


@register
@dataclass
class FormatNumber(Action):
    """Format a number as a string using optional decimal-place rounding.

    Apple display name: **Format Number**
    Identifier: ``is.workflow.actions.format.number``
    Minimum host: iOS 14

    The action converts a number to a text string. The Shortcuts.app UI
    exposes a decimal-places spinner (``WFNumberFormatDecimalPlaces``);
    when omitted Apple defaults to 2 decimal places in the formatted
    output. The 2-appearance corpus + jellycore both show only this
    decimal-places knob; Shortcuts.app's UI does have additional style
    modes (currency / percent / scientific / spell-out) that aren't
    exercised by either source — see the Quirks section.

    Args:
        number: Number to format. Pass an :class:`~shortcut_lib.schema.base.Action`
            whose output is a number, a :class:`~shortcut_lib.schema.base.Value`,
            or a Python ``int`` / ``float``. Corresponds to the ``WFNumber``
            wire key. Emitted as a ``WFTextTokenAttachment`` envelope when
            given an Action or Output reference. Omitted when ``None``
            (action runs against Shortcut Input at runtime).
            Confirmed wire key: corpus ``samples/decoded/dictionary.xml``
            lines 332-345 and 4523-4536.
        decimal_places: Number of decimal places in the formatted output.
            Corresponds to the ``WFNumberFormatDecimalPlaces`` wire key.
            When ``None`` (the default) the key is omitted from the
            emitted dict and Apple applies its own runtime default (2).
            Jellycore-confirmed parameter key.

    Returns:
        A ``Formatted Number`` text string. Reference via
        ``format_number.output()`` in subsequent actions.

    Quirks:
        - ``WFNumber`` uses a bare ``WFTextTokenAttachment`` envelope (not
          ``WFTextTokenString``). Both corpus appearances confirm this.
        - No style enum (currency / percent / scientific / spell-out) is
          present in either corpus appearance or in jellycore's
          ``parameter_keys`` list. Decimal-places is the only knob in scope
          for this schema. Note: Shortcuts.app's UI clearly exposes those
          style modes, so the gap likely reflects corpus-coverage
          limitations rather than a wire-format truth — a sample
          exercising a non-decimal style mode (or a sibling identifier
          like ``is.workflow.actions.format.measurement``) would resolve
          this. Pending such evidence, model only what's confirmed.
        - Jellycore parameter_keys: ``["WFNumber", "WFNumberFormatDecimalPlaces"]``.
    """

    identifier: ClassVar[str] = "is.workflow.actions.format.number"
    default_output_name: ClassVar[str] = "Formatted Number"

    number: ParamValue = field(default=None)
    decimal_places: int | None = field(default=None)

    def _params(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.number is not None:
            out["WFNumber"] = coerce_value(self.number)
        if self.decimal_places is not None:
            out["WFNumberFormatDecimalPlaces"] = self.decimal_places
        return out
