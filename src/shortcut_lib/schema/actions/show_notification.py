"""ShowNotification — show a system notification banner."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action, ParamValue, coerce_value
from shortcut_lib.schema.registry import register


@register
@dataclass
class ShowNotification(Action):
    """Display a system notification with an optional title and body.

    Neither title nor body produces a meaningful action output, so no
    ``default_output_name`` is set.

    Args:
        title: The notification title. Accept a plain string, a
            :class:`~shortcut_lib.schema.values.Text` template, or an
            :class:`~shortcut_lib.schema.values.Output` reference.
        body: The notification body (same rules as ``title``).
        play_sound: If ``True`` or ``False``, the WFNotificationActionSound
            key is emitted explicitly. ``None`` means omit the key
            (Apple defaults to playing a sound).
    """

    title: ParamValue = field(default="")
    body: ParamValue = field(default="")
    play_sound: bool | None = None

    identifier: ClassVar[str] = "is.workflow.actions.notification"

    def _params(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        coerced_title = coerce_value(self.title)
        if coerced_title != "":
            out["WFNotificationActionTitle"] = coerced_title
        coerced_body = coerce_value(self.body)
        if coerced_body != "":
            out["WFNotificationActionBody"] = coerced_body
        if self.play_sound is not None:
            out["WFNotificationActionSound"] = self.play_sound
        return out
