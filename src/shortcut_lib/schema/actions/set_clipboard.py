"""SetClipboard — write a value to the system clipboard."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action, ParamValue, coerce_value
from shortcut_lib.schema.registry import register


@register
@dataclass
class SetClipboard(Action):
    """Set Clipboard — write a value to the system clipboard.

    Wraps ``is.workflow.actions.setclipboard``. Replaces the clipboard
    contents with the given input. Produces no output of its own.

    Args:
        input: The value to write to the clipboard (``WFInput``). Pass
            another :class:`~shortcut_lib.schema.base.Action` to chain
            off its output, a literal string, or any
            :class:`~shortcut_lib.schema.base.Value`. Omitted from the
            plist when ``None``.

    Sample citations:
        samples/decoded/dictate_to_clipboard.xml:20 — WFInput as
        WFTextTokenAttachment referencing the preceding DictateText output.
        samples/decoded/clean_up_clipboard.xml:49 — WFInput as
        WFTextTokenAttachment.
    """

    input: ParamValue = None

    identifier: ClassVar[str] = "is.workflow.actions.setclipboard"

    def _params(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.input is not None:
            out["WFInput"] = coerce_value(self.input)
        return out
