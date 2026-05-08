"""Print the action registry — a cheat sheet for authoring.

Run:  uv run python scripts/print_actions.py

Surfaces every registered Action class with its identifier, default output
name, parameter signature, and one-line docstring. Drop-in for an LLM
context primer when starting a make-shortcut session.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from shortcut_lib.schema import describe_action, list_actions


def main() -> None:
    rows = list_actions()
    print(f"# {len(rows)} registered actions\n")
    for row in rows:
        desc = describe_action(row["identifier"])
        params = ", ".join(p["name"] for p in desc["parameters"]) or "(none)"
        out = f" → {desc['default_output_name']}" if desc["default_output_name"] else ""
        print(f"## {desc['name']}{out}")
        print(f"`{desc['identifier']}`")
        if desc["doc"]:
            first_line = desc["doc"].splitlines()[0].strip()
            print(f"_{first_line}_")
        print(f"Parameters: {params}\n")


if __name__ == "__main__":
    main()
