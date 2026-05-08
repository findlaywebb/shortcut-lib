"""UseModel — call Apple Intelligence (or ChatGPT) on a prompt."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action, SchemaError, coerce_value
from shortcut_lib.schema.registry import register


@register
@dataclass
class UseModel(Action):
    """Send a prompt to Apple Intelligence or ChatGPT and return the response.

    Apple identifier: ``is.workflow.actions.askllm``. Requires Apple
    Intelligence to be enabled in System Settings (iOS 18.1+/macOS 26+).

    Args:
        prompt: The prompt to send. String, Text template, or Output ref.
        model: Which model to use. Observed wire-format values:
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

    prompt: Any = None
    model: str = "Apple Intelligence"

    identifier: ClassVar[str] = "is.workflow.actions.askllm"
    default_output_name: ClassVar[str] = "Model Response"

    def _params(self) -> dict[str, Any]:
        if self.prompt is None:
            raise SchemaError("UseModel requires `prompt`")
        return {
            "WFLLMModel": self.model,
            "WFLLMPrompt": coerce_value(self.prompt),
        }
