"""GetVariable — re-fetch a previously set named variable into the data flow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action, SchemaError
from shortcut_lib.schema.registry import register
from shortcut_lib.schema.values import NamedVar


@register
@dataclass
class GetVariable(Action):
    """Get Variable — read a named variable into the action pipeline.

    Wraps ``is.workflow.actions.getvariable``. Emits the named variable
    as a ``WFTextTokenAttachment`` envelope under the ``WFVariable`` key.

    Most action parameter slots accept a
    :class:`~shortcut_lib.schema.values.NamedVar` directly, so an explicit
    GetVariable is only needed when the next action's input is a positional
    magic-variable slot (i.e. the action reads its input from the
    pipeline rather than from a named parameter field).

    Args:
        name: The Shortcuts variable name to retrieve (``WFVariable``).
            Raises :class:`~shortcut_lib.schema.base.SchemaError` if empty.
            Emitted as a ``WFTextTokenAttachment`` via
            :class:`~shortcut_lib.schema.values.NamedVar`.

    Returns:
        The variable's value (output name: "Variable").

    Sample citation:
        samples/decoded/dictionary.xml:141 — GetVariable following SetVariable.
    """

    name: str = ""

    identifier: ClassVar[str] = "is.workflow.actions.getvariable"
    default_output_name: ClassVar[str] = "Variable"

    def _params(self) -> dict[str, Any]:
        if not self.name:
            raise SchemaError("GetVariable requires `name`")
        return {"WFVariable": NamedVar(self.name).to_param()}
