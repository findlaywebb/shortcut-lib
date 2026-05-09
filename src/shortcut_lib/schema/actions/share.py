"""Share — open the share sheet with a value."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action, ParamValue, coerce_value
from shortcut_lib.schema.registry import register


@register
@dataclass
class Share(Action):
    """Open the iOS/macOS share sheet with a value.

    Presents the system share sheet so the user can send the input to
    any available activity (Messages, Mail, AirDrop, save-to-Files,
    and so on).  The action produces no output.

    Three corpus samples all carry only ``WFInput``; no share-scope or
    activity-type filter key has been observed.

    Samples:
        combine_screenshots_and_share.xml — NamedVar "Screenshots"
        daily_standup.xml                 — ActionOutput ("Text")
        dictionary.xml                    — ActionOutput ("Details of Podcast Episodes")

    Args:
        input: Value to share.  Pass an ``Action``, an ``Output`` /
            ``NamedVar`` reference, a plain string, or any other
            ``ParamValue``.  When ``None`` the ``WFInput`` key is
            omitted and Shortcuts will share whatever is in the
            pipeline.
    """

    input: ParamValue = None

    identifier: ClassVar[str] = "is.workflow.actions.share"

    def _params(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.input is not None:
            out["WFInput"] = coerce_value(self.input)
        return out
