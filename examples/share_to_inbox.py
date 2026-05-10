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
        question="The repo to write inbox notes to (owner/name)",
        default="owner/repo-name",
    )
    repo = s.set("Repo", repo_text)
    return token, repo


def _add_capture(s: Shortcut) -> NamedVar:
    """Capture share-sheet input as the named variable ``Input``.

    Returns:
        Typed handle for the Input variable.
    """
    input_var = s.set("Input", ShortcutInput)
    return input_var


def _url_branch_body() -> list:
    """Return actions for the URL branch: YAML front-matter + bare URL body.

    Uses NamedVar string references intentionally: branch body actions are
    constructed outside the builder's s.set() path and run inside an If
    construct, so typed handles from the outer scope are not available at
    wire-format resolution time.
    """
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
    """Return actions for the text branch: YAML front-matter + blockquote.

    Uses NamedVar string references intentionally: branch body actions are
    constructed outside the builder's s.set() path and run inside an If
    construct, so typed handles from the outer scope are not available at
    wire-format resolution time.
    """
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


def _add_stamp(s: Shortcut) -> NamedVar:
    """Produce a millisecond-precision timestamp and store as ``Stamp``.

    Returns:
        Typed handle for the Stamp variable.
    """
    stamp = s.add(
        FormatDate(
            input=CurrentDate,
            date_style="Custom",
            custom_format="yyyy-MM-dd_HH-mm-ss-SSS",
        )
    )
    stamp_var = s.set("Stamp", stamp)
    return stamp_var


def _add_branch(s: Shortcut, input_var: NamedVar) -> NamedVar:
    """Branch on input type (URL heuristic) and set ``Body`` in each branch.

    Returns:
        Typed handle for the Body variable (set inside the If branches;
        NamedVar string retained as Body is written in cross-scope branch
        bodies constructed outside s.set()).
    """
    s.add(
        If(
            operand=input_var,
            op="contains",
            value="://",
            then=_url_branch_body(),
            otherwise=_text_branch_body(),
        )
    )
    # NamedVar string retained: Body is set inside If branch bodies
    # constructed outside s.set(), so a typed handle is not available
    # from this call site.
    return NamedVar("Body")


def _add_push(
    s: Shortcut,
    body_var: NamedVar,
    stamp_var: NamedVar,
    token: NamedVar,
    repo: NamedVar,
) -> None:
    """Compose filename, encode ``Body``, and PUT to the GitHub Files API."""
    base_text = s.add(
        GetText(
            text=Text(
                "share_{stamp}",
                substitutions={"stamp": stamp_var},
            )
        )
    )
    base_var = s.set("Base", base_text)

    encoded = s.add(Base64Encode(input=body_var))
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
                "https://api.github.com/repos/{repo}/contents/inbox/{base}.md",
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
                "message": Text(
                    "Add inbox note {base}",
                    substitutions={"base": base_var},
                ),
                "content": content_b64,
            },
            body_type="JSON",
        )
    )

    s.add(
        ShowNotification(
            title="Saved to inbox",
            body=Text(
                "inbox/{base}.md written to {repo}.",
                substitutions={"base": base_var, "repo": repo},
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
    token, repo = _add_config(s)
    input_var = _add_capture(s)
    stamp_var = _add_stamp(s)
    body_var = _add_branch(s, input_var)
    _add_push(s, body_var, stamp_var, token, repo)
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
