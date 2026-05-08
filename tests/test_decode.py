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


def test_decode_bytes_non_zero_profile_raises() -> None:
    """AEA profile != 0 (e.g. encrypted) is rejected with a clear message."""
    import plistlib
    import struct

    # Build a minimal AEA1 header with profile=1 (encrypted — not supported).
    # auth_size=0 so there's no plist blob, but the profile check fires first.
    auth_blob = plistlib.dumps({"SigningCertificateChain": [b"\x00"]})
    header = b"AEA1" + struct.pack("<II", 1, len(auth_blob))
    data = header + auth_blob + b"\x00" * 64
    with pytest.raises(DecodeError, match="unexpected AEA profile"):
        decode_bytes(data)


def test_decode_bytes_missing_cert_chain_raises() -> None:
    """AEA auth plist without SigningCertificateChain is rejected."""
    import plistlib
    import struct

    auth_blob = plistlib.dumps({})  # no SigningCertificateChain key
    header = b"AEA1" + struct.pack("<II", 0, len(auth_blob))
    data = header + auth_blob + b"\x00" * 64
    with pytest.raises(DecodeError, match="missing SigningCertificateChain"):
        decode_bytes(data)
