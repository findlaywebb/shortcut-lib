"""Minimal example: dictate text and copy it to the clipboard.

Mirrors the existing `samples/dictate_to_clipboard.shortcut` sample so the
authored output can be diffed against the real Apple-exported version.

Usage:
    uv run python examples/dictate_to_clipboard.py

Drops a signed `.shortcut` file in the user's Desktop. Drag to import.
"""

from __future__ import annotations

from pathlib import Path

from shortcut_lib.builder import Shortcut
from shortcut_lib.schema.actions.dictate_text import DictateText
from shortcut_lib.schema.actions.set_clipboard import SetClipboard


def build() -> Shortcut:
    s = Shortcut(name="Dictate to Clipboard", surfaces=["watch", "widget"])
    text = s.add(DictateText())
    s.add(SetClipboard(input=text))
    return s


def main() -> None:
    s = build()
    out = Path.home() / "Desktop" / f"{s.name}.shortcut"
    s.save_signed(out)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
