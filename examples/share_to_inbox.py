"""Share to Vault Inbox — share-sheet shortcut that routes content to GitHub.

Triggered from any app's share sheet when the user highlights text or shares
a URL. Branches on content type and writes a timestamped markdown file to
``inbox/`` in the target repository via the GitHub Files API.

Surface declaration
-------------------
Surfaces: ``share`` + ``quick-action`` (``ActionExtension`` + ``QuickActions``
in the wire format).

accepted_input content-item-class strings
------------------------------------------
These are the ``WFWorkflowInputContentItemClasses`` values. The four listed
below are **sample-confirmed** — they appear verbatim in
``samples/decoded/read_later.xml``, an extracted Apple share-sheet shortcut:

- ``WFStringContentItem``        — plain text (highlighted text from any app)
- ``WFRichTextContentItem``      — rich / formatted text (e.g. from Pages)
- ``WFURLContentItem``           — bare URL string
- ``WFSafariWebPageContentItem`` — a loaded Safari tab (URL + title)

Schema gap: Apple exposes type-specific magic variables for share-sheet inputs
(e.g. a variable that resolves only to the URL part of a Safari page share)
but the lib has not yet modelled these. The ``ShortcutInput`` magic var used
here resolves to the raw input as text, which is sufficient for the V1 URL
heuristic but means we can't extract page titles from Safari shares without
additional actions.

Branching heuristic
--------------------
``If(operand=NamedVar("Input"), op="contains", value="://", ...)`` detects
URLs. This is imperfect (non-URL text could contain ``://``; some legitimate
URLs use custom schemes without ``://``) but is the V1 approach used by
real Apple gallery shortcuts (see ``read_later.xml``, which tests for
``"http://"``). A more precise approach would use Apple's type-specific
magic vars — flagged as a schema gap above.

Pipeline
--------
1. Setup prompts (GitHub token + repo)
2. Capture ShortcutInput -> ``Input``
3. If/Else on ``Input`` containing ``"://"``
   - URL branch: front-matter with type=url, tag=bookmark
   - Text branch: front-matter with type=text, tag=highlight, body as blockquote
   Both branches set ``Body``.
4. FormatDate -> ``Stamp``; compose ``Base`` filename
5. Base64-encode ``Body``, strip whitespace -> ``ContentB64``
6. GitHub Files API PUT to ``inbox/<Base>.md``
7. ShowNotification

Usage:
    uv run python examples/share_to_inbox.py

Drops ``Share to Inbox.shortcut`` on ~/Desktop. Import into Shortcuts.app,
fill in the two Setup prompts (token + repo), then share any text or URL
from any app to trigger it.
"""

from __future__ import annotations

from pathlib import Path

from shortcut_lib.builder import Shortcut
from shortcut_lib.schema import If, NamedVar, ShortcutInput, Text
from shortcut_lib.schema.actions.base64_encode import Base64Encode
from shortcut_lib.schema.actions.download_url import DownloadURL
from shortcut_lib.schema.actions.format_date import FormatDate
from shortcut_lib.schema.actions.get_text import GetText
from shortcut_lib.schema.actions.set_variable import SetVariable
from shortcut_lib.schema.actions.show_notification import ShowNotification
from shortcut_lib.schema.actions.text_replace import TextReplace
from shortcut_lib.schema.values import CurrentDate

# Sample-confirmed content-item-class strings from read_later.xml.
# Controls which app share sheets surface this shortcut.
_ACCEPTED_INPUT: list[str] = [
    "WFStringContentItem",  # plain text (highlighted text, notes)
    "WFRichTextContentItem",  # rich / formatted text
    "WFURLContentItem",  # bare URL
    "WFSafariWebPageContentItem",  # Safari tab (URL + title)
]


def _add_config(s: Shortcut) -> None:
    """Collect Token and Repo via Setup prompts shown at import time."""
    token_text = s.ask_text_on_import(
        question="Your GitHub personal access token (fine-grained, contents: read+write)",
        default="REPLACE_WITH_GITHUB_PAT",
    )
    s.set("Token", token_text)
    repo_text = s.ask_text_on_import(
        question="The repo to write inbox notes to (owner/name)",
        default="owner/repo-name",
    )
    s.set("Repo", repo_text)


def _add_capture(s: Shortcut) -> None:
    """Capture share-sheet input as the named variable ``Input``."""
    s.set("Input", ShortcutInput)


def _url_branch_body() -> list:
    """Return actions for the URL branch: YAML front-matter + bare URL body."""
    stamp_ref = NamedVar("Stamp")
    input_ref = NamedVar("Input")
    body_text = GetText(
        text=Text(
            "---\n"
            "date: {stamp}\n"
            "source: share\n"
            "type: url\n"
            "status: inbox\n"
            "tags: [bookmark]\n"
            "---\n"
            "\n"
            "{input}",
            substitutions={"stamp": stamp_ref, "input": input_ref},
        )
    )
    body_var = SetVariable(name="Body", input=body_text)
    return [body_text, body_var]


def _text_branch_body() -> list:
    """Return actions for the text branch: YAML front-matter + blockquote."""
    stamp_ref = NamedVar("Stamp")
    input_ref = NamedVar("Input")
    body_text = GetText(
        text=Text(
            "---\n"
            "date: {stamp}\n"
            "source: share\n"
            "type: text\n"
            "status: inbox\n"
            "tags: [highlight]\n"
            "---\n"
            "\n"
            "> {input}",
            substitutions={"stamp": stamp_ref, "input": input_ref},
        )
    )
    body_var = SetVariable(name="Body", input=body_text)
    return [body_text, body_var]


def _add_stamp(s: Shortcut) -> None:
    """Produce a millisecond-precision timestamp and store as ``Stamp``."""
    stamp = s.add(
        FormatDate(
            input=CurrentDate,
            date_style="Custom",
            custom_format="yyyy-MM-dd_HH-mm-ss-SSS",
        )
    )
    s.add(SetVariable(name="Stamp", input=stamp))


def _add_branch(s: Shortcut) -> None:
    """Branch on input type (URL heuristic) and set ``Body`` in each branch."""
    s.add(
        If(
            operand=NamedVar("Input"),
            op="contains",
            value="://",
            then=_url_branch_body(),
            otherwise=_text_branch_body(),
        )
    )


def _add_push(s: Shortcut) -> None:
    """Compose filename, encode ``Body``, and PUT to the GitHub Files API."""
    base_text = s.add(
        GetText(
            text=Text(
                "share_{stamp}",
                substitutions={"stamp": NamedVar("Stamp")},
            )
        )
    )
    s.add(SetVariable(name="Base", input=base_text))

    encoded = s.add(Base64Encode(input=NamedVar("Body")))
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
                "https://api.github.com/repos/{repo}/contents/inbox/{base}.md",
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
                    "Add inbox note {base}",
                    substitutions={"base": NamedVar("Base")},
                ),
                "content": NamedVar("ContentB64"),
            },
            body_type="JSON",
        )
    )

    s.add(
        ShowNotification(
            title="Saved to inbox",
            body=Text(
                "inbox/{base}.md written to {repo}.",
                substitutions={"base": NamedVar("Base"), "repo": NamedVar("Repo")},
            ),
        )
    )


def build() -> Shortcut:
    """Build the Share to Inbox shortcut."""
    s = Shortcut(
        name="Share to Inbox",
        surfaces=["share", "quick-action"],
        accepted_input=_ACCEPTED_INPUT,
    )
    _add_config(s)
    _add_capture(s)
    _add_stamp(s)
    _add_branch(s)
    _add_push(s)
    return s


def main() -> None:
    s = build()
    out = Path.home() / "Desktop" / f"{s.name}.shortcut"
    s.save_signed(out)
    print(f"wrote {out}")
    print(
        "\nImport into Shortcuts.app, fill in the two Setup prompts "
        "(GitHub token + repo), then share any text or URL from any app."
    )


if __name__ == "__main__":
    main()
