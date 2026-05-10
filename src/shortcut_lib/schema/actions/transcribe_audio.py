"""TranscribeAudio — transcribe a recorded audio file to text."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action, ParamValue, coerce_value
from shortcut_lib.schema.registry import register

# AppIntentDescriptor dict copied verbatim from
# samples/decoded/private/voice_note_to_github.xml.
# These are Apple-side constants identifying the built-in ShortcutsActions
# bundle — treat them as opaque and do not change them.
_APP_INTENT_DESCRIPTOR: dict[str, Any] = {
    "AppIntentIdentifier": "TranscribeAudioAction",
    "BundleIdentifier": "com.apple.ShortcutsActions",
    "Name": "ShortcutsActions",
    "TeamIdentifier": "0000000000",
}


@register
@dataclass
class TranscribeAudio(Action):
    """Transcribe Audio — convert an audio file to text on-device.

    Wraps the AppIntent
    ``com.apple.ShortcutsActions.TranscribeAudioAction`` — a first-party
    action in Apple's ``com.apple.ShortcutsActions`` bundle. Uses on-device
    speech recognition (no network required).

    Unlike standard ``is.workflow.actions.*`` entries, this action emits
    an ``AppIntentDescriptor`` dict containing Apple-owned bundle metadata
    that Shortcuts.app uses to resolve the AppIntent at runtime. The dict
    is treated as an opaque constant; do not modify it.

    Args:
        audio_file: The audio recording to transcribe (``audioFile``).
            Pass a :class:`~shortcut_lib.schema.values.NamedVar`, a
            :class:`RecordAudio` action output, or any coercible
            :class:`~shortcut_lib.schema.base.Value` whose output is an
            audio file. Omitted when ``None``.

    Returns:
        The transcribed text string (output name: "Transcribe Audio").

    Sample citation:
        samples/decoded/private/voice_note_to_github.xml — full
        ``AppIntentDescriptor`` + ``audioFile`` parameter shape.
    """

    identifier: ClassVar[str] = "com.apple.ShortcutsActions.TranscribeAudioAction"
    default_output_name: ClassVar[str] = "Transcribe Audio"

    audio_file: ParamValue = None

    def _params(self) -> dict[str, Any]:
        """Return the WF parameter dict for this transcribe-audio action."""
        out: dict[str, Any] = {
            "AppIntentDescriptor": dict(_APP_INTENT_DESCRIPTOR),
        }
        if self.audio_file is not None:
            out["audioFile"] = coerce_value(self.audio_file)
        return out
