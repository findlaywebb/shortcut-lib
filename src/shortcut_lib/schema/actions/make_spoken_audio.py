"""MakeSpokenAudio — synthesise a spoken-audio file from text (TTS)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action, ParamValue, coerce_text_field
from shortcut_lib.schema.registry import register


@register
@dataclass
class MakeSpokenAudio(Action):
    """Synthesise a spoken-audio file from text using device TTS.

    Apple identifier: ``is.workflow.actions.makespokenaudiofromtext``
    Display name: *Make Spoken Audio from Text*
    Minimum host: iOS 15

    The action converts a text value to an audio file that can be saved,
    shared, or passed to subsequent actions (e.g. *Preview Document*).

    **Parameter evidence**

    Corpus (2 samples — ``dictionary.xml``, ``turn_text_into_audio.xml``):

    * ``WFInput`` — the text to speak.  Both samples carry a
      ``WFTextTokenString`` envelope (``observed_envelope_types.json``
      ``.slots["is.workflow.actions.makespokenaudiofromtext"]["WFInput"]``),
      so this slot is wrapped via :func:`~shortcut_lib.schema.base.coerce_text_field`.
      In ``turn_text_into_audio.xml`` the slot holds an ``ExtensionInput``
      (share-sheet passthrough). In ``dictionary.xml`` it holds an
      ``ActionOutput`` reference chained from *Transcribe Audio*.

    * ``WFSpeakTextVoice`` — voice identifier string (bare string,
      confirmed by ``observed_envelope_types.json``
      ``.bare_string_slots["is.workflow.actions.makespokenaudiofromtext"]``).
      The only corpus value is ``"com.apple.speech.synthesis.voice.Alex"``
      (``turn_text_into_audio.xml``); other Apple voice IDs follow the same
      ``com.apple.speech.synthesis.voice.<Name>`` convention. ``None`` omits
      the key and lets the device choose the system default.

    **Jellycore-known but corpus-absent parameters**

    Jellycore lists three additional keys (confirmed with
    ``jq '.actions[] | select(.identifier ==
    "is.workflow.actions.makespokenaudiofromtext")' data/jellycore_facts.json``):

    * ``language`` — BCP-47 locale string (e.g. ``"en-US"``). Not observed
      in any decoded sample. ``None`` omits the key.
    * ``WFSpeakTextPitch`` — float, typically 0.0-2.0. Not observed. ``None``
      omits the key.
    * ``WFSpeakTextRate`` — float, typically 0.0-1.0. Not observed. ``None``
      omits the key.

    All four optional fields default to ``None`` (omit). Pass them only when
    you need to override Apple's defaults explicitly.

    Args:
        text: The text to synthesise into spoken audio. Accept a plain string,
            a :class:`~shortcut_lib.schema.values.Text` template, or any
            :class:`~shortcut_lib.schema.base.Action` /
            :class:`~shortcut_lib.schema.base.Value` whose output is text.
            Wrapped as ``WFTextTokenString`` if a variable reference is
            provided (matches the wire format observed in both corpus samples).
        voice: Apple TTS voice identifier, e.g.
            ``"com.apple.speech.synthesis.voice.Alex"``. Pass ``None`` to use
            the system-default voice. Emitted as a bare string.
        language: BCP-47 locale string for the speech language, e.g.
            ``"en-US"``. Jellycore-listed but never observed in corpus.
            Pass ``None`` to omit (device default).
        pitch: Speaking pitch as a float (Apple range: 0.0-2.0). Jellycore-
            listed but never observed in corpus. ``None`` omits the key.
        rate: Speaking rate as a float (Apple range: 0.0-1.0). Jellycore-
            listed but never observed in corpus. ``None`` omits the key.

    Output: the synthesised ``.m4a`` audio file (``Spoken Audio``).
    """

    identifier: ClassVar[str] = "is.workflow.actions.makespokenaudiofromtext"
    default_output_name: ClassVar[str] = "Spoken Audio"

    text: ParamValue = field(default="")
    voice: str | None = None
    language: str | None = None
    pitch: float | None = None
    rate: float | None = None

    def _params(self) -> dict[str, Any]:
        """Return the WF parameter dict for this make-spoken-audio action."""
        out: dict[str, Any] = {}

        # WFInput is a WFTextTokenString slot in both corpus samples.
        # Plain strings are passed through unchanged; variable refs and action
        # outputs are wrapped in a one-attachment WFTextTokenString envelope.
        coerced = coerce_text_field(self.text)
        if coerced != "":
            out["WFInput"] = coerced

        # WFSpeakTextVoice is a bare string (observed_envelope_types bare_string_slots).
        if self.voice is not None:
            out["WFSpeakTextVoice"] = self.voice

        # Jellycore-listed; never observed in corpus — emit only when set.
        if self.language is not None:
            out["language"] = self.language
        if self.pitch is not None:
            out["WFSpeakTextPitch"] = self.pitch
        if self.rate is not None:
            out["WFSpeakTextRate"] = self.rate

        return out
