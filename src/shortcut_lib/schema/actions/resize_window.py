"""ResizeWindow — resize or tile a macOS window (macOS 12+)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Literal, get_args

from shortcut_lib.schema.base import (
    Action,
    ParamValue,
    SchemaError,
    coerce_value,
)
from shortcut_lib.schema.registry import register

# Closed set of tiling/resize configuration strings for Shortcuts.app's
# "Resize Window" action on macOS.  The two preset values are confirmed
# directly from corpus samples:
#   - "Left Half"  — samples/decoded/tile_last_2_windows.xml:50
#   - "Right Half" — samples/decoded/tile_last_2_windows.xml:100
# The remaining presets are the standard macOS Stage Manager / tiling grid
# positions that appear in Shortcuts.app's dropdown (no custom-size mode is
# exposed via WFConfiguration in any sampled shortcut; jellycore lists
# WFHeight / WFWidth as separate keys used only when configuration is absent).
WFWindowConfiguration = Literal[
    "Left Half",
    "Right Half",
    "Top Half",
    "Bottom Half",
    "Top Left Quarter",
    "Top Right Quarter",
    "Bottom Left Quarter",
    "Bottom Right Quarter",
    "Fill",
    "Center",
]

_VALID_CONFIGURATIONS: frozenset[str] = frozenset(get_args(WFWindowConfiguration))


@register
@dataclass
class ResizeWindow(Action):
    """Resize or tile a macOS window to a preset position.

    Args:
        window: The window to resize.  Pass an Action whose output is a
            Window object (e.g. the result of a ``Find Windows`` or
            ``Get Item from List`` action), any ``Value``, or a pre-built
            ``WFTextTokenAttachment`` envelope dict.  Corresponds to Apple's
            ``WFWindow`` parameter.
        configuration: Tiling preset string.  One of the ``WFWindowConfiguration``
            literals (e.g. ``"Left Half"``, ``"Right Half"``).  When ``None``
            the ``WFConfiguration`` key is omitted entirely — matching the
            bare-window-only form seen in ``samples/decoded/dictionary.xml``.
        bring_to_front: When ``True`` emits ``WFBringToFront = True``.
            Defaults to ``None`` (key omitted).
    """

    identifier: ClassVar[str] = "is.workflow.actions.resizewindow"
    default_output_name: ClassVar[str] = "Resize Window"

    window: ParamValue = None
    configuration: WFWindowConfiguration | None = field(default=None)
    bring_to_front: bool | None = field(default=None)

    def __post_init__(self) -> None:
        if (
            self.configuration is not None
            and self.configuration not in _VALID_CONFIGURATIONS
        ):
            raise SchemaError(
                f"ResizeWindow.configuration {self.configuration!r} is not valid. "
                f"Expected one of: {sorted(_VALID_CONFIGURATIONS)}"
            )

    def _params(self) -> dict[str, Any]:
        """Emit WFWindow, optionally WFConfiguration and WFBringToFront."""
        out: dict[str, Any] = {}
        if self.window is not None:
            out["WFWindow"] = coerce_value(self.window)
        if self.configuration is not None:
            out["WFConfiguration"] = self.configuration
        if self.bring_to_front is not None:
            out["WFBringToFront"] = self.bring_to_front
        return out
