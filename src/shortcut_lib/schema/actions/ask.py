"""AskForInput — prompt the user to type or speak a value."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action
from shortcut_lib.schema.registry import register

_NUMBER_ANSWER_KEY = "WFAskActionDefaultAnswerNumber"
_TEXT_ANSWER_KEY = "WFAskActionDefaultAnswer"

# Apple plist key is WFInputType, not "type" (Jellycore's field name).
_VALID_TYPES = {"Text", "URL", "Number", "Date", "Time", "Date and Time"}


@register
@dataclass
class AskForInput(Action):
    """Prompt the user to enter a value.

    Input type controls the keyboard/picker shown. For Number type,
    ``default_answer`` is routed to ``WFAskActionDefaultAnswerNumber``
    and the decimal/negative flags are emitted when set. For all other
    types those flags are suppressed.

    Note: ``Ask`` is already taken as a magic-variable singleton in
    ``shortcut_lib.schema.values``; this class is ``AskForInput``.

    Divergence from Jellycore: Jellycore's ``AskForInputParameter.swift``
    declares ``type`` as the field name; the real Apple plist key is
    ``WFInputType``. This implementation uses the correct key.
    """

    identifier: ClassVar[str] = "is.workflow.actions.ask"
    default_output_name: ClassVar[str] = "Provided Input"

    prompt: str = ""
    input_type: str = "Text"
    default_answer: str | None = None
    allows_decimal: bool | None = None
    allows_negative: bool | None = None

    def _params(self) -> dict[str, Any]:
        """Emit only the relevant parameter keys for the chosen input_type."""
        out: dict[str, Any] = {}
        if self.prompt:
            out["WFAskActionPrompt"] = self.prompt
        out["WFInputType"] = self.input_type
        if self.default_answer is not None:
            if self.input_type == "Number":
                out[_NUMBER_ANSWER_KEY] = self.default_answer
            else:
                out[_TEXT_ANSWER_KEY] = self.default_answer
        if self.input_type == "Number":
            if self.allows_decimal is not None:
                out["WFAskActionAllowsDecimalNumbers"] = self.allows_decimal
            if self.allows_negative is not None:
                out["WFAskActionAllowsNegativeNumbers"] = self.allows_negative
        return out
