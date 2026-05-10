"""GetText — produce a text value, optionally with variable substitutions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action, ParamValue, coerce_text_field
from shortcut_lib.schema.registry import register


@register
@dataclass
class GetText(Action):
    """Text — produce a text value from a literal or template expression.

    Wraps ``is.workflow.actions.gettext`` (displayed as "Text" in the
    Shortcuts editor). Constructs a text string and passes it downstream.

    The ``WFTextActionText`` parameter accepts a plain ``str``, a
    ``WFTextTokenString`` (templated text with variable substitutions),
    or a ``WFTextTokenAttachment`` (single output reference). Pass a
    :class:`str` for literals, a :class:`~shortcut_lib.schema.values.Text`
    for templates, or any :class:`~shortcut_lib.schema.base.Action` /
    :class:`~shortcut_lib.schema.base.Value` for single-variable injection.

    Args:
        text: The text to produce (``WFTextActionText``). Defaults to an
            empty string. Variable references are wrapped as a
            single-attachment ``WFTextTokenString`` via
            :func:`~shortcut_lib.schema.base.coerce_text_field`.

    Returns:
        The constructed text string (output name: "Text").

    Sample citation:
        samples/decoded/daily_standup.xml:72 — WFTextTokenString with
        embedded variable substitutions.
    """

    identifier: ClassVar[str] = "is.workflow.actions.gettext"
    default_output_name: ClassVar[str] = "Text"

    text: ParamValue = field(default="")

    def _params(self) -> dict[str, Any]:
        """Return the WFTextActionText parameter dict."""
        # WFTextActionText is a WFTextTokenString slot; bare WFTextTokenAttachment
        # imports as a disconnected field. Plain strings pass through unchanged.
        return {"WFTextActionText": coerce_text_field(self.text)}
