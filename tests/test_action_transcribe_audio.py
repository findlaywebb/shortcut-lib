"""Tests for TranscribeAudio action schema."""

from __future__ import annotations

import shortcut_lib.schema.actions.transcribe_audio  # noqa: F401 — trigger registration
from shortcut_lib.schema.actions.record_audio import RecordAudio
from shortcut_lib.schema.actions.transcribe_audio import TranscribeAudio
from shortcut_lib.schema.registry import lookup
from shortcut_lib.schema.values import NamedVar


def test_transcribe_audio_emits_correct_identifier() -> None:
    """to_action_dict carries the AppIntent-style identifier."""
    action = TranscribeAudio()
    d = action.to_action_dict()
    assert (
        d["WFWorkflowActionIdentifier"]
        == "com.apple.ShortcutsActions.TranscribeAudioAction"
    )


def test_transcribe_audio_app_intent_descriptor_present() -> None:
    """AppIntentDescriptor is emitted verbatim, copied from sample XML."""
    action = TranscribeAudio()
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    desc = params["AppIntentDescriptor"]
    assert desc["AppIntentIdentifier"] == "TranscribeAudioAction"
    assert desc["BundleIdentifier"] == "com.apple.ShortcutsActions"
    assert desc["Name"] == "ShortcutsActions"
    assert desc["TeamIdentifier"] == "0000000000"


def test_transcribe_audio_with_named_var() -> None:
    """audioFile is coerced from a NamedVar into a WFTextTokenAttachment."""
    action = TranscribeAudio(audio_file=NamedVar("Audio"))
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "audioFile" in params
    token = params["audioFile"]
    assert token["WFSerializationType"] == "WFTextTokenAttachment"
    assert token["Value"]["Type"] == "Variable"
    assert token["Value"]["VariableName"] == "Audio"


def test_transcribe_audio_with_action_output() -> None:
    """audioFile can be set from a RecordAudio action (output chaining)."""
    record = RecordAudio(uuid="FIXED-UUID-0000-0000-0000-000000000001")
    action = TranscribeAudio(audio_file=record)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    token = params["audioFile"]
    assert token["WFSerializationType"] == "WFTextTokenAttachment"
    assert token["Value"]["OutputUUID"] == "FIXED-UUID-0000-0000-0000-000000000001"


def test_transcribe_audio_omits_audio_file_when_none() -> None:
    """When audio_file is None, the audioFile key is absent from params."""
    action = TranscribeAudio()
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "audioFile" not in params


def test_transcribe_audio_output_name() -> None:
    """default_output_name matches the OutputName seen in sample setvariable."""
    action = TranscribeAudio()
    out = action.output()
    assert out.name == "Transcribe Audio"


def test_transcribe_audio_registered() -> None:
    """TranscribeAudio is discoverable in the registry by its identifier."""
    cls = lookup("com.apple.ShortcutsActions.TranscribeAudioAction")
    assert cls is TranscribeAudio
