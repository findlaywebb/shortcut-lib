"""Round-trip identity: every committed sample must survive decode→encode→decode."""

from __future__ import annotations

import plistlib
from pathlib import Path

import pytest

from shortcut_lib import decode_file, encode_to_bplist

SAMPLES_DIR = Path(__file__).parent.parent / "samples"


def _all_samples() -> list[Path]:
    public = sorted(SAMPLES_DIR.glob("*.shortcut"))
    private = sorted((SAMPLES_DIR / "private").glob("*.shortcut"))
    return public + private


@pytest.mark.parametrize("sample", _all_samples(), ids=lambda p: p.stem)
def test_workflow_dict_round_trips(sample: Path) -> None:
    """decode → encode → decode preserves the workflow dict exactly."""
    original = decode_file(sample).workflow
    bplist = encode_to_bplist(original)
    re_decoded = plistlib.loads(bplist)
    assert re_decoded == original


def test_sign_to_file_round_trips(tmp_path: Path) -> None:
    """decode → sign → re-decode preserves the workflow dict.

    Exercises the shellout-to-`shortcuts sign` path end-to-end. We use one
    representative sample rather than all samples to keep the test fast —
    the bplist-only round-trip already covers per-sample coverage.
    """
    from shortcut_lib import sign_to_file

    sample = SAMPLES_DIR / "start_pomodoro.shortcut"
    original = decode_file(sample).workflow

    signed = tmp_path / "round_trip.shortcut"
    sign_to_file(original, signed)
    assert signed.exists()

    re_decoded = decode_file(signed)
    assert re_decoded.workflow == original
    assert re_decoded.signing_issuer.startswith("Apple")
