"""RoundNumber — round a number to the given precision and mode."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Literal, get_args

from shortcut_lib.schema.base import Action, ParamValue, SchemaError, coerce_value
from shortcut_lib.schema.registry import register

# Closed set of rounding modes shown in Shortcuts.app's Round Number action.
# Confirmed against corpus: "Always Round Up" in start_pomodoro.xml:45.
# Remaining values inferred from Apple's documented Shortcuts action surface.
WFRoundMode = Literal[
    "Normal",
    "Always Round Up",
    "Always Round Down",
]
_VALID_ROUND_MODES: frozenset[str] = frozenset(get_args(WFRoundMode))

# Closed set of rounding places shown in Shortcuts.app's Round Number action.
# Not observed in the three corpus samples (both dictionary.xml appearances
# omit WFRoundTo entirely, implying "Ones Place" is the wire-format default).
# Values sourced from Apple's documented Shortcuts action surface (jellycore
# parameter key: ``roundTo``).
WFRoundPlace = Literal[
    "Ones Place",
    "Tens Place",
    "Hundreds Place",
    "Thousands",
    "Ten Thousands",
    "Hundred Thousands",
    "Millions",
    "Tenths",
    "Hundredths",
    "Thousandths",
    "Millionths",
]
_VALID_ROUND_PLACES: frozenset[str] = frozenset(get_args(WFRoundPlace))


@register
@dataclass
class RoundNumber(Action):
    """Round a number to a given precision using the specified rounding mode.

    Args:
        input: Number to round. Pass an Action to chain off its output,
            a literal number, or any Value. Corresponds to ``WFInput``
            (WFTextTokenAttachment). When omitted the key is excluded.
        mode: Rounding mode — one of "Normal", "Always Round Up",
            "Always Round Down". Defaults to "Normal". Apple omits
            ``WFRoundMode`` from the wire format when it is "Normal"
            (confirmed: two of three corpus samples carry no ``WFRoundMode``
            and exhibit default / "Normal" behaviour at runtime).
        place: Decimal place to round to. One of the ``WFRoundPlace``
            literals (e.g. "Ones Place", "Tenths", "Hundreds Place").
            Defaults to "Ones Place". Apple omits ``WFRoundTo`` from the
            wire format when the default is in effect; all three corpus
            samples carry no ``WFRoundTo`` key.
    """

    identifier: ClassVar[str] = "is.workflow.actions.round"
    default_output_name: ClassVar[str] = "Rounded Number"

    input: ParamValue = None
    mode: WFRoundMode = "Normal"
    place: WFRoundPlace = "Ones Place"

    def __post_init__(self) -> None:
        if self.mode not in _VALID_ROUND_MODES:
            raise SchemaError(
                f"RoundNumber.mode {self.mode!r} is not valid. "
                f"Expected one of: {sorted(_VALID_ROUND_MODES)}"
            )
        if self.place not in _VALID_ROUND_PLACES:
            raise SchemaError(
                f"RoundNumber.place {self.place!r} is not valid. "
                f"Expected one of: {sorted(_VALID_ROUND_PLACES)}"
            )

    def _params(self) -> dict[str, Any]:
        """Emit WFInput, and conditionally WFRoundMode and WFRoundTo.

        Apple omits WFRoundMode when "Normal" and WFRoundTo when "Ones
        Place"; this matches the wire format in all three corpus samples
        (dictionary.xml:304, dictionary.xml:4582 carry neither key;
        start_pomodoro.xml:45 carries only WFRoundMode="Always Round Up").
        """
        out: dict[str, Any] = {}
        if self.input is not None:
            out["WFInput"] = coerce_value(self.input)
        if self.mode != "Normal":
            out["WFRoundMode"] = self.mode
        if self.place != "Ones Place":
            out["WFRoundTo"] = self.place
        return out
