"""Number — produce a literal numeric value."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action, ParamValue, coerce_value
from shortcut_lib.schema.registry import register


@register
@dataclass
class Number(Action):
    """Produce a literal numeric value in a shortcut.

    Apple display name: **Number**
    Identifier: ``is.workflow.actions.number``
    Minimum host: iOS 14

    This action places a single hardcoded number into the shortcut's data
    flow. It is the numeric equivalent of the "Text" action: no computation
    is performed; the value passes through as-is for downstream actions.

    In the corpus both appearances carry no ``WFNumberActionNumber`` key —
    the parameter is absent and Apple defaults to 0. Omit ``number`` (or
    leave it at its default of ``None``) to reproduce the same wire format.

    Args:
        number: The numeric literal to emit. Pass an ``int``, ``float``,
            or any :class:`~shortcut_lib.schema.base.ParamValue` (e.g. an
            action output or variable reference). Defaults to ``None``,
            which omits the key and lets Apple use its built-in default
            (0). Pass ``0`` explicitly to write the key with value ``0``.

    Returns:
        A magic variable whose output name is ``"Number"``. The output
        name is **inferred from Apple's display name** ("Number" per
        jellycore); the corpus does not confirm it because both `Number`
        action UUIDs in the samples are dead branches — never referenced
        downstream as an `OutputUUID`.

    Corpus notes:
        Both corpus appearances (``dictionary.xml`` lines 286 and 4564)
        carry only a ``UUID`` key — ``WFNumberActionNumber`` is absent.
        The action is always followed by a ``number.random`` step in the
        same sample, suggesting these are placeholder defaults.
    """

    identifier: ClassVar[str] = "is.workflow.actions.number"
    default_output_name: ClassVar[str] = "Number"

    number: ParamValue = field(default=None)

    def _params(self) -> dict[str, Any]:
        """Return the WFNumberActionNumber parameter dict.

        Omits the key when ``number`` is ``None`` to match corpus wire
        format (both samples carry no explicit value).
        """
        if self.number is None:
            return {}
        return {"WFNumberActionNumber": coerce_value(self.number)}
