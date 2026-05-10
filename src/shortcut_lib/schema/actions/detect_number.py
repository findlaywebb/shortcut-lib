"""DetectNumber — extract numbers from text in Shortcuts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action, ParamValue, coerce_value
from shortcut_lib.schema.registry import register


@register
@dataclass
class DetectNumber(Action):
    """Extract numbers from text input.

    Apple display name: **Get Numbers from Input**
    Identifier: ``is.workflow.actions.detect.number``
    Minimum host: iOS 14

    Scans a text (or any Shortcut Input) for numeric values and returns
    them as a list of numbers. The action mirrors the pattern of other
    ``is.workflow.actions.detect.*`` actions: it takes a single ``WFInput``
    parameter and carries no additional configuration keys.

    Args:
        input: Text to extract numbers from. Pass an
            :class:`~shortcut_lib.schema.base.Action` whose output is text,
            a :class:`~shortcut_lib.schema.base.Value`, or any scalar.
            Corresponds to the ``WFInput`` wire key. Emitted as a
            ``WFTextTokenAttachment`` envelope when given an Action or
            Output reference. Omitted when ``None`` (action runs against
            Shortcut Input at runtime).
            Confirmed wire key: corpus ``samples/decoded/dictionary.xml``
            lines 355-368 and 4546-4559.

    Returns:
        A list of numbers extracted from the input. Reference via
        ``detect_number.output()`` in subsequent actions.

    Quirks:
        - No additional parameters beyond ``WFInput``. Both corpus
          appearances contain only the ``WFInput`` key (plus ``UUID``).
          Jellycore parameter_keys: ``["WFInput"]``.
        - ``WFInput`` uses a bare ``WFTextTokenAttachment`` envelope (not
          ``WFTextTokenString``), consistent with the sibling
          ``is.workflow.actions.detect.*`` family.
    """

    identifier: ClassVar[str] = "is.workflow.actions.detect.number"
    default_output_name: ClassVar[str] = "Numbers"

    input: ParamValue = field(default=None)

    def _params(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.input is not None:
            out["WFInput"] = coerce_value(self.input)
        return out
