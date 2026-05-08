"""ExitShortcut — terminate the shortcut early."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action
from shortcut_lib.schema.registry import register


@register
@dataclass
class ExitShortcut(Action):
    """Stop running the shortcut immediately.

    Useful as a guard inside an If: ``if clipboard is empty, exit early``.
    Takes no parameters; produces no output.
    """

    identifier: ClassVar[str] = "is.workflow.actions.exit"

    def _params(self) -> dict[str, Any]:
        return {}
