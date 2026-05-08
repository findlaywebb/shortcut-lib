"""Comment — annotate a shortcut with a text comment block."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action, ParamValue, coerce_text_field
from shortcut_lib.schema.registry import register


@register
@dataclass
class Comment(Action):
    """Embed a text comment block inside a shortcut.

    Comments are not executed and produce no output. Variable references
    are allowed (Apple's UI lets you embed a {Token} in a comment); they
    emit as a single-attachment WFTextTokenString.

    Args:
        text: The comment body. Newlines are preserved. Pass a plain
            string, a :class:`~shortcut_lib.schema.values.Text` template,
            or any Action/Value reference.
    """

    text: ParamValue = ""

    identifier: ClassVar[str] = "is.workflow.actions.comment"

    def _params(self) -> dict[str, Any]:
        return {"WFCommentActionText": coerce_text_field(self.text)}
