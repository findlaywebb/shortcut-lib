"""Decode-pipeline tests against committed sample fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from shortcut_lib.decode import DecodeError, decode_bytes, decode_file

SAMPLES = Path(__file__).parent.parent / "samples"


def _samples() -> list[Path]:
    return sorted(SAMPLES.glob("*.shortcut"))


@pytest.mark.parametrize("sample", _samples(), ids=lambda p: p.stem)
def test_decode_returns_workflow(sample: Path) -> None:
    decoded = decode_file(sample)
    assert decoded.profile == 0
    assert decoded.signing_issuer.startswith("Apple")
    assert "WFWorkflowActions" in decoded.workflow
    actions = decoded.workflow["WFWorkflowActions"]
    assert isinstance(actions, list)
    assert all("WFWorkflowActionIdentifier" in a for a in actions)


def test_rejects_non_aea_input() -> None:
    with pytest.raises(DecodeError, match="not an AEA1 archive"):
        decode_bytes(b"bplist00" + b"\x00" * 64)
