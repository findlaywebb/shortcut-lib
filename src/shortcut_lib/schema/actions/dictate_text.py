"""DictateText — speech-to-text input."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action
from shortcut_lib.schema.registry import register


@register
@dataclass
class DictateText(Action):
    """Dictate Text — capture spoken words as a text string.

    Wraps ``is.workflow.actions.dictatetext``. Opens the device's
    speech-recognition interface and returns the transcribed text when the
    user stops speaking (or taps done).

    Args:
        locale: BCP-47 language tag for the recognition locale
            (``WFSpeechLanguage``). Examples: ``"en-GB"``, ``"fr-FR"``.
            Omitted when ``None`` — the device's system locale is used.
        stop_listening: Condition that ends the recording session
            (``WFDictateTextStopListening``). Known values observed in
            Apple's UI: ``"After Pause"``, ``"After Short Pause"``,
            ``"On Tap"``. Omitted when ``None`` — Apple applies its own
            default (typically ``"After Pause"``).

    Returns:
        The transcribed text string (output name: "Dictated Text").

    Sample citation:
        samples/decoded/dictate_to_clipboard.xml:11 — no locale or
        stop_listening keys emitted (device defaults).
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
