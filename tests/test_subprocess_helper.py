"""Tests for the shared _subprocess.run_cli helper."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from shortcut_lib._subprocess import run_cli


class _SentinelError(RuntimeError):
    """Dummy error class used in place of DecodeError/EncodeError."""


def test_run_cli_raises_on_missing_binary() -> None:
    """run_cli raises error_cls with a binary-not-found message when shutil.which returns None."""
    with (
        patch("shortcut_lib._subprocess.shutil.which", return_value=None),
        pytest.raises(_SentinelError, match="not found"),
    ):
        run_cli(
            ["nonexistent-binary", "--flag"],
            stage="test stage",
            error_cls=_SentinelError,
        )


def test_run_cli_raises_on_timeout() -> None:
    """run_cli raises error_cls when the subprocess exceeds the timeout."""
    with pytest.raises(_SentinelError, match="timed out"):
        run_cli(
            ["sleep", "5"], stage="sleep stage", error_cls=_SentinelError, timeout=0.1
        )


def test_run_cli_includes_stdout_when_stderr_empty() -> None:
    """run_cli includes stdout in the error message when stderr is empty."""
    with pytest.raises(_SentinelError, match="from-stdout"):
        run_cli(
            ["sh", "-c", "echo from-stdout; exit 1"],
            stage="sh stage",
            error_cls=_SentinelError,
        )


def test_run_cli_success_does_not_raise() -> None:
    """run_cli does not raise for a zero-exit command."""
    run_cli(["true"], stage="true stage", error_cls=_SentinelError)


def test_run_cli_prefers_stderr_over_stdout() -> None:
    """run_cli uses stderr text in the error message when both streams have content."""
    with pytest.raises(_SentinelError, match="from-stderr"):
        run_cli(
            ["sh", "-c", "echo from-stdout; echo from-stderr >&2; exit 1"],
            stage="sh stage",
            error_cls=_SentinelError,
        )
