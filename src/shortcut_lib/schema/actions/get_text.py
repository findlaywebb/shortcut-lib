"""GetText — produce a text value, optionally with variable substitutions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action, coerce_value
from shortcut_lib.schema.registry import register


@register
@dataclass
class GetText(Action):
    """Produce a text value from a literal string or templated expression.

    The Apple parameter ``WFTextActionText`` accepts a plain string, a
    ``WFTextTokenString`` (templated text with variable substitutions), or a
    ``WFTextTokenAttachment`` (single output reference). Pass a :class:`str`
    for literals, a :class:`~shortcut_lib.schema.values.Text` for templates,
    or any :class:`~shortcut_lib.schema.base.Action` /
    :class:`~shortcut_lib.schema.base.Value` for single references.

    Args:
        text: The text to produce. Defaults to an empty string.
    """

    identifier: ClassVar[str] = "is.workflow.actions.gettext"
    default_output_name: ClassVar[str] = "Text"

    text: Any = field(default="")

    def _params(self) -> dict[str, Any]:
        """Return the WFTextActionText parameter dict."""
        return {"WFTextActionText": coerce_value(self.text)}
