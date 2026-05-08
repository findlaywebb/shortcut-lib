"""Lift every sample's workflow dict through Shortcut.from_workflow → emit."""

from __future__ import annotations

from pathlib import Path

import pytest

from shortcut_lib import decode_file
from shortcut_lib.builder import Shortcut

SAMPLES_DIR = Path(__file__).parent.parent / "samples"


def _all_samples() -> list[Path]:
    public = sorted(SAMPLES_DIR.glob("*.shortcut"))
    private = sorted((SAMPLES_DIR / "private").glob("*.shortcut"))
    return public + private


@pytest.mark.parametrize("sample", _all_samples(), ids=lambda p: p.stem)
def test_lift_then_emit_preserves_actions(sample: Path) -> None:
    """Round-trip via the schema layer using RawAction passthrough.

    A decoded workflow lifted into a ``Shortcut`` and re-emitted must produce
    the same action list — proving the schema layer can wrap any decoded
    file without losing fidelity.

    Top-level metadata (workflow_identifier, surfaces) round-trips when our
    lift preserves it; we only assert on the action list since the lift may
    legitimately default some metadata.
    """
    original = decode_file(sample).workflow
    lifted = Shortcut.from_workflow(original)
    re_emitted = lifted.to_workflow()

    assert re_emitted["WFWorkflowActions"] == original["WFWorkflowActions"]
    assert re_emitted["WFWorkflowMinimumClientVersion"] == original.get(
        "WFWorkflowMinimumClientVersion", 900
    )
