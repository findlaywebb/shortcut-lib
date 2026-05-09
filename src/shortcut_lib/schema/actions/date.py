"""DateAction — return the current date or a specified date."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar, Literal, get_args

from shortcut_lib.schema.base import Action, SchemaError
from shortcut_lib.schema.registry import register

# Two modes surfaced in Apple's Shortcuts UI.
WFDateActionMode = Literal["Current Date", "Specified Date"]

_VALID_MODES: frozenset[str] = frozenset(get_args(WFDateActionMode))


@register
@dataclass
class DateAction(Action):
    """Return the current date or a fixed date value.

    Both corpus appearances (daily_standup.xml:870 and dictionary.xml:482)
    emit an empty parameters dict (UUID only), which means mode defaults to
    "Current Date" and the ``WFDateActionDate`` key is absent.

    Args:
        mode: "Current Date" (default) or "Specified Date". Corresponds to
            Apple's ``WFDateActionMode`` key. When "Current Date" the key is
            omitted from the emitted dict, matching the wire format observed
            in both corpus samples.
        date: The literal date string used when ``mode`` is "Specified Date".
            Corresponds to Apple's ``WFDateActionDate`` key. Required when
            ``mode`` is "Specified Date"; ignored otherwise.
    """

    identifier: ClassVar[str] = "is.workflow.actions.date"
    default_output_name: ClassVar[str] = "Date"

    mode: WFDateActionMode = field(default="Current Date")
    date: str | None = field(default=None)

    def __post_init__(self) -> None:
        if self.mode not in _VALID_MODES:
            raise SchemaError(
                f"mode {self.mode!r} is not valid. "
                f"Expected one of: {sorted(_VALID_MODES)}"
            )
        if self.mode == "Specified Date" and not self.date:
            raise SchemaError(
                'date must be set when mode is "Specified Date". '
                'Example: date="2025-01-01"'
            )

    def _params(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        # "Current Date" mode emits no keys — matches both corpus samples.
        if self.mode != "Current Date":
            out["WFDateActionMode"] = self.mode
        if self.mode == "Specified Date" and self.date:
            out["WFDateActionDate"] = self.date
        return out
