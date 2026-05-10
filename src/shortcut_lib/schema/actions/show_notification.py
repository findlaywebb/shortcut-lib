"""ShowNotification — show a system notification banner."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action, ParamValue, coerce_text_field
from shortcut_lib.schema.registry import register


@register
@dataclass
class ShowNotification(Action):
    """Show Notification — display a system notification banner.

    Wraps ``is.workflow.actions.notification``. Posts a local notification
    to the Notification Center with an optional title and body. Produces
    no output (no ``default_output_name``).

    Args:
        title: The notification title (``WFNotificationActionTitle``).
            Accepts a plain string, a
            :class:`~shortcut_lib.schema.values.Text` template, or any
            :class:`~shortcut_lib.schema.base.Action` /
            :class:`~shortcut_lib.schema.base.Value` reference. Omitted
            from the plist when empty.
        body: The notification body text
            (``WFNotificationActionBody``). Same rules as ``title``.
            Omitted from the plist when empty.
        play_sound: Controls the alert sound
            (``WFNotificationActionSound``). ``True`` plays a sound,
            ``False`` silences it. ``None`` omits the key — Apple
            defaults to playing a sound.

    Sample citations:
        samples/decoded/dictionary.xml:1657 — title + body, no sound key.
        samples/decoded/intelly.xml:32 — title-only notification.
    """

    title: ParamValue = field(default="")
    body: ParamValue = field(default="")
    play_sound: bool | None = None

    identifier: ClassVar[str] = "is.workflow.actions.notification"

    def _params(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        # Title and body are WFTextTokenString slots. Plain strings pass
        # through unchanged; variable refs are wrapped as a single-attachment
        # WFTextTokenString so the field links cleanly on import.
        coerced_title = coerce_text_field(self.title)
        if coerced_title != "":
            out["WFNotificationActionTitle"] = coerced_title
        coerced_body = coerce_text_field(self.body)
        if coerced_body != "":
            out["WFNotificationActionBody"] = coerced_body
        if self.play_sound is not None:
            out["WFNotificationActionSound"] = self.play_sound
        return out
