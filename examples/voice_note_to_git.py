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


def _add_record_and_transcribe(s: Shortcut) -> tuple[NamedVar, NamedVar]:
    """Record audio then transcribe it; store both as named variables.

    Returns:
        Tuple of (audio, transcript) typed handles for use downstream.
    """
    audio = s.add(RecordAudio(start="Immediately"))
    audio_var = s.set("Audio", audio)

    transcript = s.add(TranscribeAudio(audio_file=audio_var))
    transcript_var = s.set("Transcript", transcript)
    return audio_var, transcript_var


def _add_metadata_gate(s: Shortcut) -> NamedVar:
    """Prompt for optional metadata via a two-case ChooseFromMenu.

    Both cases assign the Metadata variable so downstream template code
    can reference it unconditionally. "Add metadata" prompts the user for
    tags or context; "Done" writes an empty string.

    The branch bodies are constructed as plain action lists outside the
    builder's ``s.set()`` path, so Metadata is referenced by name string
    downstream — this is intentional for cross-scope control-flow bodies.

    Returns:
        Typed handle for the Metadata variable.
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
    # NamedVar string retained: Metadata is set inside ChooseFromMenu branch
    # bodies constructed outside s.set(), so a typed handle is not available
    # from this call site.
    return NamedVar("Metadata")


def _add_push(
    s: Shortcut,
    audio_var: NamedVar,
    transcript_var: NamedVar,
    metadata_var: NamedVar,
    token: NamedVar,
    repo: NamedVar,
) -> None:
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
    stamp_var = s.set("Stamp", stamp)

    base_text = s.add(
        GetText(
            text=Text(
                "voice_{stamp}",
                substitutions={"stamp": stamp_var},
            )
        )
    )
    base_var = s.set("Base", base_text)

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
                    "stamp": stamp_var,
                    "transcript": transcript_var,
                    "metadata": metadata_var,
                    "base": base_var,
                },
            )
        )
    )
    markdown_var = s.set("Markdown", md_text)

    md_encoded = s.add(Base64Encode(input=markdown_var))
    md_stripped = s.add(
        TextReplace(input=md_encoded, find=r"\s+", replace="", regex=True)
    )
    md_b64 = s.set("MdB64", md_stripped)

    audio_encoded = s.add(Base64Encode(input=audio_var))
    audio_stripped = s.add(
        TextReplace(input=audio_encoded, find=r"\s+", replace="", regex=True)
    )
    audio_b64 = s.set("AudioB64", audio_stripped)

    auth_header = Text("Bearer {tok}", substitutions={"tok": token})
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
                    "repo": repo,
                    "base": base_var,
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
                    substitutions={"base": base_var},
                ),
                "content": md_b64,
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
                    "repo": repo,
                    "base": base_var,
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
                    substitutions={"base": base_var},
                ),
                "content": audio_b64,
            },
            body_type="JSON",
        )
    )

    s.add(
        ShowNotification(
            title="Voice Note To Git",
            body=Text(
                "Voice note pushed: {base}",
                substitutions={"base": base_var},
            ),
        )
    )


def build() -> Shortcut:
    """Compose the Voice Note To Git shortcut."""
    s = Shortcut(name="Voice Note To Git", surfaces=["quick-action"])
    token, repo = _add_config(s)
    audio_var, transcript_var = _add_record_and_transcribe(s)
    metadata_var = _add_metadata_gate(s)
    _add_push(s, audio_var, transcript_var, metadata_var, token, repo)
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
