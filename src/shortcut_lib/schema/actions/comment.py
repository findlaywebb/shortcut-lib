"""Comment — annotate a shortcut with a text comment block."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action
from shortcut_lib.schema.registry import register


@register
@dataclass
class Comment(Action):
    """Embed a text comment block inside a shortcut.

    Comments are not executed and produce no output.

    Args:
        text: The comment body. Newlines are preserved.
    """

    text: str = ""

    identifier: ClassVar[str] = "is.workflow.actions.comment"

    def _params(self) -> dict[str, Any]:
        return {"WFCommentActionText": self.text}
