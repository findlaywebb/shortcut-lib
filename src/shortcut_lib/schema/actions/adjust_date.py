"""AdjustDate — add or subtract a duration from a date, or snap to period.

Apple identifier: ``is.workflow.actions.adjustdate``

Wire-format evidence (2 corpus samples):

start_pomodoro.xml (Add with variable duration)::

    WFAdjustOperation   = "Add"        # bare string slot
    WFDate              = WFTextTokenString  # e.g. CurrentDate attachment
    WFDuration          = WFQuantityFieldValue{Magnitude, Unit}  # e.g. "min"
    WFAdjustOffsetPicker = WFTimeOffsetValue{Operation, Unit, Value}

dictionary.xml (date-only, no operation configured)::

    WFDate              = WFTextTokenString  # e.g. action-output attachment
    # WFAdjustOperation and WFDuration absent when operation is unset

Key observations:
- ``WFDate`` is always a WFTextTokenString slot (coerce_text_field).
- ``WFAdjustOperation`` is a bare string (not an envelope).
- ``WFDuration`` is a WFQuantityFieldValue envelope with Apple unit
  abbreviations: ``"sec"``, ``"min"``, ``"hour"``, ``"day"``, ``"week"``,
  ``"month"``, ``"year"``.
- ``WFAdjustOffsetPicker`` is a WFTimeOffsetValue envelope with a parallel
  *spelled-out* unit (``"Second"``, ``"Minute"``, ``"Hour"``, …) and the
  same value token.  Apple renders both when the user picks Add/Subtract.
- For operations "Get Start of Time Period" / "Get End of Time Period",
  no ``WFDuration`` or ``WFAdjustOffsetPicker`` is emitted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Literal, get_args

from shortcut_lib.schema.base import (
    Action,
    ParamValue,
    SchemaError,
    coerce_text_field,
    coerce_token,
)
from shortcut_lib.schema.registry import register

# ---------------------------------------------------------------------------
# Literal type aliases for closed-set parameters
# ---------------------------------------------------------------------------

WFAdjustOperation = Literal[
    "Add",
    "Subtract",
    "Get Start of Time Period",
    "Get End of Time Period",
]
"""Apple's four date-adjustment modes shown in the Shortcuts UI."""

WFTimeUnit = Literal["Second", "Minute", "Hour", "Day", "Week", "Month", "Year"]
"""Spelled-out time units used by WFTimeOffsetValue and WFAdjustOffsetPicker."""

_VALID_OPERATIONS: frozenset[str] = frozenset(get_args(WFAdjustOperation))
_VALID_UNITS: frozenset[str] = frozenset(get_args(WFTimeUnit))

# Map from the spelled-out WFTimeUnit to Apple's abbreviated WFQuantityFieldValue
# unit string, as observed in corpus samples.
_UNIT_TO_ABBREV: dict[str, str] = {
    "Second": "sec",
    "Minute": "min",
    "Hour": "hour",
    "Day": "day",
    "Week": "week",
    "Month": "month",
    "Year": "year",
}

# Operations that produce a duration-less wire format.
_PERIOD_OPERATIONS: frozenset[str] = frozenset(
    {"Get Start of Time Period", "Get End of Time Period"}
)


# ---------------------------------------------------------------------------
# Action
# ---------------------------------------------------------------------------


@register
@dataclass
class AdjustDate(Action):
    """Add/subtract a duration from a date, or snap it to a time-period boundary.

    Apple identifier: ``is.workflow.actions.adjustdate``

    Shortcuts UI label: *Adjust Date*

    This action takes a date (the *input*), applies a date-arithmetic operation,
    and outputs the adjusted date.  The four available operations cover the two
    arithmetic forms (Add, Subtract) and two period-rounding forms (Get Start /
    Get End of a time period such as "beginning of this week").

    Parameters
    ----------
    input:
        The date to adjust.  Accepts any ``ParamValue`` — most commonly an
        ``Action`` (e.g. :class:`~shortcut_lib.schema.actions.format_date.FormatDate`
        output), a :class:`~shortcut_lib.schema.values.MagicVar` (e.g.
        ``CurrentDate``), an :class:`~shortcut_lib.schema.values.Output`
        reference, or a :class:`~shortcut_lib.schema.values.Text` template.
        The slot is a ``WFTextTokenString`` on the wire (``coerce_text_field``
        wraps variable references automatically).  May be ``None`` to omit
        ``WFDate`` entirely (Shortcuts will prompt the user at run time).
    operation:
        The adjustment mode.  One of::

            "Add"                    # date + duration  (default)
            "Subtract"               # date - duration
            "Get Start of Time Period"  # snap to start of the unit period
            "Get End of Time Period"    # snap to end of the unit period

        For the period forms, ``magnitude`` and ``unit`` are irrelevant — no
        ``WFDuration`` or ``WFAdjustOffsetPicker`` is emitted.
    magnitude:
        How much to add or subtract.  Pass a plain ``int`` / ``float``, or any
        ``ParamValue`` that resolves to a number (e.g. an action output from
        ``Round Number``).  Ignored when ``operation`` is one of the period
        forms.  Must be provided when ``operation`` is "Add" or "Subtract".
    unit:
        The time unit for the magnitude.  One of::

            "Second" | "Minute" | "Hour"   (default: "Hour")
            "Day"    | "Week"   | "Month"  | "Year"

        Ignored when ``operation`` is one of the period forms.

    Wire format (Add/Subtract)
    --------------------------
    The emitted ``WFWorkflowActionParameters`` dict contains three keys in
    addition to the mandatory ``UUID``::

        WFAdjustOperation    = "Add"                  # bare string
        WFDate               = <WFTextTokenString>    # date slot
        WFDuration           = {                      # primary duration picker
            "Value": {"Magnitude": <token | scalar>, "Unit": "min"},
            "WFSerializationType": "WFQuantityFieldValue"
        }
        WFAdjustOffsetPicker = {                      # mirrored offset picker
            "Value": {
                "Operation": "Add",
                "Unit": "Minute",                    # spelled-out unit
                "Value": <same token | scalar>
            },
            "WFSerializationType": "WFTimeOffsetValue"
        }

    Wire format (Get Start / Get End of Time Period)
    ------------------------------------------------
    Only ``WFDate`` and ``WFAdjustOperation`` are emitted.  No
    ``WFDuration`` or ``WFAdjustOffsetPicker``.

    Corpus evidence
    ---------------
    *samples/decoded/start_pomodoro.xml* — Add with a variable magnitude
    (``Rounded Number`` action output) in minutes, applied to ``CurrentDate``::

        WFAdjustOperation   = "Add"
        WFDate              = WFTextTokenString wrapping CurrentDate token
        WFDuration.Unit     = "min"
        WFAdjustOffsetPicker.Unit = "Minute"
        WFAdjustOffsetPicker.Value = ActionOutput{OutputName: "Rounded Number"}

    *samples/decoded/dictionary.xml* — Minimal form (operation not configured
    in the demo shortcut): only ``WFDate`` is present.  Confirms that
    ``WFAdjustOperation``, ``WFDuration``, and ``WFAdjustOffsetPicker`` are all
    omitted when the user hasn't picked a mode.

    Examples
    --------
    Add 25 minutes to the current date::

        from shortcut_lib.schema.actions.adjust_date import AdjustDate
        from shortcut_lib.schema.values import CurrentDate

        adj = AdjustDate(input=CurrentDate, operation="Add",
                         magnitude=25, unit="Minute")

    Add a variable number of minutes (from a previous action)::

        ask = AskForInput(prompt="How many minutes?", input_type="Number")
        adj = AdjustDate(input=CurrentDate, operation="Add",
                         magnitude=ask, unit="Minute")

    Subtract 1 week::

        adj = AdjustDate(input=CurrentDate, operation="Subtract",
                         magnitude=1, unit="Week")

    Snap to start of the current day::

        adj = AdjustDate(input=CurrentDate,
                         operation="Get Start of Time Period", unit="Day")
    """

    identifier: ClassVar[str] = "is.workflow.actions.adjustdate"
    default_output_name: ClassVar[str] = "Adjusted Date"

    input: ParamValue = None
    operation: WFAdjustOperation = field(default="Add")
    magnitude: ParamValue = None
    unit: WFTimeUnit = field(default="Hour")

    def __post_init__(self) -> None:
        if self.operation not in _VALID_OPERATIONS:
            raise SchemaError(
                f"operation {self.operation!r} is not valid. "
                f"Expected one of: {sorted(_VALID_OPERATIONS)}"
            )
        if self.unit not in _VALID_UNITS:
            raise SchemaError(
                f"unit {self.unit!r} is not valid. "
                f"Expected one of: {sorted(_VALID_UNITS)}"
            )
        if self.operation not in _PERIOD_OPERATIONS and self.magnitude is None:
            raise SchemaError(
                f"magnitude must be set when operation is {self.operation!r}. "
                f"Pass an int, float, or an Action/Output/NamedVar that resolves "
                f"to a number."
            )

    def _params(self) -> dict[str, Any]:
        out: dict[str, Any] = {}

        if self.input is not None:
            out["WFDate"] = coerce_text_field(self.input)

        # Emit operation as bare string (confirmed bare_string_slot in corpus).
        out["WFAdjustOperation"] = self.operation

        if self.operation not in _PERIOD_OPERATIONS:
            abbrev = _UNIT_TO_ABBREV[self.unit]

            # WFDuration: WFQuantityFieldValue with abbreviated unit
            if isinstance(self.magnitude, int | float):
                mag_value: Any = self.magnitude
                mag_token: Any = self.magnitude
            else:
                # Variable reference — coerce to token for both slots
                mag_token = coerce_token(self.magnitude)  # type: ignore[arg-type]
                mag_value = mag_token

            out["WFDuration"] = {
                "Value": {"Magnitude": mag_value, "Unit": abbrev},
                "WFSerializationType": "WFQuantityFieldValue",
            }

            # WFAdjustOffsetPicker: WFTimeOffsetValue with spelled-out unit
            out["WFAdjustOffsetPicker"] = {
                "Value": {
                    "Operation": self.operation,
                    "Unit": self.unit,
                    "Value": mag_token,
                },
                "WFSerializationType": "WFTimeOffsetValue",
            }

        return out
