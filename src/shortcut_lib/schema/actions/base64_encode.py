"""Base64Encode — encode or decode data as base64."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action, coerce_value
from shortcut_lib.schema.registry import register

_DEFAULT_MODE = "Encode"


@register
@dataclass
class Base64Encode(Action):
    """Encode or decode the input using base64.

    Args:
        input: Value to process. Pass another Action to chain off its output,
            a literal string, or any Value.
        mode: "Encode" (default) or "Decode". When "Encode" the key is
            omitted from the wire format, matching Apple's convention.

    Output name: "Base64 Encoded"
    """

    input: Any = None
    mode: str = _DEFAULT_MODE

    identifier: ClassVar[str] = "is.workflow.actions.base64encode"
    default_output_name: ClassVar[str] = "Base64 Encoded"

    def _params(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.input is not None:
            out["WFInput"] = coerce_value(self.input)
        # Omit WFEncodeMode when it's the default ("Encode") — matches samples.
        if self.mode != _DEFAULT_MODE:
            out["WFEncodeMode"] = self.mode
        return out
