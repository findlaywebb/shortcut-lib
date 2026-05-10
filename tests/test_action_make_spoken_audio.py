"""Tests for MakeSpokenAudio action schema."""

from __future__ import annotations

import shortcut_lib.schema.actions.make_spoken_audio  # noqa: F401 — trigger registration
from shortcut_lib.schema.actions.make_spoken_audio import MakeSpokenAudio
from shortcut_lib.schema.registry import lookup
from shortcut_lib.schema.values import NamedVar, Text

# ---------------------------------------------------------------------------
# Identifier and output name
# ---------------------------------------------------------------------------


def test_identifier() -> None:
    """Action carries the expected Apple identifier."""
    action = MakeSpokenAudio(text="Hello world")
    d = action.to_action_dict()
    assert (
        d["WFWorkflowActionIdentifier"] == "is.workflow.actions.makespokenaudiofromtext"
    )


def test_default_output_name() -> None:
    """default_output_name matches the OutputName seen in corpus samples."""
    action = MakeSpokenAudio(text="Hello")
    assert action.output().name == "Spoken Audio"


# ---------------------------------------------------------------------------
# WFInput — WFTextTokenString slot
# ---------------------------------------------------------------------------


def test_plain_string_text() -> None:
    """Plain string text lands in WFInput as a bare string."""
    action = MakeSpokenAudio(text="Speak this aloud.")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFInput"] == "Speak this aloud."


def test_empty_string_omits_wfinput() -> None:
    """Empty string default omits the WFInput key entirely."""
    action = MakeSpokenAudio()
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "WFInput" not in params


def test_named_var_wraps_as_token_string() -> None:
    """NamedVar in text slot is wrapped as a WFTextTokenString envelope.

    Both corpus samples carry WFTextTokenString envelopes for WFInput
    (observed_envelope_types.json .slots[identifier][WFInput]).
    """
    var = NamedVar("Transcribed Text")
    action = MakeSpokenAudio(text=var)
    params = action.to_action_dict()["WFWorkflowActionParameters"]

    wfinput = params["WFInput"]
    assert wfinput["WFSerializationType"] == "WFTextTokenString"
    inner = wfinput["Value"]
    assert "string" in inner
    assert "attachmentsByRange" in inner
    assert "￼" in inner["string"]

    attachment = next(iter(inner["attachmentsByRange"].values()))
    assert attachment["Type"] == "Variable"
    assert attachment["VariableName"] == "Transcribed Text"


def test_action_output_wraps_as_token_string() -> None:
    """Action output chained into text is wrapped as WFTextTokenString.

    Matches dictionary.xml where a TranscribeAudio output feeds WFInput.
    """
    upstream = MakeSpokenAudio(text="seed", uuid="BBEC9101-CCB1-4338-97A3-E2548083D77D")
    action = MakeSpokenAudio(text=upstream)
    params = action.to_action_dict()["WFWorkflowActionParameters"]

    wfinput = params["WFInput"]
    assert wfinput["WFSerializationType"] == "WFTextTokenString"
    inner = wfinput["Value"]
    assert inner["attachmentsByRange"]["{0, 1}"]["OutputUUID"] == (
        "BBEC9101-CCB1-4338-97A3-E2548083D77D"
    )


def test_templated_text_input() -> None:
    """Text(...) template in the text slot renders as WFTextTokenString."""
    var = NamedVar("Note")
    body = Text("Summary: {v}", substitutions={"v": var})
    action = MakeSpokenAudio(text=body)
    params = action.to_action_dict()["WFWorkflowActionParameters"]

    wfinput = params["WFInput"]
    assert wfinput["WFSerializationType"] == "WFTextTokenString"
    assert "attachmentsByRange" in wfinput["Value"]


# ---------------------------------------------------------------------------
# WFSpeakTextVoice — bare string (observed in turn_text_into_audio.xml)
# ---------------------------------------------------------------------------


def test_voice_emitted_as_bare_string() -> None:
    """WFSpeakTextVoice is emitted as a plain string, not a token envelope."""
    action = MakeSpokenAudio(
        text="Hello",
        voice="com.apple.speech.synthesis.voice.Alex",
    )
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFSpeakTextVoice"] == "com.apple.speech.synthesis.voice.Alex"


def test_voice_none_omits_key() -> None:
    """When voice=None (default), WFSpeakTextVoice is absent from params."""
    action = MakeSpokenAudio(text="Hello")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "WFSpeakTextVoice" not in params


# ---------------------------------------------------------------------------
# Jellycore-known but corpus-absent parameters
# ---------------------------------------------------------------------------


def test_language_emitted_when_set() -> None:
    """language emits the 'language' key (Jellycore-listed, not corpus-observed)."""
    action = MakeSpokenAudio(text="Bonjour", language="fr-FR")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["language"] == "fr-FR"


def test_language_none_omits_key() -> None:
    """language=None (default) omits the 'language' key."""
    action = MakeSpokenAudio(text="Hello")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "language" not in params


def test_pitch_emitted_when_set() -> None:
    """WFSpeakTextPitch is emitted as a float when set."""
    action = MakeSpokenAudio(text="Hello", pitch=1.2)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFSpeakTextPitch"] == 1.2


def test_pitch_none_omits_key() -> None:
    """pitch=None (default) omits WFSpeakTextPitch."""
    action = MakeSpokenAudio(text="Hello")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "WFSpeakTextPitch" not in params


def test_rate_emitted_when_set() -> None:
    """WFSpeakTextRate is emitted as a float when set."""
    action = MakeSpokenAudio(text="Hello", rate=0.5)
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFSpeakTextRate"] == 0.5


def test_rate_none_omits_key() -> None:
    """rate=None (default) omits WFSpeakTextRate."""
    action = MakeSpokenAudio(text="Hello")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert "WFSpeakTextRate" not in params


# ---------------------------------------------------------------------------
# Wire-format equivalence — turn_text_into_audio.xml corpus sample
# ---------------------------------------------------------------------------


def test_wire_format_voice_sample() -> None:
    """Reconstruct the turn_text_into_audio.xml appearance (ExtensionInput omitted).

    The corpus sample sets WFInput (WFTextTokenString, ExtensionInput type)
    and WFSpeakTextVoice. We reconstruct it without the ExtensionInput magic
    variable (not yet modelled) and verify the voice and structure shape.
    """
    action = MakeSpokenAudio(
        text="Hello",  # placeholder — ExtensionInput not yet modelled
        voice="com.apple.speech.synthesis.voice.Alex",
        uuid="B92FA945-4EF4-4B13-9A6D-7A4B43BCA1A3",
    )
    d = action.to_action_dict()
    assert d["WFWorkflowActionIdentifier"] == (
        "is.workflow.actions.makespokenaudiofromtext"
    )
    params = d["WFWorkflowActionParameters"]
    assert params["UUID"] == "B92FA945-4EF4-4B13-9A6D-7A4B43BCA1A3"
    assert params["WFSpeakTextVoice"] == "com.apple.speech.synthesis.voice.Alex"


def test_wire_format_chained_action_sample() -> None:
    """Reconstruct the dictionary.xml appearance (ActionOutput input, no voice).

    The corpus sample chains a TranscribeAudio output into WFInput via a
    WFTextTokenString envelope. We simulate with a MakeSpokenAudio upstream.
    """
    upstream = MakeSpokenAudio(text="seed", uuid="BBEC9101-CCB1-4338-97A3-E2548083D77D")
    action = MakeSpokenAudio(text=upstream)
    params = action.to_action_dict()["WFWorkflowActionParameters"]

    # No voice in this corpus appearance
    assert "WFSpeakTextVoice" not in params

    # WFInput is a WFTextTokenString wrapping an ActionOutput reference
    wfinput = params["WFInput"]
    assert wfinput["WFSerializationType"] == "WFTextTokenString"
    attachment = wfinput["Value"]["attachmentsByRange"]["{0, 1}"]
    assert attachment["Type"] == "ActionOutput"
    assert attachment["OutputUUID"] == "BBEC9101-CCB1-4338-97A3-E2548083D77D"


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_registered() -> None:
    """MakeSpokenAudio is discoverable via the registry by its identifier."""
    cls = lookup("is.workflow.actions.makespokenaudiofromtext")
    assert cls is MakeSpokenAudio


# ---------------------------------------------------------------------------
# All-options combined
# ---------------------------------------------------------------------------


def test_all_options_combined() -> None:
    """All fields emitted correctly when set simultaneously."""
    action = MakeSpokenAudio(
        text="Good morning.",
        voice="com.apple.speech.synthesis.voice.Samantha",
        language="en-US",
        pitch=1.1,
        rate=0.6,
        uuid="AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE",
    )
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFInput"] == "Good morning."
    assert params["WFSpeakTextVoice"] == "com.apple.speech.synthesis.voice.Samantha"
    assert params["language"] == "en-US"
    assert params["WFSpeakTextPitch"] == 1.1
    assert params["WFSpeakTextRate"] == 0.6
    assert params["UUID"] == "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE"
