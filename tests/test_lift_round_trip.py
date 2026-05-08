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
def test_lift_then_emit_preserves_full_top_level(sample: Path) -> None:
    """Lift→emit must reproduce the full top-level WFWorkflow* dict.

    Captures regressions in metadata fidelity: WFWorkflowImportQuestions,
    WFWorkflowNoInputBehavior, WFQuickActionSurfaces, the original
    WFWorkflowClientVersion, etc. The schema layer routes everything not
    represented by an explicit Shortcut attribute through ``_extra`` so the
    re-emit is byte-for-byte identical at the top level.

    Anything that legitimately can't round-trip belongs on the allowlist
    below — keep that list short and document why each entry is there.
    """
    original = decode_file(sample).workflow
    lifted = Shortcut.from_workflow(original)
    re_emitted = lifted.to_workflow()

    # Currently empty: every top-level key in our committed samples
    # round-trips exactly. If a future sample legitimately can't (e.g. a
    # client-version that we want to regenerate), add the key here with a
    # one-line rationale.
    allowlist: set[str] = set()

    keys_to_check = (set(original) | set(re_emitted)) - allowlist
    for key in keys_to_check:
        assert re_emitted.get(key) == original.get(key), (
            f"top-level key {key!r} differs after lift→emit for {sample.name}"
        )
