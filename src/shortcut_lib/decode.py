"""Decode a signed `.shortcut` file to its underlying plist dict.

Pipeline:
  AEA1 wrapper  ->  Apple Archive (AA)  ->  binary plist (WFWorkflow*)

The AEA wrapper is profile 0 (sign-only, no encryption). Apple's iOS Shortcuts
app, the macOS `shortcuts sign` CLI, and the on-device share-sheet export all
use this profile. The signing public key is embedded in the AEA auth-data
plist as the leaf cert of `SigningCertificateChain`, so any signed shortcut
is decodable without external state — the chain is *self-describing for
verification purposes* (Apple's CA validates trust separately when importing).
"""

from __future__ import annotations

import plistlib
import struct
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from shortcut_lib._subprocess import run_cli

AEA_MAGIC = b"AEA1"
AEA_HEADER_LEN = 12  # magic(4) + profile(4) + auth_size(4)


class DecodeError(RuntimeError):
    """Raised when a `.shortcut` file cannot be decoded."""


@dataclass(slots=True)
class DecodedShortcut:
    """A decoded shortcut and its envelope metadata."""

    workflow: dict[str, Any]
    """The WFWorkflow* dict — the actual shortcut definition."""

    profile: int
    """AEA profile index (we expect 0 — sign-only)."""

    signing_subject: str
    """Subject CN of the leaf signing cert."""

    signing_issuer: str
    """Issuer CN of the leaf signing cert."""


def decode_file(path: Path | str) -> DecodedShortcut:
    """Decode a signed `.shortcut` file to a workflow dict."""
    path = Path(path)
    data = path.read_bytes()
    return decode_bytes(data)


def decode_bytes(data: bytes) -> DecodedShortcut:
    """Decode the raw bytes of a `.shortcut` file."""
    if not data.startswith(AEA_MAGIC):
        raise DecodeError(f"not an AEA1 archive (magic={data[:4]!r})")

    profile, auth_size = struct.unpack_from("<II", data, 4)
    if profile != 0:
        raise DecodeError(
            f"unexpected AEA profile {profile}; only sign-only (0) is supported"
        )

    auth_blob = data[AEA_HEADER_LEN : AEA_HEADER_LEN + auth_size]
    try:
        auth = plistlib.loads(auth_blob)
    except plistlib.InvalidFileException as exc:
        raise DecodeError("AEA auth data is not a valid plist") from exc

    chain = auth.get("SigningCertificateChain")
    if not chain:
        raise DecodeError("AEA auth data missing SigningCertificateChain")

    leaf_der: bytes = chain[0]
    try:
        cert = x509.load_der_x509_certificate(leaf_der)
        pub = cert.public_key()
        if not isinstance(pub, ec.EllipticCurvePublicKey):
            raise DecodeError(f"expected EC public key, got {type(pub).__name__}")
        pub_x963 = pub.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
    except DecodeError:
        raise
    except Exception as exc:
        raise DecodeError(
            "could not parse signing certificate from AEA auth data"
        ) from exc

    workflow_dict = _aea_decrypt_then_extract(data, pub_x963)

    return DecodedShortcut(
        workflow=workflow_dict,
        profile=profile,
        signing_subject=_first_cn(cert.subject),
        signing_issuer=_first_cn(cert.issuer),
    )


def _aea_decrypt_then_extract(data: bytes, pub_x963: bytes) -> dict[str, Any]:
    """Run `aea decrypt` then `aa extract`, return the bplist as a dict.

    Shells out because Apple ships these CLIs on every Mac and the alternative
    (re-implementing AEA verification + Apple Archive parsing in Python) is
    weeks of work for no behavioural gain.
    """
    with TemporaryDirectory() as tmp_str:
        tmp = Path(tmp_str)
        archive_in = tmp / "in.shortcut"
        archive_in.write_bytes(data)

        keyfile = tmp / "leaf.pub.hex"
        keyfile.write_text(f"hex:{pub_x963.hex()}")

        aa_path = tmp / "payload.aa"
        run_cli(
            [
                "aea",
                "decrypt",
                "-i",
                str(archive_in),
                "-o",
                str(aa_path),
                "-sign-pub",
                str(keyfile),
            ],
            stage="aea decrypt",
            error_cls=DecodeError,
        )

        extract_dir = tmp / "extracted"
        extract_dir.mkdir()
        run_cli(
            ["aa", "extract", "-i", str(aa_path), "-d", str(extract_dir)],
            stage="aa extract",
            error_cls=DecodeError,
        )

        wflow_files = list(extract_dir.glob("*.wflow"))
        if len(wflow_files) != 1:
            raise DecodeError(
                f"expected one .wflow file in archive, found {len(wflow_files)}"
            )

        return plistlib.loads(wflow_files[0].read_bytes())


def _first_cn(name: x509.Name) -> str:
    attrs = name.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
    if not attrs:
        return name.rfc4514_string()
    value = attrs[0].value
    return value if isinstance(value, str) else value.decode("utf-8", errors="replace")
