"""GetLastPhoto — fetch the most recent photos from the camera roll."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action
from shortcut_lib.schema.registry import register


@register
@dataclass
class GetLastPhoto(Action):
    """Return the most recent N photos from the device camera roll.

    Verified against:
    - ``samples/decoded/email_last_image.xml`` (no explicit count — default)
    - ``samples/decoded/dictionary.xml`` (no explicit count — two appearances)

    All three corpus appearances emit only UUID in WFWorkflowActionParameters,
    meaning ``WFGetLatestPhotoCount`` is omitted when using the Apple default
    (1 photo). The parameter name ``WFGetLatestPhotoCount`` is confirmed from
    the sibling action ``getlastscreenshot`` in
    ``samples/decoded/combine_screenshots_and_share.xml``.

    Args:
        count: Number of photos to return. ``None`` omits the key and lets
            Apple use its default (1).

    Output name: "Latest Photos"
    """

    identifier: ClassVar[str] = "is.workflow.actions.getlastphoto"
    default_output_name: ClassVar[str] = "Latest Photos"

    count: int | None = None

    def _params(self) -> dict[str, Any]:
        """Return WF parameter dict for this get-last-photo action."""
        params: dict[str, Any] = {}
        if self.count is not None:
            params["WFGetLatestPhotoCount"] = self.count
        return params
