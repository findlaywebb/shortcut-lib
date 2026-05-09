"""BuildList — build a list literal from individual text items.

Apple identifier: ``is.workflow.actions.list``.
Apple display name: **List**.

The action creates an ordered list of text values that can be passed to
downstream actions such as "Choose From List", "Repeat With Each", or
"Get Item from List". Think of it as a literal ``[]`` constructor in
Shortcuts.

Wire format
-----------
``WFItems`` is a **plain array of strings** — *not* the complex
``WFDictionaryFieldValue``-wrapped structure used by the Dictionary action.
Each item must be a plain string on the wire.

    # samples/decoded/set_weekend_chores.xml (8-item chores list)
    <key>WFItems</key>
    <array>
        <string>Sweeping</string>
        <string>Mopping</string>
        ...
    </array>

    # samples/decoded/dictionary.xml (empty list — WFItems is absent)
    <key>WFWorkflowActionParameters</key>
    <dict>
        <key>UUID</key>
        <string>91A02720-4C60-4126-8E75-6D344924D765</string>
    </dict>

Quirks
------
- **Empty list omits WFItems entirely.** Apple's GUI emits no ``WFItems``
  key when the list has no items; we match that to keep wire-format
  equivalence with GUI-authored shortcuts (confirmed from
  ``samples/decoded/dictionary.xml``).
- **Items are always plain strings on the wire.** Unlike Dictionary, there
  is no per-item type code; every element is serialised as a bare
  ``<string>`` plist value, not a ``WFTextTokenString`` envelope. Variable
  references therefore cannot be individual list items in the current wire
  format — each item must be a Python ``str``.
- **Default output name is "List"** (confirmed from the ``OutputName`` field
  of downstream ``choosefromlist`` and ``repeat.each`` references in both
  corpus samples).

Parameters
----------
items : list[str]
    Ordered list of string values. Each becomes one ``<string>`` element
    in the ``WFItems`` array. Pass ``[]`` (the default) to create an empty
    list action — Shortcuts will show the action with no items added.

Usage example
-------------
::

    from shortcut_lib.schema.actions.list import BuildList
    from shortcut_lib.schema.actions.show_notification import ShowNotification

    chores = BuildList(items=["Sweeping", "Mopping", "Vacuuming"])
    # chores.output() can be passed to ChooseFromList, RepeatEach, etc.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

from shortcut_lib.schema.base import Action, SchemaError
from shortcut_lib.schema.registry import register


@register
@dataclass
class BuildList(Action):
    """Create an ordered list literal from individual text items.

    Apple display name: List (``is.workflow.actions.list``).

    Pass the list to "Choose From List", "Repeat With Each", or
    "Get Item from List". Items must be plain strings — variable references
    cannot appear as individual list elements in Apple's wire format.

    Args:
        items: Ordered string values. Empty list creates an empty List
            action; ``WFItems`` is omitted from the wire envelope in that
            case to match Apple GUI output.

    Example::

        chores = BuildList(items=["Sweeping", "Mopping", "Vacuuming"])
        # Pass chores.output() to ChooseFromList as its WFInput.
    """

    identifier: ClassVar[str] = "is.workflow.actions.list"
    default_output_name: ClassVar[str] = "List"

    items: list[str] = field(default_factory=list)

    def _params(self) -> dict[str, Any]:
        """Return WFItems as a plain string array, or {} when empty.

        Apple omits ``WFItems`` entirely for an empty list (confirmed via
        ``samples/decoded/dictionary.xml`` — the list action there has only
        a UUID in its parameters dict). We match that omission to preserve
        wire-format equivalence with GUI-authored shortcuts.

        Raises:
            SchemaError: If any item is not a ``str``. Use plain strings;
                variable references are not supported as list items.
        """
        if not self.items:
            return {}
        non_strings = [i for i in self.items if not isinstance(i, str)]
        if non_strings:
            bad_type = type(non_strings[0]).__name__
            raise SchemaError(
                f"BuildList items must all be plain strings; got a "
                f"{bad_type!r} value. Variable references cannot be "
                f"individual list items in Apple's wire format. To build a "
                f"dynamic list, use the 'Add to Variable' / 'Append Variable' "
                f"pattern instead."
            )
        return {"WFItems": list(self.items)}
