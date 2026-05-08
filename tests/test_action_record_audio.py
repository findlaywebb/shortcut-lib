"""Tests for RecordAudio action schema."""

from __future__ import annotations

import shortcut_lib.schema.actions.record_audio  # noqa: F401 — trigger registration
from shortcut_lib.schema.actions.record_audio import RecordAudio
from shortcut_lib.schema.registry import lookup


def test_record_audio_emits_basic_action() -> None:
    """to_action_dict carries the correct WFWorkflowActionIdentifier."""
    action = RecordAudio()
    d = action.to_action_dict()
    assert d["WFWorkflowActionIdentifier"] == "is.workflow.actions.recordaudio"


def test_record_audio_default_start_is_immediately() -> None:
    """Default start mode matches the voice_note_to_github sample value."""
    action = RecordAudio()
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFRecordingStart"] == "Immediately"


def test_record_audio_custom_start_mode() -> None:
    """A custom start value is emitted as WFRecordingStart."""
    action = RecordAudio(start="On Tap")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFRecordingStart"] == "On Tap"


def test_record_audio_output_name() -> None:
    """output() uses the class default_output_name 'Recording'."""
    action = RecordAudio()
    out = action.output()
    assert out.name == "Recording"


def test_record_audio_registered() -> None:
    """RecordAudio is discoverable in the registry by its identifier."""
    cls = lookup("is.workflow.actions.recordaudio")
    assert cls is RecordAudio
