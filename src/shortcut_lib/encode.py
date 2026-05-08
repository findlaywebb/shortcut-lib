"""Encode a workflow dict back into a `.shortcut` file.

Two layers:

- :func:`encode_to_bplist` — plain binary plist (a bare unsigned shortcut).
  This is the round-trip oracle and what unit tests assert against.
- :func:`sign_to_file` — writes the bplist to a temp file then shells to
  ``shortcuts sign`` to produce the AA + AEA-wrapped, signed file Shortcuts.app
  imports.

Apple's ``shortcuts`` CLI handles the AA + AEA + chain-signing for us;
re-implementing that in Python would add weeks for no behavioural gain.
"""

from __future__ import annotations

import plistlib
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Literal

from shortcut_lib._subprocess import run_cli

SignMode = Literal["anyone", "people-who-know-me"]


class EncodeError(RuntimeError):
    """Raised when encoding or signing fails."""


def encode_to_bplist(workflow: dict[str, Any]) -> bytes:
    """Serialise a workflow dict to a binary plist.

    Round-trip property: ``plistlib.loads(encode_to_bplist(w)) == w``
    for any ``w`` produced by :func:`shortcut_lib.decode.decode_file`.
    """
    return plistlib.dumps(workflow, fmt=plistlib.FMT_BINARY, sort_keys=False)


def sign_to_file(
    workflow: dict[str, Any],
    output: Path | str,
    *,
    mode: SignMode = "anyone",
) -> None:
    """Encode and sign a workflow as an importable `.shortcut` file.

    Args:
        workflow: The workflow dict (the WFWorkflow* top-level dict).
        output: Destination path for the signed file.
        mode: Sign mode. ``"anyone"`` lets any user import; the alternative
            restricts to contacts of the signing identity.
    """
    output = Path(output)
    bplist = encode_to_bplist(workflow)

    with TemporaryDirectory() as tmp_str:
        tmp = Path(tmp_str)
        unsigned = tmp / "unsigned.shortcut"
        unsigned.write_bytes(bplist)
        run_cli(
            [
                "shortcuts",
                "sign",
                "--mode",
                mode,
                "--input",
                str(unsigned),
                "--output",
                str(output),
            ],
            stage="shortcuts sign",
            error_cls=EncodeError,
        )
