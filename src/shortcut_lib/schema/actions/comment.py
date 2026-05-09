"""Comment — annotate a shortcut with a text comment block."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action, ParamValue, coerce_text_field
from shortcut_lib.schema.registry import register


@register
@dataclass
class Comment(Action):
    """Comment — embed a text annotation inside a shortcut.

    Wraps ``is.workflow.actions.comment``. The action is never executed
    at runtime and produces no output; it exists solely for documentation
    within the shortcut editor.

    Variable references are allowed — Apple's UI lets you embed a
    ``{Token}`` in a comment, which is stored as a single-attachment
    ``WFTextTokenString`` in the plist.

    Args:
        text: The comment body (``WFCommentActionText``). Newlines are
            preserved. Pass a plain string, a
            :class:`~shortcut_lib.schema.values.Text` template, or any
            :class:`~shortcut_lib.schema.base.Action` /
            :class:`~shortcut_lib.schema.base.Value` reference.

    Sample citations:
        samples/decoded/batch_add_reminders.xml:11 — plain string comment.
        samples/decoded/dictionary.xml:11 — plain string comment.
    """

    text: ParamValue = ""

    identifier: ClassVar[str] = "is.workflow.actions.comment"

    def _params(self) -> dict[str, Any]:
        return {"WFCommentActionText": coerce_text_field(self.text)}
