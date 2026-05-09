"""Tests for Writing Tools AppIntent actions (writing_tools.py)."""

from __future__ import annotations

import pytest

from shortcut_lib.schema.actions.writing_tools import AdjustTone
from shortcut_lib.schema.base import SchemaError

# ---------------------------------------------------------------------------
# AdjustTone — tone validation
# ---------------------------------------------------------------------------


def test_adjust_tone_valid_professional() -> None:
    """AdjustTone with tone='professional' (sample-confirmed value) emits correctly."""
    action = AdjustTone(text="Hello world", tone="professional")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["tone"] == "professional"
    assert params["text"] == "Hello world"


def test_adjust_tone_valid_friendly() -> None:
    """AdjustTone with tone='friendly' is accepted."""
    action = AdjustTone(text="Hi", tone="friendly")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["tone"] == "friendly"


def test_adjust_tone_valid_concise() -> None:
    """AdjustTone with tone='concise' is accepted."""
    action = AdjustTone(text="Long winding text.", tone="concise")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["tone"] == "concise"


def test_adjust_tone_valid_casual() -> None:
    """AdjustTone with tone='casual' is accepted."""
    action = AdjustTone(text="Hey!", tone="casual")
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert params["tone"] == "casual"


def test_adjust_tone_invalid_raises() -> None:
    """AdjustTone with an unknown tone raises SchemaError naming the bad value."""
    with pytest.raises(SchemaError, match="'formal'"):
        AdjustTone(text="Some text", tone="formal")  # ty: ignore[invalid-argument-type]  # intentional bad value


def test_adjust_tone_invalid_message_includes_valid_set() -> None:
    """SchemaError message for bad tone lists the valid options."""
    with pytest.raises(SchemaError, match="professional"):
        AdjustTone(text="Some text", tone="robotic")  # ty: ignore[invalid-argument-type]  # intentional bad value
