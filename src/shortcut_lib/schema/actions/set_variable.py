"""SetVariable — assign a value to a named Shortcuts variable."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action, SchemaError, coerce_value
from shortcut_lib.schema.registry import register


@register
@dataclass
class SetVariable(Action):
    """Assign a value to a named Shortcuts variable.

    SetVariable stores any value under a user-visible name. The name is
    later referenced by a ``NamedVar`` or Apple's magic-variable picker.
    This action does not produce an output UUID reference of its own.

    Args:
        name: Variable name visible in the Shortcuts UI (``WFVariableName``).
        input: Value to store. Pass another Action to chain off its output,
            a literal string, or any ``Value`` instance.
    """

    name: str = ""
    input: Any = None

    identifier: ClassVar[str] = "is.workflow.actions.setvariable"

    def _params(self) -> dict[str, Any]:
        if not self.name:
            raise SchemaError("SetVariable requires `name`")
        out: dict[str, Any] = {"WFVariableName": self.name}
        if self.input is not None:
            out["WFInput"] = coerce_value(self.input)
        return out
