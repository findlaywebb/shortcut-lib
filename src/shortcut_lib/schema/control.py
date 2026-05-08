"""Control-flow constructs.

In the wire format these are flat — paired open/close marker actions
share a ``GroupingIdentifier`` and the body actions sit linearly between
them. In the DSL they're nested, then flattened on emit.

Functional API rather than context managers: ``If(cond, then=[...],
otherwise=[...])`` is friendlier for LLM authoring (no statefulness, no
indentation tracking).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, ClassVar

from shortcut_lib.schema.base import (
    Action,
    SchemaError,
    coerce_token,
    coerce_value,
    fresh_uuid,
)


class WFCondition(IntEnum):
    """Apple's ``WFCondition`` integer enum — observed values, may be incomplete.

    See ``docs/format.md`` "Open questions". The string aliases below
    (``CONDITION_CODES`` keys) are the LLM-facing names accepted by
    :class:`If`; the enum members are the wire-format integers.
    """

    EQ = 0
    LT = 1
    GT = 2
    LE = 3
    GE = 4
    BEGINS_WITH = 100
    ENDS_WITH = 101
    CONTAINS = 102
    IS_TRUE = 999
    IS_NOT_TRUE = 1000
    EXISTS = 1001
    DOES_NOT_EXIST = 1002


# String aliases accepted by ``If(op=...)``. Mapped to the integer enum.
CONDITION_CODES: dict[str, int] = {
    "==": WFCondition.EQ,
    "<": WFCondition.LT,
    ">": WFCondition.GT,
    "<=": WFCondition.LE,
    ">=": WFCondition.GE,
    "begins-with": WFCondition.BEGINS_WITH,
    "ends-with": WFCondition.ENDS_WITH,
    "contains": WFCondition.CONTAINS,
    "is-true": WFCondition.IS_TRUE,
    "is-not-true": WFCondition.IS_NOT_TRUE,
    "exists": WFCondition.EXISTS,
    "does-not-exist": WFCondition.DOES_NOT_EXIST,
}

# Reverse map for decode/summary use — int → string alias. Generated from
# ``CONDITION_CODES`` so the two never drift.
CONDITION_NAMES: dict[int, str] = {int(v): k for k, v in CONDITION_CODES.items()}


class _ControlAction(Action):
    """Marker for control-flow constructs (multi-action emit)."""

    identifier: ClassVar[str] = ""

    def _params(self) -> dict[str, Any]:  # pragma: no cover — overridden
        raise NotImplementedError

    def to_action_dict(self) -> dict[str, Any]:
        raise SchemaError(
            "Control-flow constructs emit multiple actions; use to_actions()"
        )


@dataclass
class If(_ControlAction):
    """Conditional branching.

    Args:
        operand: The value being tested. Coerced via ``coerce_token``.
        op: Comparison operator — either a :class:`WFCondition` enum
            member or one of the ``CONDITION_CODES`` string aliases
            (e.g. ``"=="``, ``"<"``, ``"contains"``, ``"is-true"``).
        value: The right-hand side of the comparison. Strings go to
            ``WFConditionalActionString``, numbers to ``WFNumberValue``.
        then: List of Actions executed when the condition is true.
        otherwise: List of Actions executed when false. Optional.
    """

    operand: Any = None
    op: str | WFCondition = "=="
    value: Any = None
    then: list[Any] = field(default_factory=list)
    otherwise: list[Any] = field(default_factory=list)
    grouping_identifier: str = field(default_factory=fresh_uuid)

    identifier: ClassVar[str] = "is.workflow.actions.conditional"

    def _params(self) -> dict[str, Any]:
        raise NotImplementedError  # multi-action

    def to_actions(self) -> list[dict[str, Any]]:
        if isinstance(self.op, WFCondition):
            op_code = int(self.op)
        elif self.op in CONDITION_CODES:
            op_code = CONDITION_CODES[self.op]
        else:
            raise SchemaError(
                f"unknown condition op {self.op!r} — pass a WFCondition enum "
                f"member or one of {sorted(CONDITION_CODES)}"
            )

        head_params: dict[str, Any] = {
            "GroupingIdentifier": self.grouping_identifier,
            "WFCondition": op_code,
            "WFControlFlowMode": 0,
            "WFInput": _wrap_variable_input(self.operand),
        }
        if self.value is not None:
            head_params.update(_condition_rhs(self.value, self.op))

        out: list[dict[str, Any]] = [
            {
                "WFWorkflowActionIdentifier": self.identifier,
                "WFWorkflowActionParameters": {**head_params, "UUID": self.uuid},
            }
        ]
        out.extend(_emit_body(self.then))

        if self.otherwise:
            out.append(
                {
                    "WFWorkflowActionIdentifier": self.identifier,
                    "WFWorkflowActionParameters": {
                        "GroupingIdentifier": self.grouping_identifier,
                        "UUID": fresh_uuid(),
                        "WFControlFlowMode": 1,
                    },
                }
            )
            out.extend(_emit_body(self.otherwise))

        out.append(
            {
                "WFWorkflowActionIdentifier": self.identifier,
                "WFWorkflowActionParameters": {
                    "GroupingIdentifier": self.grouping_identifier,
                    "UUID": fresh_uuid(),
                    "WFControlFlowMode": 2,
                },
            }
        )
        return out


@dataclass
class RepeatCount(_ControlAction):
    """Repeat the body ``count`` times. ``RepeatIndex`` magic var is in scope."""

    count: Any = 1
    body: list[Any] = field(default_factory=list)
    grouping_identifier: str = field(default_factory=fresh_uuid)

    identifier: ClassVar[str] = "is.workflow.actions.repeat.count"

    def _params(self) -> dict[str, Any]:
        raise NotImplementedError

    def to_actions(self) -> list[dict[str, Any]]:
        head: dict[str, Any] = {
            "GroupingIdentifier": self.grouping_identifier,
            "UUID": self.uuid,
            "WFControlFlowMode": 0,
            "WFRepeatCount": (
                self.count
                if isinstance(self.count, int | float)
                else coerce_token(self.count)
            ),
        }
        return _close_grouping(
            self.identifier, head, self.body, self.grouping_identifier
        )


@dataclass
class RepeatEach(_ControlAction):
    """Iterate over a list; ``RepeatItem`` magic var is the current element."""

    items: Any = None
    body: list[Any] = field(default_factory=list)
    grouping_identifier: str = field(default_factory=fresh_uuid)

    identifier: ClassVar[str] = "is.workflow.actions.repeat.each"

    def _params(self) -> dict[str, Any]:
        raise NotImplementedError

    def to_actions(self) -> list[dict[str, Any]]:
        if self.items is None:
            raise SchemaError(
                "RepeatEach requires `items` (a list-typed Output or value)"
            )
        head: dict[str, Any] = {
            "GroupingIdentifier": self.grouping_identifier,
            "UUID": self.uuid,
            "WFControlFlowMode": 0,
            "WFInput": _wrap_variable_input(self.items),
        }
        return _close_grouping(
            self.identifier, head, self.body, self.grouping_identifier
        )


@dataclass
class ChooseFromMenu(_ControlAction):
    """Present a menu; each ``case`` runs its body when selected.

    ``cases`` is a list of ``(label, [actions])`` tuples. Apple emits a
    head action, then a separate "case" marker action per option (mode=1)
    interspersed with the option bodies, then a tail close (mode=2).
    """

    prompt: Any = ""
    cases: list[tuple[str, list[Any]]] = field(default_factory=list)
    grouping_identifier: str = field(default_factory=fresh_uuid)

    identifier: ClassVar[str] = "is.workflow.actions.choosefrommenu"

    def _params(self) -> dict[str, Any]:
        raise NotImplementedError

    def to_actions(self) -> list[dict[str, Any]]:
        if not self.cases:
            raise SchemaError("ChooseFromMenu needs at least one case")
        labels = [label for label, _ in self.cases]
        head_params: dict[str, Any] = {
            "GroupingIdentifier": self.grouping_identifier,
            "UUID": self.uuid,
            "WFControlFlowMode": 0,
            "WFMenuItems": labels,
        }
        if self.prompt:
            head_params["WFMenuPrompt"] = (
                self.prompt
                if isinstance(self.prompt, str)
                else coerce_value(self.prompt)
            )
        out: list[dict[str, Any]] = [
            {
                "WFWorkflowActionIdentifier": self.identifier,
                "WFWorkflowActionParameters": head_params,
            }
        ]
        for label, body in self.cases:
            out.append(
                {
                    "WFWorkflowActionIdentifier": self.identifier,
                    "WFWorkflowActionParameters": {
                        "GroupingIdentifier": self.grouping_identifier,
                        "UUID": fresh_uuid(),
                        "WFControlFlowMode": 1,
                        "WFMenuItemTitle": label,
                    },
                }
            )
            out.extend(_emit_body(body))
        out.append(
            {
                "WFWorkflowActionIdentifier": self.identifier,
                "WFWorkflowActionParameters": {
                    "GroupingIdentifier": self.grouping_identifier,
                    "UUID": fresh_uuid(),
                    "WFControlFlowMode": 2,
                },
            }
        )
        return out


def _emit_body(body: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in body:
        if not isinstance(item, Action):
            raise SchemaError(
                f"control-flow body items must be Actions; got {type(item).__name__}"
            )
        out.extend(item.to_actions())
    return out


def _close_grouping(
    identifier: str,
    head: dict[str, Any],
    body: list[Any],
    grouping_id: str,
) -> list[dict[str, Any]]:
    # Only valid for simple open → body → close constructs (RepeatCount,
    # RepeatEach). If and ChooseFromMenu have interleaved markers (an else
    # mid-section, per-case markers) and emit their own three-action layout.
    out: list[dict[str, Any]] = [
        {
            "WFWorkflowActionIdentifier": identifier,
            "WFWorkflowActionParameters": head,
        }
    ]
    out.extend(_emit_body(body))
    out.append(
        {
            "WFWorkflowActionIdentifier": identifier,
            "WFWorkflowActionParameters": {
                "GroupingIdentifier": grouping_id,
                "UUID": fresh_uuid(),
                "WFControlFlowMode": 2,
            },
        }
    )
    return out


def _wrap_variable_input(operand: Any) -> dict[str, Any]:
    """Wrap an operand as the ``{Type: Variable, Variable: <token>}`` envelope.

    `if`, `for-each`, and similar control-flow heads expect the input in
    this two-layer form rather than the plain WFTextTokenAttachment shape.
    """
    if operand is None:
        raise SchemaError("control-flow input operand is required")
    return {"Type": "Variable", "Variable": coerce_value(operand)}


_VALUELESS_OPS: frozenset[str | WFCondition] = frozenset(
    {
        "is-true",
        "is-not-true",
        "exists",
        "does-not-exist",
        WFCondition.IS_TRUE,
        WFCondition.IS_NOT_TRUE,
        WFCondition.EXISTS,
        WFCondition.DOES_NOT_EXIST,
    }
)


def _condition_rhs(value: Any, op: str | WFCondition) -> dict[str, Any]:
    """Map a condition right-hand side to the right WF* parameter key.

    Some operators ("is-true", "is-not-true", "exists", "does-not-exist")
    take no RHS — calling code passes ``value=None`` for those, so this
    function never sees them in practice. We still guard the bool case
    against the wrong operator to catch caller mistakes early.
    """
    # bool is a subclass of int, so this branch must come before int|float.
    if isinstance(value, bool):
        if op not in _VALUELESS_OPS:
            raise SchemaError(
                f"If(value={value!r}) is a boolean, only valid for valueless "
                f"operators (string aliases: is-true, is-not-true, exists, "
                f"does-not-exist; or the matching WFCondition members). For "
                f"comparing against a string 'true'/'false', wrap it: "
                f"value='true'."
            )
        return {}
    if isinstance(value, int | float):
        return {"WFNumberValue": str(value)}
    if isinstance(value, str):
        return {"WFConditionalActionString": value}
    # Variable / Output / Text on the RHS
    return {"WFConditionalActionString": coerce_value(value)}
