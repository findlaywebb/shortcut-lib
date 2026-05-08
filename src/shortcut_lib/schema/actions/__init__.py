"""Leaf-action implementations.

Each action lives in its own module and registers itself via the
``@register`` decorator. Importing this package side-effect-imports every
submodule so the registry is populated.

Tier 0 actions live here (the ones C1 needs to round-trip a synthetic
shortcut). Tier 1+ actions are added by C2-* tasks.
"""

from __future__ import annotations

from shortcut_lib.schema.actions import dictate_text, set_clipboard

__all__ = ["dictate_text", "set_clipboard"]
