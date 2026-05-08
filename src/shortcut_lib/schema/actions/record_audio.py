"""RecordAudio — record audio from the device microphone."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action
from shortcut_lib.schema.registry import register

# Valid values from Apple's UI: "Immediately" or "On Tap".
# "Immediately" starts recording as soon as the action runs;
# "On Tap" waits for the user to tap the record button.
_DEFAULT_START = "Immediately"


@register
@dataclass
class RecordAudio(Action):
    """Record audio from the device microphone.

    Verified against ``samples/decoded/private/voice_note_to_github.xml``.
    Only ``WFRecordingStart`` appears in that sample; additional parameter
    keys (``quality``, ``end``, ``WFRecordingTimeInterval``) are listed in
    Jellycore but do not appear in any decoded sample, so they are omitted
    here. Pass them via ``RawAction`` if needed.

    Args:
        start: When recording begins. ``"Immediately"`` (default) starts as
            soon as the action runs. ``"On Tap"`` waits for the user.

    Output: the recorded audio file.
    """

    identifier: ClassVar[str] = "is.workflow.actions.recordaudio"
    default_output_name: ClassVar[str] = "Recording"

    start: str = _DEFAULT_START

    def _params(self) -> dict[str, Any]:
        """Return the WF parameter dict for this record-audio action."""
        return {"WFRecordingStart": self.start}
