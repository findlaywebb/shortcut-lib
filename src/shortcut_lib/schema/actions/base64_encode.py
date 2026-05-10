"""Base64Encode — encode or decode data as base64."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action, ParamValue, coerce_value
from shortcut_lib.schema.registry import register

_DEFAULT_MODE = "Encode"


@register
@dataclass
class Base64Encode(Action):
    """Encode/Decode with Base64 — encode or decode data as base64.

    Wraps ``is.workflow.actions.base64encode``. Encodes arbitrary binary
    or text data as a base64 ASCII string, or reverses the operation.

    Args:
        input: Value to process (``WFInput``). Pass another
            :class:`~shortcut_lib.schema.base.Action` to chain off its
            output, a literal string, or any
            :class:`~shortcut_lib.schema.base.Value`. Omitted when ``None``.
        mode: ``"Encode"`` (default) or ``"Decode"`` (``WFEncodeMode``).
            When ``"Encode"``, the key is omitted from the plist entirely —
            Apple's convention for the default value. Pass ``"Decode"``
            explicitly to reverse the operation.

    Returns:
        The encoded or decoded string (output name: "Base64 Encoded").

    Sample citation:
        samples/decoded/dictionary.xml:1259 — default Encode mode (no
        ``WFEncodeMode`` key emitted).
    """

    input: ParamValue = None
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
