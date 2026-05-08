"""Vault note → polished by Apple Intelligence → committed to GitHub.

Single self-contained shortcut. Python composes the steps via helper
functions; the emitted ``.shortcut`` is one workflow with no
``RunWorkflow`` calls — iOS assigns fresh UUIDs at import time and
won't honour pre-baked links to other shortcuts in a locally-signed
file, so multi-shortcut composition costs more than it gives.

Pipeline:

    clipboard
      -> Apple Intelligence "Use Model" (polish)
      -> base64 + GitHub Files API PUT
      -> notification

Token + repo are placeholder Text actions at the top of the shortcut.
Edit them in Shortcuts.app after import; don't share the signed
``.shortcut`` file with a real PAT baked in.

Usage:
    uv run python examples/vault_note_to_git.py

Drops ``Vault Note To Git.shortcut`` on ~/Desktop. Import, edit the
two placeholders, and run with a clipboard note.
"""

from __future__ import annotations

from pathlib import Path

from shortcut_lib.builder import Shortcut
from shortcut_lib.schema import NamedVar, Text
from shortcut_lib.schema.actions.base64_encode import Base64Encode
from shortcut_lib.schema.actions.download_url import DownloadURL
from shortcut_lib.schema.actions.format_date import FormatDate
from shortcut_lib.schema.actions.get_clipboard import GetClipboard
from shortcut_lib.schema.actions.get_text import GetText
from shortcut_lib.schema.actions.set_variable import SetVariable
from shortcut_lib.schema.actions.show_notification import ShowNotification
from shortcut_lib.schema.actions.text_replace import TextReplace
from shortcut_lib.schema.actions.use_model import UseModel
from shortcut_lib.schema.values import CurrentDate

PLACEHOLDER_TOKEN = "REPLACE_WITH_GITHUB_PAT"  # noqa: S105
PLACEHOLDER_REPO = "owner/repo-name"


def _add_config(s: Shortcut) -> None:
    """Set Token and Repo named variables from placeholder Text actions."""
    token_text = s.add(GetText(text=PLACEHOLDER_TOKEN))
    s.add(SetVariable(name="Token", input=token_text))

    repo_text = s.add(GetText(text=PLACEHOLDER_REPO))
    s.add(SetVariable(name="Repo", input=repo_text))


def _add_polish(s: Shortcut) -> None:
    """Read the clipboard, polish via Apple Intelligence, store as ``Polished``."""
    note = s.add(GetClipboard())
    s.add(SetVariable(name="Note", input=note))
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


def _add_push(s: Shortcut) -> None:
    """Encode ``Polished`` and PUT it to the GitHub Files API."""
    # Filename: yyyy-MM-dd_HH-mm-ss-SSS — ms precision keeps re-runs from
    # colliding on the GitHub side (PUT returns 422 "sha wasn't supplied"
    # if the path already exists).
    stamp = s.add(
        FormatDate(
            input=CurrentDate,
            date_style="Custom",
            custom_format="yyyy-MM-dd_HH-mm-ss-SSS",
        )
    )
    s.add(SetVariable(name="Stamp", input=stamp))

    base_text = s.add(
        GetText(
            text=Text(
                "note_{stamp}",
                substitutions={"stamp": NamedVar("Stamp")},
            )
        )
    )
    s.add(SetVariable(name="Base", input=base_text))

    encoded = s.add(Base64Encode(input=NamedVar("Polished")))
    stripped = s.add(
        TextReplace(
            input=encoded,
            find=r"\s+",
            replace="",
            regex=True,
        )
    )
    s.add(SetVariable(name="ContentB64", input=stripped))

    url_text = s.add(
        GetText(
            text=Text(
                "https://api.github.com/repos/{repo}/contents/notes/{base}.md",
                substitutions={"repo": NamedVar("Repo"), "base": NamedVar("Base")},
            )
        )
    )
    auth_header = Text("Bearer {tok}", substitutions={"tok": NamedVar("Token")})
    s.add(
        DownloadURL(
            url=url_text,
            method="PUT",
            headers={
                "Authorization": auth_header,
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            body={
                "message": Text(
                    "Add note {base}", substitutions={"base": NamedVar("Base")}
                ),
                "content": NamedVar("ContentB64"),
            },
            body_type="JSON",
        )
    )

    s.add(
        ShowNotification(
            title="Pushed to GitHub",
            body=Text(
                "Saved notes/{base}.md to {repo}.",
                substitutions={"base": NamedVar("Base"), "repo": NamedVar("Repo")},
            ),
        )
    )


def build() -> Shortcut:
    s = Shortcut(name="Vault Note To Git", surfaces=["share", "quick-action"])
    _add_config(s)
    _add_polish(s)
    _add_push(s)
    return s


def main() -> None:
    s = build()
    out = Path.home() / "Desktop" / f"{s.name}.shortcut"
    s.save_signed(out)
    print(f"wrote {out}")
    print(
        "\nImport, then open the shortcut in Shortcuts.app and replace the "
        "placeholder token + repo in the first two Text actions."
    )


if __name__ == "__main__":
    main()
