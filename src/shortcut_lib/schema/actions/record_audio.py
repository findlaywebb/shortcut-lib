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
    """Record Audio — record audio from the device microphone.

    Wraps ``is.workflow.actions.recordaudio``. Opens the in-app audio
    recorder and returns the captured audio file when recording stops.

    Args:
        start: When recording begins (``WFRecordingStart``). One of:

            - ``"Immediately"`` (default) — recording starts as soon as
              the action runs; no user interaction needed before capture.
            - ``"On Tap"`` — displays the recorder UI and waits for the
              user to tap the record button.

    Returns:
        The recorded audio file (output name: "Recording").

    Quirks:
        Jellycore lists additional parameters (``quality``, ``end``,
        ``WFRecordingTimeInterval``) that do not appear in any decoded
        corpus sample. They are omitted here; use
        :class:`~shortcut_lib.schema.base.RawAction` if you need them.

    Sample citation:
        samples/decoded/dictionary.xml:1531 — ``WFRecordingStart:
        Immediately`` (default mode).
    """

    identifier: ClassVar[str] = "is.workflow.actions.recordaudio"
    default_output_name: ClassVar[str] = "Recording"

    start: str = _DEFAULT_START

    def _params(self) -> dict[str, Any]:
        """Return the WF parameter dict for this record-audio action."""
        return {"WFRecordingStart": self.start}
