"""SetVariable — assign a value to a named Shortcuts variable."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action, ParamValue, SchemaError, coerce_value
from shortcut_lib.schema.registry import register


@register
@dataclass
class SetVariable(Action):
    """Set Variable — assign a value to a named Shortcuts variable.

    Wraps ``is.workflow.actions.setvariable``. Stores any value under a
    user-visible name. The name is later referenced by a
    :class:`~shortcut_lib.schema.values.NamedVar` or Apple's
    magic-variable picker. This action does not produce an output UUID
    reference of its own (no ``default_output_name``).

    Args:
        name: Variable name visible in the Shortcuts UI
            (``WFVariableName``). Raises
            :class:`~shortcut_lib.schema.base.SchemaError` if empty.
        input: Value to store (``WFInput``). Pass another
            :class:`~shortcut_lib.schema.base.Action` to chain off its
            output, a literal string, or any
            :class:`~shortcut_lib.schema.base.Value` instance. Omitted
            from the plist when ``None``.

    Sample citations:
        samples/decoded/add_expiry_reminder.xml:24 — stores a previous
        action output into a named variable.
        samples/decoded/dictionary.xml:135 — plain WFVariableName form.
    """

    name: str = ""
    input: ParamValue = None

    identifier: ClassVar[str] = "is.workflow.actions.setvariable"

    def _params(self) -> dict[str, Any]:
        if not self.name:
            raise SchemaError("SetVariable requires `name`")
        out: dict[str, Any] = {"WFVariableName": self.name}
        if self.input is not None:
            out["WFInput"] = coerce_value(self.input)
        return out
