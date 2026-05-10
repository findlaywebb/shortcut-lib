"""ShowResult — display a value to the user inside the shortcut."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action, ParamValue, coerce_text_field
from shortcut_lib.schema.registry import register


@register
@dataclass
class ShowResult(Action):
    """Display a result value to the user during shortcut execution.

    The action renders the current pipeline value (or an explicit text
    template) in an inline sheet inside the Shortcuts runner.  It
    produces no output of its own.

    Args:
        text: The value to display. Accepts a plain string, a
            :class:`~shortcut_lib.schema.values.Text` template, or an
            :class:`~shortcut_lib.schema.values.Output` reference.
            ``None`` (the default) omits the ``Text`` key entirely,
            which causes Shortcuts to display the implicit pipeline
            input — matching Apple's ``<dict/>`` wire form.
    """

    text: ParamValue = field(default=None)

    identifier: ClassVar[str] = "is.workflow.actions.showresult"

    def _params(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.text is not None:
            coerced = coerce_text_field(self.text)
            if coerced != "":
                out["Text"] = coerced
        return out
