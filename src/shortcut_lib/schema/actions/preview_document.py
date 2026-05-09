"""PreviewDocument — Quick Look / Preview action."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action, ParamValue, coerce_value
from shortcut_lib.schema.registry import register


@register
@dataclass
class PreviewDocument(Action):
    """Show a file or document in a Quick Look preview.

    Args:
        input: File, data, or any value to preview. Pass another Action to
            chain off its output, a literal string, or any Value. When
            omitted the action previews whatever is currently on the
            clipboard or the shortcut's input.

    Output name: "Quick Look"
    """

    input: ParamValue = None

    identifier: ClassVar[str] = "is.workflow.actions.previewdocument"
    default_output_name: ClassVar[str] = "Quick Look"

    def _params(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.input is not None:
            out["WFInput"] = coerce_value(self.input)
        return out
