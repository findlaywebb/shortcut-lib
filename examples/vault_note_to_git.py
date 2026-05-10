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

Token + repo are collected via Setup prompts shown at import time.
Don't bake a real PAT into the signed ``.shortcut`` file.

Usage:
    uv run python examples/vault_note_to_git.py

Drops ``Vault Note To Git.shortcut`` on ~/Desktop. Import, fill in
the two Setup prompts, and run with a clipboard note.
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
from shortcut_lib.schema.actions.show_notification import ShowNotification
from shortcut_lib.schema.actions.text_replace import TextReplace
from shortcut_lib.schema.actions.use_model import UseModel
from shortcut_lib.schema.values import CurrentDate


def _add_config(s: Shortcut) -> tuple[NamedVar, NamedVar]:
    """Collect Token and Repo via Setup prompts shown at import time.

    Returns:
        Tuple of (token, repo) typed handles for use downstream.
    """
    token_text = s.ask_text_on_import(
        question="Your GitHub personal access token (fine-grained, contents: read+write)",
        default="REPLACE_WITH_GITHUB_PAT",
    )
    token = s.set("Token", token_text)
    repo_text = s.ask_text_on_import(
        question="The repo to commit to (owner/name)",
        default="owner/repo-name",
    )
    repo = s.set("Repo", repo_text)
    return token, repo


def _add_polish(s: Shortcut) -> NamedVar:
    """Read the clipboard, polish via Apple Intelligence, store as ``Polished``.

    Returns:
        Typed handle for the Polished variable.
    """
    note = s.add(GetClipboard())
    note_var = s.set("Note", note)
    polished = s.add(
        UseModel(
            prompt=Text(
                "Polish this note for clarity and tone, preserving meaning. "
                "Return only the polished text, no commentary:\n\n{n}",
                substitutions={"n": note_var},
            ),
            model="Apple Intelligence",
        )
    )
    polished_var = s.set("Polished", polished)
    return polished_var


def _add_push(
    s: Shortcut,
    polished_var: NamedVar,
    token: NamedVar,
    repo: NamedVar,
) -> None:
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
    stamp_var = s.set("Stamp", stamp)

    base_text = s.add(
        GetText(
            text=Text(
                "note_{stamp}",
                substitutions={"stamp": stamp_var},
            )
        )
    )
    base_var = s.set("Base", base_text)

    encoded = s.add(Base64Encode(input=polished_var))
    stripped = s.add(
        TextReplace(
            input=encoded,
            find=r"\s+",
            replace="",
            regex=True,
        )
    )
    content_b64 = s.set("ContentB64", stripped)

    url_text = s.add(
        GetText(
            text=Text(
                "https://api.github.com/repos/{repo}/contents/notes/{base}.md",
                substitutions={"repo": repo, "base": base_var},
            )
        )
    )
    auth_header = Text("Bearer {tok}", substitutions={"tok": token})
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
                "message": Text("Add note {base}", substitutions={"base": base_var}),
                "content": content_b64,
            },
            body_type="JSON",
        )
    )

    s.add(
        ShowNotification(
            title="Pushed to GitHub",
            body=Text(
                "Saved notes/{base}.md to {repo}.",
                substitutions={"base": base_var, "repo": repo},
            ),
        )
    )


def build() -> Shortcut:
    s = Shortcut(name="Vault Note To Git", surfaces=["share", "quick-action"])
    token, repo = _add_config(s)
    polished_var = _add_polish(s)
    _add_push(s, polished_var, token, repo)
    return s


def main() -> None:
    s = build()
    out = Path.home() / "Desktop" / f"{s.name}.shortcut"
    s.save_signed(out)
    print(f"wrote {out}")
    print("\nImport, fill in the two Setup prompts, and run with a clipboard note.")


if __name__ == "__main__":
    main()
