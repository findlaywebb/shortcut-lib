"""SetClipboard — write a value to the system clipboard."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action, coerce_value
from shortcut_lib.schema.registry import register


@register
@dataclass
class SetClipboard(Action):
    """Copy the input to the clipboard.

    Args:
        input: Value to copy. Pass another Action to chain off its output,
            or a literal string, or any Value.
    """

    input: Any = None

    identifier: ClassVar[str] = "is.workflow.actions.setclipboard"

    def _params(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.input is not None:
            out["WFInput"] = coerce_value(self.input)
        return out
