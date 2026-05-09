"""AppendVariable — append a value to a named variable (list-style accumulation)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action, ParamValue, SchemaError, coerce_value
from shortcut_lib.schema.registry import register


@register
@dataclass
class AppendVariable(Action):
    """Add to Variable — append a value to a named variable.

    Adds the input to the end of an existing Shortcuts variable, creating
    it on first use. Emits ``WFVariableName`` and (optionally) ``WFInput``
    in the ``is.workflow.actions.appendvariable`` plist entry.

    Useful for accumulating items inside a Repeat block; the variable
    grows into a list with one entry per loop iteration.

    Args:
        name: The Shortcuts variable name to append to (``WFVariableName``).
            Raises :class:`~shortcut_lib.schema.base.SchemaError` if empty.
        input: The value to append. Pass another :class:`~shortcut_lib.schema.base.Action`
            to chain off its output, a plain string, or any
            :class:`~shortcut_lib.schema.base.Value`. Omitted from the plist
            when ``None``.

    Sample citation:
        samples/decoded/dictionary.xml:147 — plain ``WFVariableName`` form.
    """

    name: str = ""
    input: ParamValue = None

    identifier: ClassVar[str] = "is.workflow.actions.appendvariable"

    def _params(self) -> dict[str, Any]:
        if not self.name:
            raise SchemaError("AppendVariable requires `name`")
        out: dict[str, Any] = {"WFVariableName": self.name}
        if self.input is not None:
            out["WFInput"] = coerce_value(self.input)
        return out
