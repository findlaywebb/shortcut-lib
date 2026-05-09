"""ShowAlert — display a modal dialog with title and message."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action, ParamValue, coerce_text_field
from shortcut_lib.schema.registry import register


@register
@dataclass
class ShowAlert(Action):
    """Display a modal dialog with a title, message, and optional cancel button.

    Neither title nor message produces a meaningful action output, so no
    ``default_output_name`` is set.

    Samples:
        - samples/decoded/dictionary.xml[2]: empty params (all defaults).
        - samples/decoded/read_later.xml[15]: title="Link saved!",
          message="", show_cancel_button=False.

    Args:
        title: The alert dialog title. Accepts a plain string, a
            :class:`~shortcut_lib.schema.values.Text` template, or an
            :class:`~shortcut_lib.schema.values.Output` reference.
        message: The alert dialog message body (same rules as ``title``).
        show_cancel_button: When ``True`` or ``False``, emits
            ``WFAlertActionCancelButtonShown`` explicitly. ``None`` omits
            the key (Apple defaults to showing the cancel button).
    """

    title: ParamValue = field(default="")
    message: ParamValue = field(default="")
    show_cancel_button: bool | None = None

    identifier: ClassVar[str] = "is.workflow.actions.alert"

    def _params(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        coerced_title = coerce_text_field(self.title)
        if coerced_title != "":
            out["WFAlertActionTitle"] = coerced_title
        coerced_message = coerce_text_field(self.message)
        if coerced_message != "":
            out["WFAlertActionMessage"] = coerced_message
        if self.show_cancel_button is not None:
            out["WFAlertActionCancelButtonShown"] = self.show_cancel_button
        return out
