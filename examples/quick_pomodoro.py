"""Re-author the gallery Start Pomodoro shortcut from Python.

Demonstrates the schema layer end-to-end: ask for input, conditional with
self-recursion guard, variable composition, templated notification text.

Authored from scratch — not lifted. The result will differ from the gallery
sample in details (UUIDs, unset fields), but matches the same intent.

Usage:
    uv run python examples/quick_pomodoro.py
"""

from __future__ import annotations

from pathlib import Path

from shortcut_lib.builder import Shortcut
from shortcut_lib.schema import If, RunWorkflow, Self, Text
from shortcut_lib.schema.actions.ask import AskForInput
from shortcut_lib.schema.actions.show_notification import ShowNotification


def build() -> Shortcut:
    s = Shortcut(name="Quick Pomodoro", surfaces=["watch", "widget"])

    minutes = s.add(
        AskForInput(
            prompt="OK, for how many minutes?",
            input_type="Number",
            default_answer="25",
            allows_decimal=False,
            allows_negative=False,
        )
    )

    # Guard against zero / negative input — fall back to a default.
    s.add(
        If(
            operand=minutes,
            op="<",
            value=1,
            then=[
                ShowNotification(
                    title="Pomodoro",
                    body="That's not a valid duration — try again.",
                ),
                # Recurse into self to re-prompt. The Self sentinel is bound
                # to the containing shortcut at add() time.
                RunWorkflow(target=Self),
            ],
        )
    )

    s.add(
        ShowNotification(
            title="Pomodoro started",
            body=Text(
                "{n} minutes. Focus until the timer runs out.",
                substitutions={"n": minutes},
            ),
        )
    )
    return s


def main() -> None:
    s = build()
    out = Path.home() / "Desktop" / f"{s.name}.shortcut"
    s.save_signed(out)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
