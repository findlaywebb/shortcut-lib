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
    """Use Model — send a prompt to Apple Intelligence and return the response.

    Wraps ``is.workflow.actions.askllm`` (displayed as "Use Model" in the
    Shortcuts editor). Requires Apple Intelligence to be enabled in System
    Settings (iOS 18.1+ / macOS 26+). The ``WFLLMPrompt`` slot is a
    ``WFTextTokenString`` — variable refs must be wrapped as a
    single-attachment templated string.

    Args:
        prompt: The prompt to send (``WFLLMPrompt``). Required; raises
            :class:`~shortcut_lib.schema.base.SchemaError` if ``None``.
            Accepts a plain string, a
            :class:`~shortcut_lib.schema.values.Text` template, or any
            :class:`~shortcut_lib.schema.base.Action` /
            :class:`~shortcut_lib.schema.base.Value` reference.
        model: Which model to invoke (``WFLLMModel``). Defaults to
            ``"Apple Intelligence"``. One of:

            - ``"Apple Intelligence"`` — on-device default
            - ``"Private Cloud Compute"`` — Apple's privacy-preserving cloud
            - ``"On-Device"`` — explicitly on-device (no cloud fallback)
            - ``"Extension"`` — routes to ChatGPT or another configured extension
            - ``"Ask Each Time"`` — user selects the model at run time

            The wire-format strings match the Shortcuts.app GUI dropdown
            verbatim. Raises
            :class:`~shortcut_lib.schema.base.SchemaError` for unknown values.

    Returns:
        The model's text response (output name: "Model Response").

    Sample citation:
        samples/decoded/intelly.xml:63 — WFLLMModel + WFLLMPrompt with a
        variable-reference prompt.
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
