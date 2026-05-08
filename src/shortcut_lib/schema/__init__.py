"""Typed authoring layer for Apple Shortcuts.

The schema lets you describe a shortcut in Python:

    from shortcut_lib.builder import Shortcut
    from shortcut_lib.schema import DictateText, SetClipboard

    s = Shortcut(name="Dictate to Clipboard")
    text = s.add(DictateText())
    s.add(SetClipboard(input=text))
    s.save_signed("Dictate.shortcut")

Action classes are typed dataclasses. Every Action knows its
``WFWorkflowActionIdentifier`` and how to emit its
``WFWorkflowActionParameters`` dict. Control-flow constructs (If, RepeatEach,
ChooseFromMenu) are flat-encoded with paired open/close markers on emit.

The registry exposes :func:`list_actions` and :func:`describe_action` so an
LLM can introspect available actions and their parameters at runtime.
"""

from __future__ import annotations

# Importing the actions submodule registers leaf-action classes via decorators.
from shortcut_lib.schema import actions as _actions  # noqa: F401
from shortcut_lib.schema.base import Action, SchemaError, Value
from shortcut_lib.schema.compose import RunWorkflow, Self
from shortcut_lib.schema.control import (
    ChooseFromMenu,
    If,
    RepeatCount,
    RepeatEach,
)
from shortcut_lib.schema.registry import (
    describe_action,
    list_actions,
    list_control_flow,
    list_values,
    register,
)
from shortcut_lib.schema.values import (
    Ask,
    Clipboard,
    CurrentDate,
    MagicVar,
    NamedVar,
    Output,
    Quantity,
    RepeatIndex,
    RepeatItem,
    ShortcutInput,
    Text,
    TimeOffset,
)

__all__ = [
    "Action",
    "Ask",
    "ChooseFromMenu",
    "Clipboard",
    "CurrentDate",
    "If",
    "MagicVar",
    "NamedVar",
    "Output",
    "Quantity",
    "RepeatCount",
    "RepeatEach",
    "RepeatIndex",
    "RepeatItem",
    "RunWorkflow",
    "SchemaError",
    "Self",
    "ShortcutInput",
    "Text",
    "TimeOffset",
    "Value",
    "describe_action",
    "list_actions",
    "list_control_flow",
    "list_values",
    "register",
]
