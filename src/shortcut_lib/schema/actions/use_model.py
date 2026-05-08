"""UseModel — call Apple Intelligence (or ChatGPT) on a prompt."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Literal, get_args

from shortcut_lib.schema.base import (
    Action,
    ParamValue,
    SchemaError,
    coerce_text_field,
)
from shortcut_lib.schema.registry import register

# Wire-format strings shown in Shortcuts.app's GUI dropdown for the LLM
# selector. Confirmed by sample inspection (intelly.shortcut). The
# best-practices review suggested possible iOS 26 additions (On-Device
# with Reasoning, Cloud Verifiable, Custom Endpoint, ChatGPT) — none of
# those are sample-confirmed yet, so they're left out until a real export
# uses them.
WFLLMModel = Literal[
    "Apple Intelligence",
    "Private Cloud Compute",
    "On-Device",
    "Extension",
    "Ask Each Time",
]
_VALID_MODELS: frozenset[str] = frozenset(get_args(WFLLMModel))


@register
@dataclass
class UseModel(Action):
    """Send a prompt to Apple Intelligence or ChatGPT and return the response.

    Apple identifier: ``is.workflow.actions.askllm``. Requires Apple
    Intelligence to be enabled in System Settings (iOS 18.1+/macOS 26+).

    Args:
        prompt: The prompt to send. String, Text template, or Output ref.
        model: Which model to use. One of :data:`WFLLMModel`:
            - ``"Apple Intelligence"`` (the on-device default)
            - ``"Private Cloud Compute"`` (Apple's cloud-relay model)
            - ``"On-Device"``
            - ``"Extension"`` — routes to ChatGPT (or another configured
              extension)
            - ``"Ask Each Time"`` — prompts the user at run time
            The wire-format strings shown in Shortcuts.app's GUI dropdown
            match what's emitted into the plist; pass any of them
            verbatim.
    """

    prompt: ParamValue = None
    model: WFLLMModel = "Apple Intelligence"

    identifier: ClassVar[str] = "is.workflow.actions.askllm"
    default_output_name: ClassVar[str] = "Model Response"

    def __post_init__(self) -> None:
        if self.model not in _VALID_MODELS:
            raise SchemaError(
                f"UseModel.model {self.model!r} is not valid. "
                f"Expected one of: {sorted(_VALID_MODELS)}"
            )

    def _params(self) -> dict[str, Any]:
        if self.prompt is None:
            raise SchemaError("UseModel requires `prompt`")
        return {
            "WFLLMModel": self.model,
            # WFLLMPrompt is a WFTextTokenString slot — variable refs need
            # a single-attachment templated-string envelope.
            "WFLLMPrompt": coerce_text_field(self.prompt),
        }
