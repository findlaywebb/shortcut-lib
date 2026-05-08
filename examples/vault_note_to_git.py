"""Compositional example: an orchestrator + two helper shortcuts.

This is the multi-shortcut composition pattern: small focused helper
shortcuts (like Python modules) and an orchestrator that links them via
``RunWorkflow``. Each is signed and importable separately.

The actual LLM-polish step is stubbed because Apple's iOS 26 ``Use Model``
action isn't yet schema-modelled (no decoded sample available — see
docs/product_review.md P2). When that lands, swap the placeholder
``ShowNotification`` inside ``polish_helper()`` for a real ``UseModel``
action.

Usage:
    uv run python examples/vault_note_to_git.py

Drops three .shortcut files on ~/Desktop:
- "Polish With LLM.shortcut"  (helper)
- "Push To Vault Repo.shortcut" (helper, placeholder push)
- "Vault Note To Git.shortcut" (orchestrator)

Import all three; the orchestrator's ``RunWorkflow`` actions reference the
helpers by their internal UUID, so they must be present in the Shortcuts
library when the orchestrator runs.
"""

from __future__ import annotations

from pathlib import Path

from shortcut_lib.builder import Shortcut
from shortcut_lib.schema import NamedVar, RunWorkflow, ShortcutInput, Text
from shortcut_lib.schema.actions.get_clipboard import GetClipboard
from shortcut_lib.schema.actions.set_variable import SetVariable
from shortcut_lib.schema.actions.show_notification import ShowNotification


def polish_helper() -> Shortcut:
    """Stub helper: receives a note as input, would call Use Model.

    For now: notifies that a polish would happen, then returns the input
    unchanged (set as a named variable so the orchestrator can pull it).
    """
    s = Shortcut(name="Polish With LLM", surfaces=[])
    s.add(SetVariable(name="Note", input=ShortcutInput))
    s.add(
        ShowNotification(
            title="Polish (stub)",
            body=Text(
                "Would polish: {n}",
                substitutions={"n": NamedVar("Note")},
            ),
        )
    )
    # NB: when UseModel lands, swap the notification for a UseModel
    # action that takes NamedVar("Note") as input and a polish-style
    # prompt, then SetVariable("Note") on its output.
    return s


def push_helper() -> Shortcut:
    """Stub helper: receives polished text, would PUT to GitHub.

    For now: just notifies. The real push (DownloadURL PUT to the GitHub
    Files API) lives in examples/note_to_github.py — copy that block in
    here when you wire this up to a real repo.
    """
    s = Shortcut(name="Push To Vault Repo", surfaces=[])
    s.add(SetVariable(name="Note", input=ShortcutInput))
    s.add(
        ShowNotification(
            title="Push (stub)",
            body=Text(
                "Would push to repo: {n}",
                substitutions={"n": NamedVar("Note")},
            ),
        )
    )
    return s


def orchestrator(polish: Shortcut, push: Shortcut) -> Shortcut:
    """Top-level shortcut: clipboard → polish → push → notify."""
    s = Shortcut(name="Vault Note To Git", surfaces=["share", "quick-action"])

    note = s.add(GetClipboard())
    polished = s.add(RunWorkflow(target=polish, input=note))
    pushed = s.add(RunWorkflow(target=push, input=polished))

    # The orchestrator's tail is a confirmation. The push helper's output
    # is opaque (a stub), so this just acknowledges completion.
    s.add(
        ShowNotification(
            title="Vault → git",
            body=Text(
                "Note flowed through Polish + Push. Result: {r}",
                substitutions={"r": pushed},
            ),
        )
    )
    return s


def main() -> None:
    desktop = Path.home() / "Desktop"
    polish = polish_helper()
    push = push_helper()
    main_shortcut = orchestrator(polish, push)

    for s in (polish, push, main_shortcut):
        out = desktop / f"{s.name}.shortcut"
        s.save_signed(out)
        print(f"wrote {out}")
    print(
        "\nImport all three into Shortcuts.app. The orchestrator's "
        "RunWorkflow steps reference the helpers by UUID, so the helpers "
        "must be present in the library before the orchestrator runs."
    )


if __name__ == "__main__":
    main()
