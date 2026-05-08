"""GetClipboard — read the current system clipboard contents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action
from shortcut_lib.schema.registry import register


@register
@dataclass
class GetClipboard(Action):
    """Return the current clipboard contents as a content item.

    No parameters — Apple's action reads the clipboard unconditionally.
    The output is the clipboard value, available as a magic variable in
    subsequent actions.

    Output name: "Clipboard"
    """

    identifier: ClassVar[str] = "is.workflow.actions.getclipboard"
    default_output_name: ClassVar[str] = "Clipboard"

    def _params(self) -> dict[str, Any]:
        return {}
