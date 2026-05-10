"""ExitShortcut — terminate the shortcut early."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action
from shortcut_lib.schema.registry import register


@register
@dataclass
class ExitShortcut(Action):
    """Exit Shortcut — terminate the shortcut run immediately.

    Wraps ``is.workflow.actions.exit``. Takes no parameters and produces
    no output. Execution stops at this action; no subsequent actions run.

    Typically used as a guard after an If block::

        If(clipboard is empty) → ExitShortcut()

    Sample citations:
        samples/decoded/adjust_clipboard.xml:70 — bare exit with no params.
        samples/decoded/dictionary.xml:1359 — bare exit with no params.
    """

    identifier: ClassVar[str] = "is.workflow.actions.exit"

    def _params(self) -> dict[str, Any]:
        return {}
