"""Worked patterns for control-flow constructs.

Reading reference for the LLM author. Each ``build_*()`` function returns
a tiny standalone Shortcut showing one construct in a realistic shape.

The Apple wire format uses paired open/close marker actions sharing a
``GroupingIdentifier``; the lib emits these automatically as long as you
nest body actions correctly in the DSL — you should not need to think
about ``GroupingIdentifier`` directly.

Magic variables in scope inside bodies:

- ``RepeatCount(...)`` body: ``RepeatIndex`` (1-based current iteration)
- ``RepeatEach(items=...)`` body: ``RepeatItem`` (current element),
  ``RepeatIndex`` (1-based)
- ``If(...)`` and ``ChooseFromMenu(...)`` bodies: no special magic vars

Run this file to drop four ``.shortcut`` files on ~/Desktop. Drag any
one into Shortcuts.app to see how Apple renders the construct.

Usage:
    uv run python examples/control_flow_demo.py
"""

from __future__ import annotations

from pathlib import Path

from shortcut_lib.builder import Shortcut
from shortcut_lib.schema import (
    ChooseFromMenu,
    If,
    RepeatCount,
    RepeatEach,
    RepeatIndex,
    RepeatItem,
    Text,
)
from shortcut_lib.schema.actions.ask import AskForInput
from shortcut_lib.schema.actions.get_text import GetText
from shortcut_lib.schema.actions.show_notification import ShowNotification
from shortcut_lib.schema.actions.text_split import TextSplit


def build_if() -> Shortcut:
    """Demonstrate ``If`` / ``Else``: ask a question and react.

    Pattern:
    - The condition has three parts: ``operand`` (the value being tested),
      ``op`` (a string alias like ``"=="``, ``"contains"``, ``"is-true"``,
      or a :class:`WFCondition` member), and ``value`` (the right-hand side).
    - ``then=`` and ``otherwise=`` each take a list of Actions.
    - Pairing of head / else / close markers is automatic.
    """
    s = Shortcut(name="Coin Flip", surfaces=[])
    answer = s.add(AskForInput.text(prompt="Heads or tails?"))
    s.add(
        If(
            operand=answer,
            op="==",
            value="heads",
            then=[
                ShowNotification(title="Coin", body="You called it — heads."),
            ],
            otherwise=[
                ShowNotification(title="Coin", body="Tails. Try again."),
            ],
        )
    )
    return s


def build_repeat_count() -> Shortcut:
    """Demonstrate ``RepeatCount``: do something N times.

    ``RepeatIndex`` is 1-based and refers to the current iteration. The
    ``count`` field accepts either an int literal or any Action / Value
    whose output is a number.
    """
    s = Shortcut(name="Three Ticks", surfaces=[])
    s.add(
        RepeatCount(
            count=3,
            body=[
                ShowNotification(
                    title="Tick",
                    body=Text("Iteration {i} of 3", substitutions={"i": RepeatIndex}),
                ),
            ],
        )
    )
    return s


def build_repeat_each() -> Shortcut:
    """Demonstrate ``RepeatEach``: iterate over a list.

    ``RepeatItem`` refers to the current element. Here the list comes
    from splitting a literal text on newlines, but in real shortcuts it
    is typically the output of an action that produces a list (e.g.
    ``TextSplit``, ``GetFiles``, ``FindPhotos``).
    """
    s = Shortcut(name="Process Lines", surfaces=[])
    text = s.add(GetText(text="alpha\nbeta\ngamma"))
    lines = s.add(TextSplit(input=text, separator="New Lines"))
    s.add(
        RepeatEach(
            items=lines,
            body=[
                ShowNotification(
                    title="Line",
                    body=Text("got {x}", substitutions={"x": RepeatItem}),
                ),
            ],
        )
    )
    return s


def build_choose_from_menu() -> Shortcut:
    """Demonstrate ``ChooseFromMenu``: present options and branch by selection.

    ``cases`` is a list of ``(label, [body actions])`` tuples. The user
    sees a menu with one entry per label; the selected case's body runs.
    """
    s = Shortcut(name="Mood Logger", surfaces=[])
    s.add(
        ChooseFromMenu(
            prompt="How are you?",
            cases=[
                ("Happy", [ShowNotification(title="Mood", body="Glad to hear it.")]),
                ("Neutral", [ShowNotification(title="Mood", body="Logged.")]),
                ("Sad", [ShowNotification(title="Mood", body="Thinking of you.")]),
            ],
        )
    )
    return s


def main() -> None:
    desktop = Path.home() / "Desktop"
    builders = (
        build_if,
        build_repeat_count,
        build_repeat_each,
        build_choose_from_menu,
    )
    for build in builders:
        s = build()
        out = desktop / f"{s.name}.shortcut"
        s.save_signed(out)
        print(f"wrote {out}")


if __name__ == "__main__":
    main()
