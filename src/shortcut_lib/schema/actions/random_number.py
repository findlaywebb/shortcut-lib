"""RandomNumber — produce a random integer within a range."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action, ParamValue, coerce_value
from shortcut_lib.schema.registry import register


@register
@dataclass
class RandomNumber(Action):
    """Produce a random integer between a minimum and maximum (inclusive).

    Apple display name: **Random Number**
    Identifier: ``is.workflow.actions.number.random``
    Minimum host: iOS 14

    This action generates a uniformly random integer each time the shortcut
    runs. The result is an integer in the closed interval
    ``[minimum, maximum]``. Apple's UI exposes two numeric fields —
    *Minimum* and *Maximum* — and defaults both to unset (corpus samples
    carry no bound keys at all, so Apple falls back to its built-in
    defaults, which appear to be 0 and 100 based on the Shortcuts.app
    interface).

    The output name observed in downstream ``round`` action references
    within the corpus is ``"Random Number"`` (confirmed at
    ``dictionary.xml`` lines 314 and 4592), which matches Apple's display
    name exactly and is exposed as :attr:`default_output_name`.

    Args:
        minimum: Lower bound (inclusive). Pass an ``int``, ``float``, or
            any :class:`~shortcut_lib.schema.base.ParamValue`. Defaults to
            ``None``, which omits the ``WFRandomNumberMinimum`` key and
            lets Apple use its built-in lower bound.
        maximum: Upper bound (inclusive). Same type rules as ``minimum``.
            Defaults to ``None``, omitting ``WFRandomNumberMaximum``.

    Returns:
        A magic variable whose output name is ``"Random Number"``.
        Reference it with ``action.output()`` to chain into subsequent
        actions (e.g. ``Round``, ``Format Number``).

    Corpus notes:
        Both corpus appearances (``dictionary.xml`` lines 295 and 4573)
        carry only a ``UUID`` key — neither ``WFRandomNumberMinimum`` nor
        ``WFRandomNumberMaximum`` is present. To reproduce that wire
        format exactly, leave both bounds at their default of ``None``.

        Jellycore (``data/jellycore_facts.json``) lists this action as an
        array entry with display name ``"Random Number"`` and parameter
        keys ``WFRandomNumberMinimum`` / ``WFRandomNumberMaximum``. The
        top-level JSON lookup returns ``null`` because the facts file is
        stored as an array, not a keyed map.
    """

    identifier: ClassVar[str] = "is.workflow.actions.number.random"
    default_output_name: ClassVar[str] = "Random Number"

    minimum: ParamValue = field(default=None)
    maximum: ParamValue = field(default=None)

    def _params(self) -> dict[str, Any]:
        """Return bound parameters, omitting any key whose value is None.

        Omitting a key reproduces the corpus wire format and lets Apple
        apply its built-in defaults at runtime.
        """
        params: dict[str, Any] = {}
        if self.minimum is not None:
            params["WFRandomNumberMinimum"] = coerce_value(self.minimum)
        if self.maximum is not None:
            params["WFRandomNumberMaximum"] = coerce_value(self.maximum)
        return params
