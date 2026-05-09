"""Post the clipboard contents as a markdown file to a GitHub repo.

Demonstrates the full Tier 0/1/2 surface end to end:
- Setup section (FU-9) for token + repo — filled at import time
- Get Clipboard → text
- Format Date for the filename
- Templated strings (Text)
- Base64 + regex strip whitespace (GitHub Files API requires raw base64)
- Dictionary literal for the JSON body
- DownloadURL PUT with Authorization header
- ShowNotification on success

Pattern lifted from Findlay's `voice_note_to_github.shortcut` but trimmed
to text only — no audio recording, no Notes backup, no transcription.

Usage:
    uv run python examples/note_to_github.py

Drops ``Note to GitHub.shortcut`` on ~/Desktop. Import, fill in the two
Setup prompts (token and repo), then run with content on the clipboard.
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
from shortcut_lib.schema.values import CurrentDate


def build() -> Shortcut:
    s = Shortcut(
        name="Note to GitHub",
        surfaces=["share", "quick-action"],
    )

    # 1. Configuration block — token + repo via Setup prompts at import time.
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

    # 2. Source: clipboard contents.
    note = s.add(GetClipboard())
    s.add(SetVariable(name="Note", input=note))

    # 3. Filename: yyyy-MM-dd_HH-mm-ss
    stamp = s.set(
        "Stamp",
        s.add(
            FormatDate(
                input=CurrentDate,
                date_style="Custom",
                custom_format="yyyy-MM-dd_HH-mm-ss",
            )
        ),
    )

    base = s.set(
        "Base",
        s.add(
            GetText(
                text=Text(
                    "note_{stamp}",
                    substitutions={"stamp": stamp},
                )
            )
        ),
    )

    # 4. Encode the note content for the GitHub Files API.
    encoded = s.add(Base64Encode(input=NamedVar("Note")))
    stripped = s.add(
        TextReplace(
            input=encoded,
            find=r"\s+",
            replace="",
            regex=True,
        )
    )
    content_b64 = s.set("ContentB64", stripped)

    # 5. Build the request URL.
    url_text = s.add(
        GetText(
            text=Text(
                "https://api.github.com/repos/{repo}/contents/notes/{base}.md",
                substitutions={"repo": repo, "base": base},
            )
        )
    )

    # 6. PUT to GitHub Files API.  body is the JSON object Apple inlines
    #    into WFJSONValues.  GitHub: PUT contents/{path} with
    #    {"message": "...", "content": "<base64>"}.
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
                "message": Text("Add note {base}", substitutions={"base": base}),
                "content": content_b64,
            },
            body_type="JSON",
        )
    )

    # 7. Confirm to the user.
    s.add(
        ShowNotification(
            title="Pushed to GitHub",
            body=Text(
                "Saved {base}.md to {repo}.",
                substitutions={
                    "base": base,
                    "repo": repo,
                },
            ),
        )
    )
    return s


def main() -> None:
    s = build()
    out = Path.home() / "Desktop" / f"{s.name}.shortcut"
    s.save_signed(out)
    print(f"wrote {out}")
    print("\nImport, fill in the two Setup prompts (token + repo), and run.")


if __name__ == "__main__":
    main()
