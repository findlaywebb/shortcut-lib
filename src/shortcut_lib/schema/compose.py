"""Composition: shortcuts calling other shortcuts via Run Workflow.

Helper shortcuts work like Python modules; orchestrator shortcuts compose
them. The wire format embeds the target shortcut's identifier + name
inside a ``WFWorkflow`` dict and routes input through ``WFInput``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

from shortcut_lib.schema.base import Action, SchemaError, coerce_value

if TYPE_CHECKING:
    pass


@dataclass
class RunWorkflow(Action):
    """Run another shortcut, optionally with input.

    Args:
        target: A :class:`shortcut_lib.builder.Shortcut` instance,
            or a ``(identifier, name)`` tuple, or the special string
            ``"self"`` to recurse into the containing shortcut.
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

    if isinstance(target, Shortcut):
        return target.workflow_identifier, target.name, False
    if isinstance(target, tuple) and len(target) == 2:
        return str(target[0]), str(target[1]), False
    if target == "self":
        # Caller resolves at encode time via Shortcut._resolve_self_refs.
        return "__SELF__", "__SELF__", True
    raise SchemaError(
        f"RunWorkflow target must be a Shortcut, (identifier, name) tuple, "
        f"or 'self'; got {type(target).__name__}"
    )
