"""TextReplace — find-and-replace within a text value."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

from shortcut_lib.schema.base import (
    Action,
    ParamValue,
    coerce_text_field,
)
from shortcut_lib.schema.registry import register


@register
@dataclass
class TextReplace(Action):
    """Replace Text — find-and-replace within a text value.

    Wraps ``is.workflow.actions.text.replace``. Scans ``input`` for all
    occurrences of ``find`` and replaces them with ``replace``, returning
    the modified string.

    Args:
        input: The source text to search within (``WFInput``). Accepts a
            plain string, a :class:`~shortcut_lib.schema.values.Text`
            template, or any :class:`~shortcut_lib.schema.base.Action` /
            :class:`~shortcut_lib.schema.base.Value`. This slot is a
            ``WFTextTokenString`` in the corpus — bare
            ``WFTextTokenAttachment`` is not used. Omitted when ``None``.
        find: The search string or regex pattern
            (``WFReplaceTextFind``). Defaults to ``""``; omitted from the
            plist when empty (Apple's convention for an unconfigured action).
        replace: The replacement string (``WFReplaceTextReplace``).
            Defaults to ``""``; omitted when empty.
        case_sensitive: If explicitly set, emits
            ``WFReplaceTextCaseSensitive``. ``None`` omits the key —
            Apple's default is case-sensitive (``True``).
        regex: If ``True``, ``find`` is interpreted as a regex pattern
            (``WFReplaceTextRegularExpression``). ``None`` omits the key
            — Apple's default is plain-text matching.

    Returns:
        The text with all replacements applied (output name: "Updated Text").

    Sample citations:
        samples/decoded/rename_files.xml:17 — WFInput as single-attachment
        WFTextTokenString.
        samples/decoded/dictionary.xml:42 — unconfigured form (no find/replace
        keys emitted).
    """

    identifier: ClassVar[str] = "is.workflow.actions.text.replace"
    default_output_name: ClassVar[str] = "Updated Text"

    input: ParamValue = None
    find: ParamValue = field(default="")
    replace: ParamValue = field(default="")
    case_sensitive: bool | None = None
    regex: bool | None = None

    def _params(self) -> dict[str, Any]:
        """Return the WFReplaceText* parameter dict."""
        out: dict[str, Any] = {}
        if self.input is not None:
            # WFInput is a WFTextTokenString slot in the corpus — all 5 sample
            # observations in rename_files.xml and dictionary.xml use a
            # single-attachment WFTextTokenString, not WFTextTokenAttachment.
            # Confirmed: samples/decoded/rename_files.xml:17 and
            # samples/decoded/dictionary.xml:42.
            out["WFInput"] = coerce_text_field(self.input)
        # Find/Replace are WFTextTokenString slots when not bare literals;
        # route variable refs through coerce_text_field for the right envelope.
        # Apple omits both keys when the value is an empty string (the demo /
        # unconfigured shape in samples/decoded/dictionary.xml:42); honour that.
        if self.find != "":
            out["WFReplaceTextFind"] = coerce_text_field(self.find)
        if self.replace != "":
            out["WFReplaceTextReplace"] = coerce_text_field(self.replace)
        if self.case_sensitive is not None:
            out["WFReplaceTextCaseSensitive"] = self.case_sensitive
        if self.regex is not None:
            out["WFReplaceTextRegularExpression"] = self.regex
        return out
