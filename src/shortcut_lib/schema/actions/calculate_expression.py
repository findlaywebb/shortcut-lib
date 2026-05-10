"""CalculateExpression — evaluate a text expression like ``"5 + 3 * 2"``."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action, ParamValue, SchemaError, coerce_text_field
from shortcut_lib.schema.registry import register


@register
@dataclass
class CalculateExpression(Action):
    """Evaluate a free-form text expression and return the numeric result.

    Apple identifier: ``is.workflow.actions.calculateexpression``.

    This action is Shortcuts' **string-expression calculator**: it receives an
    arbitrary text string — which may contain variable interpolations — parses
    it as a mathematical expression, and returns the computed value.

    It is **distinct from** :class:`~shortcut_lib.schema.actions.math.Math`
    (``is.workflow.actions.math``), which is a *structured* calculator that
    takes two discrete numeric operands and a drop-down operator.  The two
    actions are complementary:

    - Use ``Math`` when both operands are known at authoring time and the
      operation is a simple binary/scientific function.
    - Use ``CalculateExpression`` when you need to evaluate a dynamically
      constructed expression string, e.g. one assembled by preceding Text
      or Set-Variable actions.

    **Wire format** (``WFWorkflowActionParameters``)::

        {
            "Input": {
                "Value": {
                    "string": "￼",
                    "attachmentsByRange": {
                        "{0, 1}": {
                            "OutputName": "Calculation Result",
                            "OutputUUID": "<uuid>",
                            "Type": "ActionOutput"
                        }
                    }
                },
                "WFSerializationType": "WFTextTokenString"
            },
            "UUID": "<action-uuid>"
        }

    The ``Input`` slot uses a ``WFTextTokenString`` envelope — even when the
    expression is a single variable reference.  This differs from ``Math``'s
    ``WFInput`` slot, which uses the ``WFTextTokenAttachment`` envelope for
    direct variable references.  :func:`~shortcut_lib.schema.base.coerce_text_field`
    handles the wrapping automatically.

    **Source notes**:

    - Corpus evidence: ``samples/decoded/dictionary.xml`` lines 396-424 and
      4464-4492 (two appearances, both with a variable-interpolated expression).
    - ``data/jellycore_facts.json``: jellycore lists
      ``parameter_keys: ["Input"]`` for this identifier (verify with
      ``jq '.actions[] | select(.identifier == "is.workflow.actions.calculateexpression")' data/jellycore_facts.json``).
      Jellycore corroborates the bare ``Input`` wire key (matching the
      AppIntent convention) — both jellycore and corpus agree.
    - Output name ``"Calculation Result"`` confirmed from both corpus
      appearances (``OutputName`` inside each ``attachmentsByRange`` dict).

    Args:
        expression: The text expression to evaluate.  Pass a plain string
            (e.g. ``"5 + 3 * 2"``), an :class:`~shortcut_lib.schema.base.Action`
            whose output is an expression string, or any
            :class:`~shortcut_lib.schema.base.Value`.

            Wire key: ``Input``.  Serialised as a ``WFTextTokenString``
            envelope; variable references are wrapped as single-attachment
            templated strings (see :func:`~shortcut_lib.schema.base.coerce_text_field`).

            Defaults to ``None`` (raises :class:`~shortcut_lib.schema.base.SchemaError`
            at build time if omitted).

    Returns:
        The result of evaluating the expression. Apple labels this output
        ``"Calculation Result"`` in the variable picker.

    Raises:
        :class:`~shortcut_lib.schema.base.SchemaError`: if ``expression`` is
            ``None`` when the action is built.

    Examples::

        from shortcut_lib.schema.actions.calculate_expression import (
            CalculateExpression,
        )
        from shortcut_lib import NamedVar

        # Plain literal expression
        calc = CalculateExpression(expression="5 + 3 * 2")

        # Expression held in a named variable (WFTextTokenString envelope)
        expr_var = NamedVar("My Expression")
        calc = CalculateExpression(expression=expr_var)

        # Chain: feed a previous action's text output as the expression
        from shortcut_lib.schema.actions.get_text import GetText
        text_action = GetText(text="10 / 2")
        calc = CalculateExpression(expression=text_action)

    Note:
        The expression syntax accepted at runtime is iOS's built-in expression
        parser (the same engine used in the Shortcuts formula field).  It
        supports the four arithmetic operators, parentheses, and standard
        operator precedence.  The exact set of supported functions is not
        documented by Apple.
    """

    identifier: ClassVar[str] = "is.workflow.actions.calculateexpression"
    default_output_name: ClassVar[str] = "Calculation Result"

    expression: ParamValue = None

    def _params(self) -> dict[str, Any]:
        if self.expression is None:
            raise SchemaError("CalculateExpression requires `expression`")
        return {
            # ``Input`` is the corpus-confirmed wire key (capitalised,
            # AppIntent style). Distinct from Math's ``WFInput``.
            "Input": coerce_text_field(self.expression),
        }
