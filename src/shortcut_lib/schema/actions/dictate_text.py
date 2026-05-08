"""DictateText — speech-to-text input."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action
from shortcut_lib.schema.registry import register


@register
@dataclass
class DictateText(Action):
    """Prompt the user to dictate text via speech.

    Output: the dictated string.
    """

    locale: str | None = None  # e.g. "en-GB"; None means device default
    stop_listening: str | None = (
        None  # e.g. "After Pause", "After Short Pause", "On Tap"
    )

    identifier: ClassVar[str] = "is.workflow.actions.dictatetext"
    default_output_name: ClassVar[str] = "Dictated Text"

    def _params(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.locale is not None:
            out["WFSpeechLanguage"] = self.locale
        if self.stop_listening is not None:
            out["WFDictateTextStopListening"] = self.stop_listening
        return out
