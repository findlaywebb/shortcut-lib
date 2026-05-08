"""TranscribeAudio — transcribe a recorded audio file to text."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action, coerce_value
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
    """Transcribe an audio file to text using on-device speech recognition.

    This is a first-party AppIntent action under the
    ``com.apple.ShortcutsActions`` bundle, verified against
    ``samples/decoded/private/voice_note_to_github.xml``.

    The ``AppIntentDescriptor`` dict is emitted verbatim — it contains
    Apple-owned bundle metadata that Shortcuts.app requires in order to
    resolve the AppIntent at runtime.

    Args:
        audio_file: The audio recording to transcribe. Pass a
            :class:`~shortcut_lib.schema.values.NamedVar`, an
            :class:`~shortcut_lib.schema.base.Action` (typically
            :class:`RecordAudio`), or any coercible Value whose output is
            an audio file.

    Output: the transcribed text string.
    """

    identifier: ClassVar[str] = "com.apple.ShortcutsActions.TranscribeAudioAction"
    default_output_name: ClassVar[str] = "Transcribe Audio"

    audio_file: Any = None

    def _params(self) -> dict[str, Any]:
        """Return the WF parameter dict for this transcribe-audio action."""
        out: dict[str, Any] = {
            "AppIntentDescriptor": dict(_APP_INTENT_DESCRIPTOR),
        }
        if self.audio_file is not None:
            out["audioFile"] = coerce_value(self.audio_file)
        return out
