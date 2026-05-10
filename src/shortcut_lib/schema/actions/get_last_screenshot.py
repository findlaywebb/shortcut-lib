"""GetLastScreenshot — fetch the most recent screenshots."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action
from shortcut_lib.schema.registry import register


@register
@dataclass
class GetLastScreenshot(Action):
    """Return the most recent N screenshots from the device.

    Verified against:
    - ``samples/decoded/combine_screenshots_and_share.xml`` — one appearance
      with ``WFGetLatestPhotoCount`` set to an "Ask" dynamic token, confirming
      the parameter key name.
    - ``samples/decoded/dictionary.xml`` — two appearances with no explicit
      count (UUID only), confirming omission is valid for the Apple default.

    Args:
        count: Number of screenshots to return. ``None`` omits the key and
            lets Apple use its default (1).

    Output name: "Latest Screenshots"
    """

    identifier: ClassVar[str] = "is.workflow.actions.getlastscreenshot"
    default_output_name: ClassVar[str] = "Latest Screenshots"

    count: int | None = None

    def _params(self) -> dict[str, Any]:
        """Return WF parameter dict for this get-last-screenshot action."""
        params: dict[str, Any] = {}
        if self.count is not None:
            params["WFGetLatestPhotoCount"] = self.count
        return params
