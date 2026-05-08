"""Snapshot test for the buzz summary format."""

from __future__ import annotations

from pathlib import Path

from shortcut_lib import decode_file
from shortcut_lib.summary import workflow_to_summary

SAMPLES = Path(__file__).parent.parent / "samples"
SNAPSHOTS = Path(__file__).parent / "snapshots"


def test_start_pomodoro_jelly_snapshot() -> None:
    """The summary output for the canonical sample stays stable.

    Update via: ``uv run shortcut-decode samples/start_pomodoro.shortcut
    --format buzz -o tests/snapshots/start_pomodoro.buzz``.
    """
    actual = workflow_to_summary(
        decode_file(SAMPLES / "start_pomodoro.shortcut").workflow
    )
    expected = (SNAPSHOTS / "start_pomodoro.buzz").read_text()
    assert actual == expected


def test_summary_compact() -> None:
    """Sanity: the summary should be markedly smaller than the XML plist."""
    import plistlib

    decoded = decode_file(SAMPLES / "start_pomodoro.shortcut")
    summary = workflow_to_summary(decoded.workflow)
    xml = plistlib.dumps(decoded.workflow, fmt=plistlib.FMT_XML).decode()
    # 5x is a conservative floor; in practice we see ~7-10x.
    assert len(xml) > 5 * len(summary), (
        f"summary not compact enough: xml={len(xml)} summary={len(summary)}"
    )
