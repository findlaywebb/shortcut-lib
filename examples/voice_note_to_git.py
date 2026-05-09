"""Voice note → transcribed markdown + raw audio committed to GitHub.

Single self-contained shortcut. Record audio, transcribe it on-device,
optionally collect metadata via a ChooseFromMenu gate, then push two
files to GitHub: a frontmatter-stamped markdown note under
``jots/voice/`` and the raw ``.m4a`` binary under
``jots/voice/raw_audio/``.

Pipeline:

    import -> fill Setup (Token + Repo) -> run
      -> RecordAudio (immediately)
      -> TranscribeAudio
      -> ChooseFromMenu: "Add metadata" | "Done"
          Add metadata: AskForInput -> Metadata variable
          Done:         Metadata = "" (empty, harmless in template)
      -> FormatDate (yyyy-MM-dd_HH-mm-ss-SSS)
      -> build Base = "voice_<Stamp>"
      -> build markdown with frontmatter + transcript + metadata
      -> Base64Encode markdown -> strip whitespace -> PUT jots/voice/<Base>.md
      -> Base64Encode audio   -> strip whitespace -> PUT jots/voice/raw_audio/<Base>.m4a
      -> ShowNotification

Notes:
- Token and Repo are collected via Setup prompts at import time (FU-9
  pattern). Never bake a real PAT into the signed file.
- The original hand-built shortcut included a Notes backup via
  com.apple.mobilenotes.SharingExtension. That action is not modelled
  in the lib and is intentionally omitted here.
- The original shortcut embedded a device: field using a DeviceDetails
  magic variable in the frontmatter. DeviceDetails is not modelled in
  V1 and is intentionally skipped.

Usage:
    uv run python examples/voice_note_to_git.py

Drops ``Voice Note To Git.shortcut`` on ~/Desktop. Import, fill in the
two Setup prompts, and run.
"""

from __future__ import annotations

from pathlib import Path

from shortcut_lib.builder import Shortcut
from shortcut_lib.schema import ChooseFromMenu, NamedVar, Text
from shortcut_lib.schema.actions.ask import AskForInput
from shortcut_lib.schema.actions.base64_encode import Base64Encode
from shortcut_lib.schema.actions.download_url import DownloadURL
from shortcut_lib.schema.actions.format_date import FormatDate
from shortcut_lib.schema.actions.get_text import GetText
from shortcut_lib.schema.actions.record_audio import RecordAudio
from shortcut_lib.schema.actions.set_variable import SetVariable
from shortcut_lib.schema.actions.show_notification import ShowNotification
from shortcut_lib.schema.actions.text_replace import TextReplace
from shortcut_lib.schema.actions.transcribe_audio import TranscribeAudio
from shortcut_lib.schema.values import CurrentDate


def _add_config(s: Shortcut) -> None:
    """Collect Token and Repo via Setup prompts shown at import time."""
    token_text = s.ask_text_on_import(
        question="Your GitHub personal access token (fine-grained, contents: read+write)",
        default="REPLACE_WITH_GITHUB_PAT",
    )
    s.set("Token", token_text)
    repo_text = s.ask_text_on_import(
        question="The repo to commit to (owner/name)",
        default="owner/repo-name",
    )
    s.set("Repo", repo_text)


def _add_record_and_transcribe(s: Shortcut) -> None:
    """Record audio then transcribe it; store both as named variables."""
    audio = s.add(RecordAudio(start="Immediately"))
    s.set("Audio", audio)

    transcript = s.add(TranscribeAudio(audio_file=NamedVar("Audio")))
    s.set("Transcript", transcript)


def _add_metadata_gate(s: Shortcut) -> None:
    """Prompt for optional metadata via a two-case ChooseFromMenu.

    Both cases assign the Metadata variable so downstream template code
    can reference it unconditionally. "Add metadata" prompts the user for
    tags or context; "Done" writes an empty string.
    """
    ask = AskForInput.text(
        prompt="Tags / extra context (optional)",
        default_answer="",
    )
    s.add(
        ChooseFromMenu(
            prompt="Continue or done?",
            cases=[
                (
                    "Add metadata",
                    [
                        ask,
                        SetVariable(name="Metadata", input=ask),
                    ],
                ),
                (
                    "Done",
                    [
                        SetVariable(
                            name="Metadata",
                            input=GetText(text=""),
                        ),
                    ],
                ),
            ],
        )
    )


def _add_push(s: Shortcut) -> None:
    """Stamp a filename then PUT markdown + audio to the GitHub Files API."""
    # Millisecond precision avoids collisions when two recordings land in the
    # same second (GitHub returns 422 if the path already exists with no sha).
    stamp = s.add(
        FormatDate(
            input=CurrentDate,
            date_style="Custom",
            custom_format="yyyy-MM-dd_HH-mm-ss-SSS",
        )
    )
    s.set("Stamp", stamp)

    base_text = s.add(
        GetText(
            text=Text(
                "voice_{stamp}",
                substitutions={"stamp": NamedVar("Stamp")},
            )
        )
    )
    s.set("Base", base_text)

    # --- markdown ---
    md_text = s.add(
        GetText(
            text=Text(
                "---\n"
                "date: {stamp}\n"
                "source: voice\n"
                "author: human\n"
                "status: inbox\n"
                "tags: [note/jot, voice]\n"
                "---\n"
                "\n"
                "{transcript}\n"
                "\n"
                "{metadata}\n"
                "\n"
                "![[{base}.m4a]]",
                substitutions={
                    "stamp": NamedVar("Stamp"),
                    "transcript": NamedVar("Transcript"),
                    "metadata": NamedVar("Metadata"),
                    "base": NamedVar("Base"),
                },
            )
        )
    )
    s.set("Markdown", md_text)

    md_encoded = s.add(Base64Encode(input=NamedVar("Markdown")))
    md_stripped = s.add(
        TextReplace(input=md_encoded, find=r"\s+", replace="", regex=True)
    )
    s.set("MdB64", md_stripped)

    audio_encoded = s.add(Base64Encode(input=NamedVar("Audio")))
    audio_stripped = s.add(
        TextReplace(input=audio_encoded, find=r"\s+", replace="", regex=True)
    )
    s.set("AudioB64", audio_stripped)

    auth_header = Text("Bearer {tok}", substitutions={"tok": NamedVar("Token")})
    github_headers = {
        "Authorization": auth_header,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # PUT 1: markdown note
    md_url = s.add(
        GetText(
            text=Text(
                "https://api.github.com/repos/{repo}/contents/jots/voice/{base}.md",
                substitutions={
                    "repo": NamedVar("Repo"),
                    "base": NamedVar("Base"),
                },
            )
        )
    )
    s.add(
        DownloadURL(
            url=md_url,
            method="PUT",
            headers=github_headers,
            body={
                "message": Text(
                    "voice: {base}",
                    substitutions={"base": NamedVar("Base")},
                ),
                "content": NamedVar("MdB64"),
            },
            body_type="JSON",
        )
    )

    # PUT 2: raw audio binary
    audio_url = s.add(
        GetText(
            text=Text(
                "https://api.github.com/repos/{repo}/contents/jots/voice/raw_audio/{base}.m4a",
                substitutions={
                    "repo": NamedVar("Repo"),
                    "base": NamedVar("Base"),
                },
            )
        )
    )
    s.add(
        DownloadURL(
            url=audio_url,
            method="PUT",
            headers=github_headers,
            body={
                "message": Text(
                    "voice-audio: {base}",
                    substitutions={"base": NamedVar("Base")},
                ),
                "content": NamedVar("AudioB64"),
            },
            body_type="JSON",
        )
    )

    s.add(
        ShowNotification(
            title="Voice Note To Git",
            body=Text(
                "Voice note pushed: {base}",
                substitutions={"base": NamedVar("Base")},
            ),
        )
    )


def build() -> Shortcut:
    """Compose the Voice Note To Git shortcut."""
    s = Shortcut(name="Voice Note To Git", surfaces=["quick-action"])
    _add_config(s)
    _add_record_and_transcribe(s)
    _add_metadata_gate(s)
    _add_push(s)
    return s


def main() -> None:
    s = build()
    out = Path.home() / "Desktop" / f"{s.name}.shortcut"
    s.save_signed(out)
    print(f"wrote {out}")
    print(
        "\nImport, fill in the two Setup prompts (Token + Repo), then run."
        "\nThe shortcut records immediately, transcribes on-device,"
        "\nand pushes markdown + audio to jots/voice/ in your repo."
    )


if __name__ == "__main__":
    main()
