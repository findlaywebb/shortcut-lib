"""GetTravelTime — query estimated travel time to a destination."""

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

# Transport mode values as shown in Shortcuts.app's Get Travel Time action.
# "Driving" is the default — samples omit the key entirely when it is selected.
# The full set is confirmed from Apple's Shortcuts action dictionary.
WFTransportType = Literal[
    "Driving",
    "Walking",
    "Transit",
    "Cycling",
]

_VALID_TRANSPORT_TYPES: frozenset[str] = frozenset(get_args(WFTransportType))


@register
@dataclass
class GetTravelTime(Action):
    """Get the estimated travel time to a destination.

    Args:
        destination: The target location. Pass an Action output (e.g. from
            a Search Maps or Get Contacts action), a bare address string,
            or any Value. Corresponds to Apple's ``WFDestination`` parameter.
            All 3 corpus samples emit a plain WFTextTokenAttachment envelope,
            so this slot uses coerce_value (not coerce_text_field).
        transport_type: One of "Driving", "Walking", "Transit", "Cycling".
            Defaults to "Driving". When "Driving" is selected, Shortcuts.app
            omits the key from the emitted dict; all other values are emitted
            explicitly.
        origin: Optional origin address or location. When omitted, Shortcuts
            uses the device's current location. Corresponds to Apple's
            ``WFFromAddress`` parameter.
    """

    identifier: ClassVar[str] = "is.workflow.actions.gettraveltime"
    default_output_name: ClassVar[str] = "Travel Time"

    destination: ParamValue = None
    transport_type: WFTransportType = field(default="Driving")
    origin: ParamValue = None

    def __post_init__(self) -> None:
        if self.transport_type not in _VALID_TRANSPORT_TYPES:
            raise SchemaError(
                f"transport_type {self.transport_type!r} is not valid. "
                f"Expected one of: {sorted(_VALID_TRANSPORT_TYPES)}"
            )

    def _params(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.destination is not None:
            # WFDestination is a plain attachment slot — corpus samples use a
            # bare WFTextTokenAttachment envelope, not WFTextTokenString.
            out["WFDestination"] = coerce_value(self.destination)
        if self.origin is not None:
            out["WFFromAddress"] = coerce_value(self.origin)
        # "Driving" is the default; Shortcuts.app omits the key entirely when
        # selected — confirmed by all 3 corpus samples which use the default
        # and carry no WFTransportType key.
        if self.transport_type != "Driving":
            out["WFTransportType"] = self.transport_type
        return out
