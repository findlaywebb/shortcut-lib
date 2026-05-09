"""GetClipboard — read the current system clipboard contents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action
from shortcut_lib.schema.registry import register


@register
@dataclass
class GetClipboard(Action):
    """Get Clipboard — read the current system clipboard contents.

    Wraps ``is.workflow.actions.getclipboard``. Takes no parameters and
    reads the clipboard unconditionally at the point the action runs.
    The clipboard value is returned as a content item and is also
    available as a magic variable in subsequent actions.

    Returns:
        The clipboard contents as a content item (output name: "Clipboard").

    Sample citations:
        samples/decoded/clean_up_clipboard.xml:11 — bare action, no params.
        samples/decoded/adjust_clipboard.xml:11 — bare action, no params.
    """

    identifier: ClassVar[str] = "is.workflow.actions.getclipboard"
    default_output_name: ClassVar[str] = "Clipboard"

    def _params(self) -> dict[str, Any]:
        return {}
