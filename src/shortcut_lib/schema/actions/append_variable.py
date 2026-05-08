"""AppendVariable — append a value to a named variable (list-style accumulation)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action, SchemaError, coerce_value
from shortcut_lib.schema.registry import register


@register
@dataclass
class AppendVariable(Action):
    """Append the input to a named variable.

    Useful for accumulating items inside a Repeat block. The variable is
    created on first append if it doesn't exist.
    """

    name: str = ""
    input: Any = None

    identifier: ClassVar[str] = "is.workflow.actions.appendvariable"

    def _params(self) -> dict[str, Any]:
        if not self.name:
            raise SchemaError("AppendVariable requires `name`")
        out: dict[str, Any] = {"WFVariableName": self.name}
        if self.input is not None:
            out["WFInput"] = coerce_value(self.input)
        return out
