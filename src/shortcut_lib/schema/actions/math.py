"""Math — perform arithmetic or scientific calculation on numbers.

Apple identifier: ``is.workflow.actions.math``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Literal, get_args

from shortcut_lib.schema.base import Action, ParamValue, SchemaError, coerce_value
from shortcut_lib.schema.registry import register

# ---------------------------------------------------------------------------
# Operation type aliases
# ---------------------------------------------------------------------------

# Basic arithmetic operations shown in Shortcuts.app's Math action.
# Wire-format strings confirmed from Apple's plist encoding. The corpus
# (dictionary.xml:373 and dictionary.xml:4455) contains two appearances of
# this action; both omit WFMathOperation entirely, confirming "+" as default.
#
# Note: Apple uses Unicode math symbols for three of the five operators.
# The exact codepoints are embedded in the Literal below.
WFMathOperation = Literal[
    "+",  # addition — ASCII plus, wire-format default
    "−",  # subtraction — MINUS SIGN (U+2212), not ASCII hyphen
    "×",  # multiplication — MULTIPLICATION SIGN (U+00D7)
    "÷",  # division — DIVISION SIGN (U+00F7)
    "Modulo",  # remainder after integer division
]

# Scientific / unary operations (``scientific`` parameter key).
# These apply a single-operand function to WFInput; WFMathOperand is not
# used when a scientific operation is active (except for "x^y", where it
# supplies the exponent).
#
# Source confidence:
#   * The ``scientific`` parameter KEY is confirmed by jellycore
#     (data/jellycore_facts.json — parameter_keys for
#     is.workflow.actions.math: ["WFInput", "WFMathOperation",
#     "WFMathOperand", "scientific"]).
#   * The 13 operation TOKEN STRINGS below (e.g. "√", "sin(x)",
#     "x^y") and the rule that "x^y" still consumes WFMathOperand as
#     the exponent are inferred from Apple's Shortcuts.app UI labels
#     (iOS 17 / macOS 14); no decoded corpus sample exercises any
#     scientific operation, so the exact wire encoding of each token
#     is pending a fresh sample.
# Use the exact codepoints below; do not substitute ASCII
# approximations.
WFScientificOperation = Literal[
    "√",  # square root — U+221A SQUARE ROOT
    "x^2",  # square
    "x^3",  # cube
    "x^y",  # arbitrary power; WFMathOperand is the exponent y
    "e^x",  # natural exponential
    "10^x",  # base-10 exponential
    "ln(x)",  # natural logarithm
    "log(x)",  # base-10 logarithm
    "sin(x)",  # sine, degrees
    "cos(x)",  # cosine, degrees
    "tan(x)",  # tangent, degrees
    "abs(x)",  # absolute value
    "∛",  # cube root — U+221B CUBE ROOT
]

_VALID_OPERATIONS: frozenset[str] = frozenset(get_args(WFMathOperation))
_VALID_SCIENTIFIC: frozenset[str] = frozenset(get_args(WFScientificOperation))

# Scientific ops that still consume a second operand: WFMathOperand carries
# the exponent for x^y.
_SCIENTIFIC_WITH_OPERAND: frozenset[str] = frozenset({"x^y"})

# Convenience references to the Apple Unicode operator characters. These
# match the wire-format strings above and are used by the examples below.
_SUBTRACT = "−"  # MINUS SIGN
_MULTIPLY = "×"  # MULTIPLICATION SIGN
_DIVIDE = "÷"  # DIVISION SIGN
_SQRT = "√"  # SQUARE ROOT
_CBRT = "∛"  # CUBE ROOT


@register
@dataclass
class Math(Action):
    """Perform arithmetic or scientific calculation on one or two numbers.

    The **Math** action (``is.workflow.actions.math``) is Shortcuts' primary
    numeric calculator.  It operates in two modes:

    **Arithmetic mode** -- binary operations on two operands::

        result = WFInput  <operation>  WFMathOperand

    Supported operations (``operation`` argument):

    +-----------+------+-------------------------------------------------------+
    | Token     | UI   | Notes                                                 |
    +===========+======+=======================================================+
    | ``"+"``   |  +   | Addition; Apple omits the key when default.           |
    +-----------+------+-------------------------------------------------------+
    | U+2212    |  -   | Subtraction (MINUS SIGN, not ASCII hyphen).           |
    +-----------+------+-------------------------------------------------------+
    | U+00D7    |  x   | Multiplication (MULTIPLICATION SIGN).                 |
    +-----------+------+-------------------------------------------------------+
    | U+00F7    |  /   | Division (DIVISION SIGN).                             |
    +-----------+------+-------------------------------------------------------+
    | Modulo    |  %   | Remainder after integer division.                     |
    +-----------+------+-------------------------------------------------------+

    The three non-ASCII operators must be passed as their Unicode codepoints.
    Import the convenience constants from this module, or use the escape
    sequences directly::

        from shortcut_lib.schema.actions.math import Math, _SUBTRACT, _MULTIPLY

        Math(operation=_SUBTRACT, operand=5)     # subtract 5
        Math(operation="×", operand=3)      # multiply by 3

    **Scientific mode** -- unary (or exponent) functions on ``WFInput``::

        result = f(WFInput)              # most scientific ops
        result = WFInput ^ WFMathOperand # x^y only

    Activate by setting ``scientific_operation`` to one of the
    ``WFScientificOperation`` literals, e.g. ``"√"`` for square root
    or ``"sin(x)"`` for sine.  The library emits the ``scientific``
    parameter key and suppresses ``WFMathOperation``.  For ``"x^y"``
    the ``operand`` is emitted as the exponent.

    *Note on scientific mode:* the ``scientific`` parameter key is
    jellycore-confirmed; the 13 operation token strings and the rule
    that ``x^y`` consumes ``WFMathOperand`` are inferred from Apple's
    UI and are pending a corpus sample. See the module docstring's
    "Source confidence" block.

    **Corpus evidence** (``samples/decoded/dictionary.xml``):

    - Line 373 -- first input operand bound to the ``Numbers`` output of a
      preceding action via ``WFTextTokenAttachment``; no ``WFMathOperation``
      or ``WFMathOperand`` emitted (defaults: addition, no explicit operand).
    - Line 4455 -- bare action with only a ``UUID`` key; again all-default.

    Both appearances confirm that ``"+"`` is the wire-format default and that
    Shortcuts.app omits ``WFMathOperation`` when the default is in effect
    (mirroring the omit-if-default convention used by ``RoundNumber`` and
    ``FormatDate``).

    **Minimum host**: not corpus-confirmed; the action is present in
    iOS 13+ Shortcuts catalogues but the exact lowest compatible host
    is not asserted here pending a confirmed source.

    Args:
        input: First operand.  Pass an :class:`~shortcut_lib.schema.base.Action`
            to chain off a previous step's output, a literal number (``int``
            or ``float``), or any :class:`~shortcut_lib.schema.base.Value`.
            Corresponds to the ``WFInput`` parameter key; encoded as
            ``WFTextTokenAttachment`` when an action output or variable is
            provided.  Defaults to ``None`` (key omitted).
        operation: Arithmetic operator applied in binary mode.  One of the
            ``WFMathOperation`` literals.  Defaults to ``"+"`` (addition).
            Apple omits this key when the value is ``"+"``; the library
            matches that behaviour.  Ignored when ``scientific_operation``
            is set.
        operand: Second operand (right-hand side).  Accepts the same types
            as ``input``.  Corresponds to ``WFMathOperand``.  Also used as
            the exponent when ``scientific_operation`` is ``"x^y"``.
            Omitted when ``None``.
        scientific_operation: When set, activates scientific / unary mode.
            One of the ``WFScientificOperation`` literals — e.g.
            ``"√"`` (square root, U+221A), ``"sin(x)"``,
            ``"log(x)"``; or ``"x^y"`` for arbitrary power.  The library
            emits the ``scientific`` parameter key and suppresses
            ``WFMathOperation``.  Defaults to ``None`` (arithmetic mode).

    Raises:
        :class:`~shortcut_lib.schema.base.SchemaError`: if ``operation`` is
            not a recognised arithmetic symbol, or if ``scientific_operation``
            is not a recognised function name.

    Examples::

        from shortcut_lib.schema.actions.math import Math, _SUBTRACT

        # Add 5 to a previous action's output (default "+" operation)
        result = Math(input=prev_action, operand=5)

        # Divide by 100 using the Unicode division sign (U+00F7)
        ratio = Math(input=prev_action, operation="÷", operand=100)

        # Square root in scientific mode (U+221A)
        sqrt_val = Math(input=prev_action, scientific_operation="√")

        # Raise to an arbitrary power (x^y; operand is the exponent)
        cubed = Math(input=prev_action, scientific_operation="x^y", operand=3)

        # Subtract using the MINUS SIGN constant
        diff = Math(
            input=prev_action.output(),
            operation=_SUBTRACT,
            operand=other_action.output(),
        )
    """

    identifier: ClassVar[str] = "is.workflow.actions.math"
    default_output_name: ClassVar[str] = "Calculation Result"

    input: ParamValue = None
    operation: WFMathOperation = field(default="+")
    operand: ParamValue = None
    scientific_operation: WFScientificOperation | None = field(default=None)

    def __post_init__(self) -> None:
        if self.operation not in _VALID_OPERATIONS:
            raise SchemaError(
                f"Math.operation {self.operation!r} is not valid. "
                f"Expected one of: {sorted(_VALID_OPERATIONS)}"
            )
        if (
            self.scientific_operation is not None
            and self.scientific_operation not in _VALID_SCIENTIFIC
        ):
            raise SchemaError(
                f"Math.scientific_operation {self.scientific_operation!r} "
                f"is not valid. "
                f"Expected one of: {sorted(_VALID_SCIENTIFIC)}"
            )

    def _params(self) -> dict[str, Any]:
        """Emit WFInput, WFMathOperation, WFMathOperand, or scientific key.

        Omission rules (matching Apple's wire format):
        - WFInput omitted when ``input`` is None.
        - WFMathOperation omitted when arithmetic mode and operation is "+"
          (confirmed: both corpus appearances carry no WFMathOperation).
        - WFMathOperand omitted when ``operand`` is None.
        - In scientific mode: ``scientific`` key emitted, WFMathOperation
          suppressed; WFMathOperand only emitted for ``"x^y"``.
        """
        out: dict[str, Any] = {}

        if self.input is not None:
            out["WFInput"] = coerce_value(self.input)

        if self.scientific_operation is not None:
            # Scientific / unary mode -- emit the ``scientific`` key.
            out["scientific"] = self.scientific_operation
            # Only x^y uses the second operand as the exponent.
            if (
                self.scientific_operation in _SCIENTIFIC_WITH_OPERAND
                and self.operand is not None
            ):
                out["WFMathOperand"] = coerce_value(self.operand)
        else:
            # Arithmetic (binary) mode.
            # Apple omits WFMathOperation for the default "+".
            if self.operation != "+":
                out["WFMathOperation"] = self.operation
            if self.operand is not None:
                out["WFMathOperand"] = coerce_value(self.operand)

        return out
