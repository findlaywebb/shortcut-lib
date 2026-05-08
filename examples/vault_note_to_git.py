"""Compositional example: an orchestrator + two helper shortcuts.

This is the multi-shortcut composition pattern: small focused helper
shortcuts (like Python modules) and an orchestrator that links them via
``RunWorkflow``. Each is signed and importable separately.

The polish helper now calls Apple Intelligence's ``Use Model`` action
(modelled in C2 after the user exported `intelly.shortcut`). The push
helper is still a placeholder — see ``examples/note_to_github.py`` for
a real GitHub Files API push you can paste in.

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
from shortcut_lib.schema.actions.use_model import UseModel


def polish_helper() -> Shortcut:
    """Receive a note via Shortcut Input, polish it via Apple Intelligence.

    The polished text is set as the ``Polished`` named variable so the
    orchestrator can pull it via NamedVar regardless of the helper's
    output-passing behaviour.
    """
    s = Shortcut(name="Polish With LLM", surfaces=[])
    s.add(SetVariable(name="Note", input=ShortcutInput))
    polished = s.add(
        UseModel(
            prompt=Text(
                "Polish this note for clarity and tone, preserving meaning. "
                "Return only the polished text, no commentary:\n\n{n}",
                substitutions={"n": NamedVar("Note")},
            ),
            model="Apple Intelligence",
        )
    )
    s.add(SetVariable(name="Polished", input=polished))
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
