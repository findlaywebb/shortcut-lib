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
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action, SchemaError, coerce_value
from shortcut_lib.schema.registry import register

# Apple's Writing Tools tone values observed in samples and Apple UI (iOS 26+).
# Only "professional" is confirmed from intelly.shortcut; the remaining three are
# the other tones shown in the Writing Tools picker. Add here if more are
# discovered in wild samples.
_VALID_TONES: frozenset[str] = frozenset(
    {"friendly", "professional", "concise", "casual"}
)


def _text_param(text: Any) -> dict[str, Any]:
    if text is None:
        raise SchemaError("Writing Tools actions require `text`")
    out: dict[str, Any] = {}
    out["text"] = coerce_value(text)
    return out


@register
@dataclass
class AdjustTone(Action):
    """Rewrite text in a target tone (e.g. "professional", "friendly").

    Apple identifier: ``com.apple.WritingTools.WritingToolsAppIntentsExtension.AdjustToneIntent``.
    """

    text: Any = None
    tone: str = "professional"

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
    """Format free-form text into a structured list.

    Apple identifier: ``com.apple.WritingTools.WritingToolsAppIntentsExtension.FormatListIntent``.
    """

    text: Any = None

    identifier: ClassVar[str] = (
        "com.apple.WritingTools.WritingToolsAppIntentsExtension.FormatListIntent"
    )
    default_output_name: ClassVar[str] = "Formatted List"

    def _params(self) -> dict[str, Any]:
        return _text_param(self.text)


@register
@dataclass
class RewriteText(Action):
    """Improve clarity / grammar of input text.

    Apple identifier: ``com.apple.WritingTools.WritingToolsAppIntentsExtension.RewriteTextIntent``.
    """

    text: Any = None

    identifier: ClassVar[str] = (
        "com.apple.WritingTools.WritingToolsAppIntentsExtension.RewriteTextIntent"
    )
    default_output_name: ClassVar[str] = "Rewritten Text"

    def _params(self) -> dict[str, Any]:
        return _text_param(self.text)


@register
@dataclass
class SummarizeText(Action):
    """Summarise input text. Defaults to a paragraph; pass
    ``summary_type="createKeyPoints"`` for a bullet list.

    Apple identifier: ``com.apple.WritingTools.WritingToolsAppIntentsExtension.SummarizeTextIntent``.
    """

    text: Any = None
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
