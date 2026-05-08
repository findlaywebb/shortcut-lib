"""Tests for GetClipboard action schema."""

from __future__ import annotations

import shortcut_lib.schema.actions.get_clipboard  # noqa: F401 — trigger registration
from shortcut_lib.schema.actions.get_clipboard import GetClipboard
from shortcut_lib.schema.registry import lookup


def test_get_clipboard_emits_basic_action() -> None:
    """to_action_dict carries the correct WFWorkflowActionIdentifier."""
    action = GetClipboard()
    d = action.to_action_dict()
    assert d["WFWorkflowActionIdentifier"] == "is.workflow.actions.getclipboard"


def test_get_clipboard_output_token() -> None:
    """output() produces an Output whose name is 'Clipboard'."""
    action = GetClipboard()
    out = action.output()
    assert out.name == "Clipboard"


def test_get_clipboard_registered() -> None:
    """GetClipboard is discoverable via the registry."""
    cls = lookup("is.workflow.actions.getclipboard")
    assert cls is GetClipboard
