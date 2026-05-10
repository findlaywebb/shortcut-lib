"""Statistics — Get Statistic from a list of numbers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Literal, get_args

from shortcut_lib.schema.base import (
    Action,
    ParamValue,
    SchemaError,
    coerce_value,
)
from shortcut_lib.schema.registry import register

# Closed set of aggregate operations shown in Shortcuts.app's "Get Statistic
# of Numbers" action dropdown.
#
# Source confidence:
#
# * **Both corpus appearances omit the operation key**, confirming "Average"
#   is Apple's default but giving no evidence of the wire-key spelling for
#   non-default operations.
# * **Jellycore lists ``parameter_keys: ["Input", "operation"]``** (lowercase
#   ``operation``) for ``is.workflow.actions.statistics``. This implementation
#   currently emits ``WFStatisticsOperation`` (WF-prefixed). Given the
#   AppIntent-style pattern (the action uses bare ``Input`` rather than
#   ``WFInput``), the wire key may actually be lowercase ``operation`` to
#   match. Until a corpus sample exercises a non-default operation, the
#   wire-key spelling is **uncertain**; the schema may need to switch to
#   ``operation`` if a non-Average sample surfaces. Tests pin only the
#   default-omit behaviour, which is unambiguous.
# * **The 9 operation token strings below** ("Average", "Minimum", ...) are
#   Shortcuts.app UI labels. Jellycore does not enumerate values, only the
#   parameter name. They are the project's best inference; treat any
#   round-trip equivalence test that exercises a non-default operation as
#   speculative until corpus evidence arrives.
WFStatisticsOperation = Literal[
    "Average",
    "Minimum",
    "Maximum",
    "Sum",
    "Count",
    "Range",
    "Median",
    "Mode",
    "Standard Deviation",
]
_VALID_OPERATIONS: frozenset[str] = frozenset(get_args(WFStatisticsOperation))


@register
@dataclass
class Statistics(Action):
    """Compute an aggregate statistic from a list of numbers.

    Wraps ``is.workflow.actions.statistics`` — the "Get Statistic of Numbers"
    action in Shortcuts.app. Accepts a list of numbers (or any action whose
    output is a list of numbers) and returns a single numeric result.

    **Wire format (corpus-verified)**

    Both corpus appearances (``samples/decoded/dictionary.xml``, lines 26 and
    239) pass ``Input`` as ``WFTextTokenAttachment``, meaning a single-variable
    reference to the output of a preceding action. Neither appearance sets
    ``WFStatisticsOperation``, confirming "Average" is Apple's implicit default.
    This model uses :func:`~shortcut_lib.schema.base.coerce_value` (not
    ``coerce_text_field``) for ``Input`` because the slot carries
    ``WFTextTokenAttachment`` in the corpus, not ``WFTextTokenString``.

    **Source notes**

    - Corpus: 2 appearances in ``samples/decoded/dictionary.xml``.
    - Jellycore: **entry exists** with ``parameter_keys: ["Input",
      "operation"]`` (lowercase ``operation``). The branch currently
      emits ``WFStatisticsOperation`` — the disagreement is unresolved
      pending a non-default-operation corpus sample. See the module
      docstring's "Source confidence" block above.
    - ``observed_envelope_types.json`` entry: ``Input`` → ``WFTextTokenAttachment``
      (2 of 2 observations).

    **Supported operations**

    All nine operations available in Shortcuts.app are typed as
    :data:`WFStatisticsOperation`:

    - ``"Average"`` — arithmetic mean (default, omitted from wire format).
    - ``"Minimum"`` — smallest value in the list.
    - ``"Maximum"`` — largest value in the list.
    - ``"Sum"`` — total of all values.
    - ``"Count"`` — number of items.
    - ``"Range"`` — maximum minus minimum.
    - ``"Median"`` — middle value when sorted.
    - ``"Mode"`` — most frequently occurring value.
    - ``"Standard Deviation"`` — population standard deviation.

    **Usage examples**

    Compute the average of a variable list of numbers::

        from shortcut_lib.schema.actions.statistics import Statistics
        from shortcut_lib.schema.actions.get_variable import GetVariable

        numbers = GetVariable(variable="My Numbers")
        avg = Statistics(input=numbers)

    Compute the sum, chaining directly off a previous action's output::

        numbers = GetVariable(variable="My Numbers")
        total = Statistics(input=numbers, operation="Sum")

    Args:
        input: The list of numbers to aggregate. Typically the output of a
            prior action (e.g. ``GetVariable``, ``TextSplit``, or any action
            whose output is a list). Passed as ``WFTextTokenAttachment`` in
            the wire format. Defaults to ``None`` (no input configured).
        operation: One of the nine aggregate operations listed above.
            Defaults to ``"Average"``. Apple omits the key from the wire dict
            when the value is ``"Average"``; this model matches that behaviour.
    """

    identifier: ClassVar[str] = "is.workflow.actions.statistics"
    default_output_name: ClassVar[str] = "Statistic"

    input: ParamValue = None
    operation: WFStatisticsOperation = "Average"

    def __post_init__(self) -> None:
        if self.operation not in _VALID_OPERATIONS:
            raise SchemaError(
                f"Statistics.operation {self.operation!r} is not valid. "
                f"Expected one of: {sorted(_VALID_OPERATIONS)}"
            )

    def _params(self) -> dict[str, Any]:
        """Return the Input and WFStatisticsOperation parameter dict.

        NOTE: the wire-key spelling for the operation is unverified —
        jellycore lists ``operation`` (lowercase) but the corpus contains
        no non-default sample. See the module docstring's "Source
        confidence" block.

        Apple omits ``WFStatisticsOperation`` when the operation is "Average"
        (the default). Both corpus observations confirm this — neither sets
        the key. This model matches that emission to produce wire-identical
        output for the default case.
        """
        out: dict[str, Any] = {}
        if self.input is not None:
            # Input is WFTextTokenAttachment in both corpus observations.
            # coerce_value correctly emits WFTextTokenAttachment for an Action
            # argument (Output.to_param()). coerce_text_field is NOT used here
            # because the corpus slot is WFTextTokenAttachment, not
            # WFTextTokenString.
            out["Input"] = coerce_value(self.input)
        # "Average" is Apple's default and is omitted in the wire format.
        if self.operation != "Average":
            out["WFStatisticsOperation"] = self.operation
        return out
