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
    """Read a named variable into the next action's input slot.

    Most parameters accept a :class:`NamedVar` directly, so an explicit
    GetVariable is only needed when the next action's input is a positional
    Magic Variable slot rather than a named parameter.
    """

    name: str = ""

    identifier: ClassVar[str] = "is.workflow.actions.getvariable"
    default_output_name: ClassVar[str] = "Variable"

    def _params(self) -> dict[str, Any]:
        if not self.name:
            raise SchemaError("GetVariable requires `name`")
        return {"WFVariable": NamedVar(self.name).to_param()}
