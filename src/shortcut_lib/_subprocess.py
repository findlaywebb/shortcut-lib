"""Shared subprocess helper for shelling out to Apple's CLIs."""

from __future__ import annotations

import shutil
import subprocess

DEFAULT_TIMEOUT = 60.0  # seconds


def run_cli(
    cmd: list[str],
    *,
    stage: str,
    error_cls: type[Exception],
    timeout: float = DEFAULT_TIMEOUT,
) -> None:
    """Run a CLI command, raising ``error_cls`` on non-zero exit, missing binary, or timeout.

    Args:
        cmd: Argv list. cmd[0] must be the binary name or absolute path.
        stage: Human-readable stage name for the error message
            (e.g. "aea decrypt", "shortcuts sign").
        error_cls: Exception class to raise — DecodeError or EncodeError.
        timeout: Wall-clock seconds before SIGKILL.
    """
    binary = cmd[0]
    if shutil.which(binary) is None:
        raise error_cls(
            f"{binary} binary not found — this library requires macOS with "
            f"Xcode Command Line Tools (provides aea/aa/shortcuts)."
        )
    try:
        # cmd is constructed by the caller from literal binary names + paths
        # under TemporaryDirectory; no untrusted-input concern.
        result = subprocess.run(  # noqa: S603
            cmd, capture_output=True, check=False, timeout=timeout
        )
    except subprocess.TimeoutExpired as exc:
        raise error_cls(f"{stage} timed out after {timeout}s") from exc
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        stdout = result.stdout.decode("utf-8", errors="replace").strip()
        # Apple's `shortcuts sign` writes some failure modes to stdout, so
        # include both streams in the error message.
        detail = stderr or stdout or "(no output)"
        raise error_cls(f"{stage} failed (rc={result.returncode}): {detail}")
