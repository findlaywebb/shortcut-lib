"""Quick Task → Daily Note: fast-capture from macOS Spotlight.

V1 simplification: writes one file per task at
``daily/<yyyy-MM-dd>/task_<HH-mm-ss-SSS>.md`` rather than appending to a
single daily-tasks file.  Separate per-task files mean no GET-then-PUT-with-sha
dance (FU-8) is needed: every PUT creates a new path, so sha collisions are
impossible.  V1.5 will ship the GET-then-PUT pattern (FU-8) to append to a
single daily file instead.

Surface: macOS Spotlight (``WFWorkflowTypeShowInSearch``).  Run the shortcut
by name from Spotlight (Cmd-Space → "Quick Task" → Enter) or by assigning it
a keyboard shortcut in System Settings → Keyboard → Shortcuts.

Pipeline:

    AskForInput (task text)
      -> FormatDate x2 (date directory + ms-precision stamp)
      -> GetText (markdown content)
      -> Base64Encode + TextReplace (strip whitespace for GitHub API)
      -> DownloadURL PUT (daily/<Day>/task_<Stamp>.md)
      -> ShowNotification ("Task added: <text>")

Token + repo are collected via Setup prompts shown at import time (FU-9).
Never bake a real PAT into the signed ``.shortcut`` file.

Usage:
    uv run python examples/spotlight_quick_task.py

Drops ``Quick Task.shortcut`` on ~/Desktop.  Import into Shortcuts, fill in
the two Setup prompts (GitHub PAT and repo), then run from Spotlight.
"""

from __future__ import annotations

from pathlib import Path

from shortcut_lib.builder import Shortcut
from shortcut_lib.schema import NamedVar, Text
from shortcut_lib.schema.actions.ask import AskForInput
from shortcut_lib.schema.actions.base64_encode import Base64Encode
from shortcut_lib.schema.actions.download_url import DownloadURL
from shortcut_lib.schema.actions.format_date import FormatDate
from shortcut_lib.schema.actions.get_text import GetText
from shortcut_lib.schema.actions.show_notification import ShowNotification
from shortcut_lib.schema.actions.text_replace import TextReplace
from shortcut_lib.schema.values import CurrentDate

# WFWorkflowTypeShowInSearch — verified against samples/decoded/dictionary.xml
# and samples/decoded/get_contents_of_url.xml; this string makes the shortcut
# appear in macOS Spotlight and the Shortcuts search bar.  Not in
# SURFACE_TO_TYPE; passes through verbatim per builder.py's string-passthrough
# guarantee.
_SPOTLIGHT_SURFACE = "WFWorkflowTypeShowInSearch"


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


def _add_input(s: Shortcut) -> NamedVar:
    """Prompt the user for the task text and store as ``TaskText``.

    Returns:
        Typed handle for the TaskText variable.
    """
    task = s.add(AskForInput.text(prompt="Task text"))
    task_text = s.set("TaskText", task)
    return task_text


def _add_datestamp(s: Shortcut) -> tuple[NamedVar, NamedVar]:
    """Compute date directory and ms-precision stamp; store as named vars.

    Returns:
        Tuple of (day, stamp) typed handles for use downstream.
    """
    # Day: directory component — "2026-05-09"
    day = s.add(
        FormatDate(
            input=CurrentDate,
            date_style="Custom",
            custom_format="yyyy-MM-dd",
        )
    )
    day_var = s.set("Day", day)

    # Stamp: filename component with ms precision — "14-37-22-843"
    # Millisecond precision eliminates filename collisions for rapid-fire runs.
    stamp = s.add(
        FormatDate(
            input=CurrentDate,
            date_style="Custom",
            custom_format="HH-mm-ss-SSS",
        )
    )
    stamp_var = s.set("Stamp", stamp)
    return day_var, stamp_var


def _add_content(
    s: Shortcut,
    task_text: NamedVar,
    stamp_var: NamedVar,
) -> NamedVar:
    """Build the markdown task file content and store as ``ContentB64``.

    Returns:
        Typed handle for the ContentB64 variable.
    """
    # Tiny frontmatter + a single checkbox task line.  Keeping the schema
    # minimal so vault tooling (dataview, tasks plugin) can query it.
    content_text = s.add(
        GetText(
            text=Text(
                "---\ndate: {stamp}\nsource: spotlight\nstatus: open\ntags: [task]\n---\n\n- [ ] {task}",
                substitutions={
                    "stamp": stamp_var,
                    "task": task_text,
                },
            )
        )
    )
    content_var = s.set("Content", content_text)

    # Base64-encode then strip whitespace — GitHub Files API requires raw
    # base64 with no line-breaks or trailing newlines.
    encoded = s.add(Base64Encode(input=content_var))
    stripped = s.add(
        TextReplace(
            input=encoded,
            find=r"\s+",
            replace="",
            regex=True,
        )
    )
    content_b64 = s.set("ContentB64", stripped)
    return content_b64


def _add_push(
    s: Shortcut,
    task_text: NamedVar,
    day_var: NamedVar,
    stamp_var: NamedVar,
    content_b64: NamedVar,
    token: NamedVar,
    repo: NamedVar,
) -> None:
    """PUT the task file to GitHub and notify the user."""
    # Path: daily/<Day>/task_<Stamp>.md
    # Each combination is unique — ms-precision stamp means concurrent runs
    # from the same second don't collide.
    url_text = s.add(
        GetText(
            text=Text(
                "https://api.github.com/repos/{repo}/contents/daily/{day}/task_{stamp}.md",
                substitutions={
                    "repo": repo,
                    "day": day_var,
                    "stamp": stamp_var,
                },
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
                "message": Text(
                    "Add task {stamp}",
                    substitutions={"stamp": stamp_var},
                ),
                "content": content_b64,
            },
            body_type="JSON",
        )
    )

    s.add(
        ShowNotification(
            title="Task added",
            body=Text(
                "{task}",
                substitutions={"task": task_text},
            ),
        )
    )


def build() -> Shortcut:
    """Compose the Quick Task shortcut and return the Shortcut object."""
    s = Shortcut(
        name="Quick Task",
        surfaces=[_SPOTLIGHT_SURFACE],
    )
    token, repo = _add_config(s)
    task_text = _add_input(s)
    day_var, stamp_var = _add_datestamp(s)
    content_b64 = _add_content(s, task_text, stamp_var)
    _add_push(s, task_text, day_var, stamp_var, content_b64, token, repo)
    return s


def main() -> None:
    """Build and sign the shortcut to ~/Desktop/Quick Task.shortcut."""
    s = build()
    out = Path.home() / "Desktop" / f"{s.name}.shortcut"
    s.save_signed(out)
    print(f"wrote {out}")
    print(
        "\nImport into Shortcuts, fill in the two Setup prompts "
        "(GitHub PAT and repo), then invoke from Spotlight with Cmd-Space."
    )


if __name__ == "__main__":
    main()
