# shortcut-lib

Author and decode Apple Shortcuts files programmatically. The library's primary
user is a well-prompted LLM (Claude Code); the human tells the LLM what shortcut
to build and the lib handles the wire format. V1 validated end-to-end on iPhone
(iOS 26.4.2 + Apple Intelligence) with a vault note → polish → GitHub commit
workflow on 2026-05-09.

**Status: V1 — used daily; v1.0 not yet tagged.**

---

## Status table

| Layer | State |
|-------|-------|
| Decode (AEA → AA → bplist) | Done — 20 public + 1 private sample |
| Encode + round-trip | Done — bplist + `shortcuts sign`; 917 tests incl. equivalence sweep |
| Schema: 61 leaf actions + 5 control-flow + 7 value types | Done — `RawAction` passthrough for the rest |
| Wire-format discipline | Done — `coerce_text_field` for every `WFTextTokenString` slot; envelope oracle at `data/observed_envelope_types.json` |
| Setup-section authoring (FU-9) | Done — `ask_on_import` / `ask_text_on_import` for import-time credentials |
| Real-target shortcuts | Done — 8 in `examples/`; vault-note-to-git on-device validated |
| Skills (make / edit / decode) | Done — in-repo at `skills/`, symlinked into `~/.claude/skills/` |
| MCP server | Done — 5 tools, 12-task eval harness, stdio entrypoint (see `docs/mcp.md`) |
| Licence + attribution | Done — GPL-3.0-or-later, `NOTICE`, `docs/sources.md` |

---

## Install

```sh
uv venv && uv pip install -e '.[dev]'
```

Requires macOS (uses the system `aea`, `aa`, and `shortcuts` binaries).

---

## Quickstart

Build a minimal shortcut, sign it, and drop it on the Desktop:

```python
from shortcut_lib.builder import Shortcut
from shortcut_lib.schema.actions.get_clipboard import GetClipboard
from shortcut_lib.schema.actions.show_notification import ShowNotification

s = Shortcut(name="Hello Clipboard")
clip = s.add(GetClipboard())
s.add(ShowNotification(title="Clipboard contents", body=clip.output()))
s.save_signed()  # drops Hello Clipboard.shortcut on ~/Desktop
```

Import the resulting `.shortcut` file into Shortcuts.app and run it —
it reads whatever is on your clipboard and shows it in a notification.

---

## Examples

Four real-target shortcuts live in `examples/`. All use the Setup-section
pattern (FU-9): token and repo are emitted as `WFWorkflowImportQuestions`
entries — Shortcuts shows them as a form at import time, with answers wired
into hidden `GetText` action slots. Never bake a real PAT into a signed file.

- **`vault_note_to_git.py`** — clipboard → Apple Intelligence polish → GitHub
  Files API PUT → notification. On-device validated: iPhone iOS 26.4.2 +
  Apple Intelligence, 2026-05-09. See `examples/VALIDATION_vault_note_to_git.md`
  for the setup and lessons learned.

- **`voice_note_to_git.py`** — record audio → on-device transcription →
  optional metadata via `ChooseFromMenu` → two GitHub PUTs (markdown +
  raw `.m4a` binary).

- **`spotlight_quick_task.py`** — `AskForInput` from macOS Spotlight → format
  timestamp → GitHub Files API PUT at `daily/<date>/task_<stamp>.md`.

- **`share_to_inbox.py`** — share-sheet trigger (`ActionExtension` surface);
  branches on URL vs text; writes a timestamped markdown file to `inbox/` in
  the target repo.

- **`note_to_github.py`** — clipboard text → GitHub Files API PUT. The
  simplest end-to-end GitHub-target example; compact single-function form
  with no helper decomposition.

---

## CLI

```sh
shortcut-decode path/to/foo.shortcut                   # XML plist to stdout
shortcut-decode path/to/foo.shortcut --format summary  # action breakdown
shortcut-decode path/to/foo.shortcut --format buzz     # LLM-readable digest
shortcut-decode path/to/foo.shortcut --format json -o foo.json
```

---

## Library

Decode an existing shortcut:

```python
from shortcut_lib import decode_file

decoded = decode_file("Start Pomodoro.shortcut")
print(decoded.signing_subject)      # leaf cert CN
for action in decoded.workflow["WFWorkflowActions"]:
    print(action["WFWorkflowActionIdentifier"])
```

---

## MCP server

`shortcut-lib` ships an optional [Model Context Protocol](https://modelcontextprotocol.io)
server so any MCP host (Claude Code, Claude Desktop, Cursor, ChatGPT) can
author shortcuts directly. The server is local stdio; the agent calls five
tools — discovery, schema inspection, dry-run validation, signed build,
and decode of an existing file.

```sh
uv pip install -e '.[mcp]'
claude mcp add shortcut-lib -- shortcut-mcp
```

Then in a Claude Code session: *"build me a shortcut that copies the
clipboard contents to a notification."* The agent inspects the registry,
constructs a `ShortcutSpec`, validates it, and lands a signed `.shortcut`
in `~/Downloads` (configurable via `SHORTCUT_LIB_MCP_OUTPUT_DIR`).

Full walkthrough in [`docs/mcp.md`](docs/mcp.md), including the agent-level
eval harness under `evals/mcp/`.

---

## See also

- `docs/format.md` — what we know about the `.shortcut` file format
- `docs/mcp.md` — MCP server, JSON spec, eval harness
- `docs/sources.md` — attribution to prior reverse-engineering work
- `docs/architecture-review/synthesis.md` — V1 design rationale (7-agent review)
- `docs/release-notes/v1.0.md` — V1 release notes
- `NOTICE` — formal third-party acknowledgements

---

## Licence

GPL-3.0-or-later. See `LICENSE` for the full text and `NOTICE` for
attribution of upstream public projects examined while building this lib.
