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
    """Find and replace text within an input string.

    Wraps ``is.workflow.actions.text.replace``. The ``find`` and
    ``replace`` fields accept plain strings, :class:`~shortcut_lib.schema.values.Text`
    templates, or any :class:`~shortcut_lib.schema.base.Action` /
    :class:`~shortcut_lib.schema.base.Value` that resolves to a string.

    ``case_sensitive`` and ``regex`` are only emitted when explicitly set;
    leave them ``None`` to rely on Apple's defaults (case-sensitive on,
    regex off).

    Args:
        input: The source text to search within.
        find: The string (or pattern) to find. Defaults to empty string.
        replace: The replacement string. Defaults to empty string.
        case_sensitive: Override Apple's default (True) only when needed.
        regex: When True, ``find`` is interpreted as a regex pattern.
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
        out["WFReplaceTextFind"] = coerce_text_field(self.find)
        out["WFReplaceTextReplace"] = coerce_text_field(self.replace)
        if self.case_sensitive is not None:
            out["WFReplaceTextCaseSensitive"] = self.case_sensitive
        if self.regex is not None:
            out["WFReplaceTextRegularExpression"] = self.regex
        return out
