"""Shortcut.from_file — convenience for decode_file → from_workflow."""

from __future__ import annotations

from pathlib import Path

from shortcut_lib.builder import Shortcut

SAMPLES = Path(__file__).parent.parent / "samples"


def test_from_file_loads_and_round_trips() -> None:
    sample = SAMPLES / "dictate_to_clipboard.shortcut"
    lifted = Shortcut.from_file(sample)
    assert lifted.name == "dictate_to_clipboard"
    workflow = lifted.to_workflow()
    assert len(workflow["WFWorkflowActions"]) == 2


def test_from_file_custom_name() -> None:
    sample = SAMPLES / "start_pomodoro.shortcut"
    lifted = Shortcut.from_file(sample, name="My Pomodoro")
    assert lifted.name == "My Pomodoro"
