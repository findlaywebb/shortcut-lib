"""Composition: shortcuts calling other shortcuts via Run Workflow.

Helper shortcuts work like Python modules; orchestrator shortcuts compose
them. The wire format embeds the target shortcut's identifier + name
inside a ``WFWorkflow`` dict and routes input through ``WFInput``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar, Final

from shortcut_lib.schema.base import Action, SchemaError, coerce_value

if TYPE_CHECKING:
    from shortcut_lib.builder import Shortcut


class _SelfRef:
    """Sentinel for ``RunWorkflow(target=Self)``.

    The containing :class:`~shortcut_lib.builder.Shortcut` rebinds this to a
    :class:`_BoundSelf` at ``add()`` time so emit doesn't need a second pass.
    """

    __slots__ = ()

    def __repr__(self) -> str:
        return "Self"


Self: Final = _SelfRef()


class _BoundSelf:
    """``Self`` bound to a specific containing shortcut.

    Internal — produced by ``Shortcut.add`` when it sees ``Self`` as a
    ``RunWorkflow.target``. Resolves at emit time to the containing
    shortcut's identity with ``isSelf=True``.
    """

    __slots__ = ("shortcut",)

    def __init__(self, shortcut: Shortcut) -> None:
        self.shortcut = shortcut


@dataclass
class RunWorkflow(Action):
    """Run another shortcut, optionally with input.

    Args:
        target: A :class:`shortcut_lib.builder.Shortcut` instance, a
            ``(identifier, name)`` tuple, or the :data:`Self` sentinel
            to recurse into the containing shortcut. ``Self`` only
            resolves once the action is added to a Shortcut.
        input: Value passed to the target as its input. Optional.
        show_workflow: Whether the target shows its UI when run. Mirrors
            Apple's "Show When Run" toggle. Defaults to ``True``.
    """

    target: Any = None
    input: Any = None
    show_workflow: bool = True

    identifier: ClassVar[str] = "is.workflow.actions.runworkflow"
    default_output_name: ClassVar[str] = "Result"

    def _params(self) -> dict[str, Any]:
        if self.target is None:
            raise SchemaError("RunWorkflow requires `target`")
        target_identifier, target_name, is_self = _resolve_target(self.target)

        params: dict[str, Any] = {
            "WFShowWorkflow": self.show_workflow,
            "WFWorkflow": {
                "isSelf": is_self,
                "workflowIdentifier": target_identifier,
                "workflowName": target_name,
            },
            "WFWorkflowName": target_name,
        }
        if self.input is not None:
            params["WFInput"] = coerce_value(self.input)
        return params


def _resolve_target(target: Any) -> tuple[str, str, bool]:
    """Resolve a target spec to (identifier, name, is_self)."""
    # Late import to avoid the circular dependency.
    from shortcut_lib.builder import Shortcut

    if isinstance(target, _BoundSelf):
        return target.shortcut.workflow_identifier, target.shortcut.name, True
    if isinstance(target, Shortcut):
        return target.workflow_identifier, target.name, False
    if isinstance(target, tuple) and len(target) == 2:
        return str(target[0]), str(target[1]), False
    if isinstance(target, _SelfRef):
        raise SchemaError(
            "RunWorkflow(target=Self) only resolves once the action is added "
            "to a Shortcut. Call shortcut.add(RunWorkflow(target=Self, ...))."
        )
    raise SchemaError(
        f"RunWorkflow target must be a Shortcut, (identifier, name) tuple, "
        f"or the Self sentinel; got {type(target).__name__}"
    )
