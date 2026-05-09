"""Writing Tools AppIntent actions (iOS 26+).

Five actions that share the ``com.apple.WritingTools.WritingToolsAppIntentsExtension``
namespace and the camelCase ``text`` parameter pattern:

- :class:`AdjustTone` — rewrites text in a target tone.
- :class:`FormatList` — converts free-form text to a structured list.
- :class:`RewriteText` — improves clarity and grammar of input text.
- :class:`SummarizeText` — generates a summary; with ``summary_type=
  "createKeyPoints"`` produces a bullet list instead of a paragraph.

Unlike :class:`shortcut_lib.schema.actions.transcribe_audio.TranscribeAudio`,
these AppIntents don't emit an ``AppIntentDescriptor`` dict in the wire
format — verified against the ``intelly.shortcut`` sample.

All accept a ``text`` parameter (string, Text template, or Output) and
emit it as a bare ``text`` key (camelCase, AppIntent convention).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Literal, get_args

from shortcut_lib.schema.base import Action, ParamValue, SchemaError, coerce_value
from shortcut_lib.schema.registry import register

# Apple's Writing Tools tone values observed in samples and Apple UI (iOS 26+).
# Only "professional" is confirmed from intelly.shortcut; the remaining three are
# the other tones shown in the Writing Tools picker. Add here if more are
# discovered in wild samples.
WFAdjustTone = Literal["friendly", "professional", "concise", "casual"]
_VALID_TONES: frozenset[str] = frozenset(get_args(WFAdjustTone))


def _text_param(text: Any) -> dict[str, Any]:
    if text is None:
        raise SchemaError("Writing Tools actions require `text`")
    out: dict[str, Any] = {}
    out["text"] = coerce_value(text)
    return out


@register
@dataclass
class AdjustTone(Action):
    """Adjust Tone — rewrite text in a specified tone using Writing Tools.

    Wraps ``com.apple.WritingTools.WritingToolsAppIntentsExtension.AdjustToneIntent``
    (iOS 26+). Uses Apple Writing Tools to recast the input text in the
    requested tone without changing its core meaning.

    Unlike :class:`~shortcut_lib.schema.actions.transcribe_audio.TranscribeAudio`,
    no ``AppIntentDescriptor`` dict is emitted — verified against
    ``samples/decoded/intelly.xml:94``.

    Args:
        text: The text to rewrite (``text`` — camelCase AppIntent key).
            Required; raises :class:`~shortcut_lib.schema.base.SchemaError`
            if ``None``. Pass a plain string, a
            :class:`~shortcut_lib.schema.values.Text` template, or any
            :class:`~shortcut_lib.schema.base.Action` /
            :class:`~shortcut_lib.schema.base.Value`.
        tone: The target tone (``tone``). One of ``"friendly"``,
            ``"professional"``, ``"concise"``, ``"casual"``. Defaults to
            ``"professional"``. Only ``"professional"`` is confirmed from
            corpus; the others are the remaining Writing Tools picker
            options. Raises
            :class:`~shortcut_lib.schema.base.SchemaError` for unknown values.

    Returns:
        The rewritten text (output name: "Adjusted Text").

    Sample citation:
        samples/decoded/intelly.xml:94 — ``tone: professional``, ``text``
        from a prior action output.
    """

    text: ParamValue = None
    tone: WFAdjustTone = "professional"

    identifier: ClassVar[str] = (
        "com.apple.WritingTools.WritingToolsAppIntentsExtension.AdjustToneIntent"
    )
    default_output_name: ClassVar[str] = "Adjusted Text"

    def __post_init__(self) -> None:
        if self.tone not in _VALID_TONES:
            raise SchemaError(
                f"AdjustTone.tone {self.tone!r} is not valid. "
                f"Expected one of: {sorted(_VALID_TONES)}"
            )

    def _params(self) -> dict[str, Any]:
        out = _text_param(self.text)
        out["tone"] = self.tone
        return out


@register
@dataclass
class FormatList(Action):
    """Format into List — convert free-form text into a structured list.

    Wraps ``com.apple.WritingTools.WritingToolsAppIntentsExtension.FormatListIntent``
    (iOS 26+). Uses Apple Writing Tools to parse bullet points, numbered
    items, or free prose from the input and return a structured list.

    No ``AppIntentDescriptor`` dict is emitted — verified against
    ``samples/decoded/intelly.xml:107``.

    Args:
        text: The source text to convert (``text`` — camelCase AppIntent
            key). Required; raises
            :class:`~shortcut_lib.schema.base.SchemaError` if ``None``.

    Returns:
        The formatted list text (output name: "Formatted List").

    Sample citation:
        samples/decoded/intelly.xml:107 — ``text`` from a prior output.
    """

    text: ParamValue = None

    identifier: ClassVar[str] = (
        "com.apple.WritingTools.WritingToolsAppIntentsExtension.FormatListIntent"
    )
    default_output_name: ClassVar[str] = "Formatted List"

    def _params(self) -> dict[str, Any]:
        return _text_param(self.text)


@register
@dataclass
class RewriteText(Action):
    """Rewrite — improve the clarity and grammar of input text.

    Wraps ``com.apple.WritingTools.WritingToolsAppIntentsExtension.RewriteTextIntent``
    (iOS 26+). Uses Apple Writing Tools to clean up phrasing, fix
    grammatical errors, and improve readability without changing meaning.

    No ``AppIntentDescriptor`` dict is emitted — verified against
    ``samples/decoded/intelly.xml:118``.

    Args:
        text: The text to rewrite (``text`` — camelCase AppIntent key).
            Required; raises
            :class:`~shortcut_lib.schema.base.SchemaError` if ``None``.

    Returns:
        The rewritten text (output name: "Rewritten Text").

    Sample citation:
        samples/decoded/intelly.xml:118 — ``text`` from a prior output.
    """

    text: ParamValue = None

    identifier: ClassVar[str] = (
        "com.apple.WritingTools.WritingToolsAppIntentsExtension.RewriteTextIntent"
    )
    default_output_name: ClassVar[str] = "Rewritten Text"

    def _params(self) -> dict[str, Any]:
        return _text_param(self.text)


@register
@dataclass
class SummarizeText(Action):
    """Summarize — distil input text into a shorter summary.

    Wraps ``com.apple.WritingTools.WritingToolsAppIntentsExtension.SummarizeTextIntent``
    (iOS 26+). Uses Apple Writing Tools to produce a condensed version of
    the input. The default output is a prose paragraph; pass
    ``summary_type="createKeyPoints"`` for a bullet-point list instead.

    No ``AppIntentDescriptor`` dict is emitted — verified against
    ``samples/decoded/intelly.xml:129``.

    Args:
        text: The text to summarise (``text`` — camelCase AppIntent key).
            Required; raises
            :class:`~shortcut_lib.schema.base.SchemaError` if ``None``.
        summary_type: Controls the output format (``summaryType``).
            ``None`` omits the key — Apple defaults to a prose paragraph.
            Pass ``"createKeyPoints"`` for a bullet list. Other values
            are not confirmed from corpus samples.

    Returns:
        The summary text (output name: "Summary").

    Sample citations:
        samples/decoded/intelly.xml:129 — default paragraph summary (no
        summaryType key).
        samples/decoded/intelly.xml:140 — ``summaryType: createKeyPoints``.
    """

    text: ParamValue = None
    summary_type: str | None = None

    identifier: ClassVar[str] = (
        "com.apple.WritingTools.WritingToolsAppIntentsExtension.SummarizeTextIntent"
    )
    default_output_name: ClassVar[str] = "Summary"

    def _params(self) -> dict[str, Any]:
        out = _text_param(self.text)
        if self.summary_type is not None:
            out["summaryType"] = self.summary_type
        return out
