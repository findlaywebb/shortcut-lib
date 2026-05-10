---
name: make-shortcut
description: Author an Apple Shortcut from a description. Uses ~/personal/shortcut-lib to scaffold Python that emits a signed .shortcut file the user can drag into Shortcuts.app. Triggers when user says "make a shortcut", "build a shortcut", "create a shortcut for X", or asks for an iOS/macOS shortcut.
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
---

# Make Shortcut

Author an Apple Shortcuts file from a description. The library lives at
`~/personal/shortcut-lib`. You write Python that uses its schema, run it,
and the resulting `.shortcut` lands on `~/Desktop/` for the user to drag
into Shortcuts.app.

## When to use

User says any of:
- "make a shortcut that…"
- "build me a shortcut for…"
- "create an iOS/Mac shortcut…"
- "I want a shortcut to…"

## Mandatory pre-reading

Before writing any Python, read in this order:

1. `~/personal/shortcut-lib/docs/roadmap.md` — vision and current state.
2. `~/personal/shortcut-lib/docs/format.md` — wire format anatomy.
3. The lib's full authoring surface — leaf actions, control flow, and value types: `cd ~/personal/shortcut-lib && uv run python scripts/print_actions.py`. (Or call `list_actions`, `list_control_flow`, `list_values` from `shortcut_lib.schema`.)

Then read the vault notes relevant to the shortcut's surface area:

- `~/Documents/FMP/tech/Apple_Shortcuts/Design_Intent.md` — Apple's mental model: input/output, content graph, surfaces.
- `~/Documents/FMP/tech/Apple_Shortcuts/Magic_Variables.md` — when the shortcut uses CurrentDate / Clipboard / Ask / RepeatItem / etc.
- `~/Documents/FMP/tech/Apple_Shortcuts/Control_Flow.md` — when nesting If / Repeat / Choose-from-Menu.
- `~/Documents/FMP/tech/Apple_Shortcuts/Content_Item_Classes.md` — when the shortcut accepts share-sheet input or produces typed output.
- `~/Documents/FMP/tech/Apple_Shortcuts/URL_Schemes.md` — when integrating with `shortcuts://` or x-callback-url.
- `~/Documents/FMP/tech/Apple_Shortcuts/Personal_Automation.md` — when the user asks for time / location / app-triggered automation.
- `~/Documents/FMP/tech/Apple_Shortcuts/iOS_26_Highlights.md` — when using Apple Intelligence (UseModel) or Writing Tools.
- `~/Documents/FMP/tech/Apple_Shortcuts/Action_Reference_Index.md` — navigation hub when you don't know which note covers something.

If the shortcut concept matches an existing `samples/*.shortcut`, decode
it for reference: `uv run shortcut-decode samples/<name>.shortcut --format buzz`.

## Workflow

### Step 1 — Clarify

If the user's description is missing critical pieces, ask. Examples:
- "Where should the result go — clipboard, notification, file?"
- "Does it need user input (text, number, date)?"
- "Should it run from the share sheet, the watch, a widget?"

Don't guess on hard-to-undo branches. Do guess on small details.

### Step 2 — Choose actions

Pick action classes from the registry. If a needed action isn't yet
implemented in the lib (`list_actions()` won't show it), tell the user
and offer one of:

- A — implement the action now (only if simple — read the Jellycore facts at `data/jellycore_facts.json` and at least one decoded sample that uses it).
- B — pick a workable alternative.
- C — defer until that action lands.

### Step 3 — Credentials: use `ask_text_on_import`

If the shortcut needs a credential (GitHub PAT, API key, repo path, or
any other user-specific secret), collect it via a Setup prompt shown at
import time. **Never bake a real secret into the signed `.shortcut` file.**

```python
token_text = s.ask_text_on_import(
    question="Your GitHub personal access token (fine-grained, contents: read+write)",
    default="REPLACE_WITH_GITHUB_PAT",
)
token = s.set("Token", token_text)
```

`ask_text_on_import` adds a `GetText` action wired as a
`WFWorkflowImportQuestions` entry. When the user imports the shortcut,
Shortcuts.app shows a form with your `question` pre-filled with
`default`. The answer flows into the `GetText` slot and from there into
`token` — a typed `NamedVar` handle that downstream code references
directly.

The import flow is: **drag-in → fill prompts → tap Import → run**. No
manual editing of actions required.

### Step 4 — Write Python

Write a script under `~/personal/shortcut-lib/examples/<name>.py` (or wherever fits).

Pattern (short pipeline, no logical phases — inline everything in `build()`):

```python
from pathlib import Path
from shortcut_lib.builder import Shortcut
from shortcut_lib.schema import Text
from shortcut_lib.schema.actions.ask import AskForInput
from shortcut_lib.schema.actions.show_notification import ShowNotification

def build() -> Shortcut:
    s = Shortcut(name="My Shortcut", surfaces=["share"])
    count = s.add(AskForInput.number(prompt="How many?", allows_decimal=False))
    s.add(ShowNotification(title="Count", body=Text("You said {n}", substitutions={"n": count})))
    return s

if __name__ == "__main__":
    out = Path.home() / "Desktop" / f"{build().name}.shortcut"
    build().save_signed(out)
    print(f"wrote {out}")
```

When the workflow has more than 3 logical phases, decompose into
`_add_<phase>` helpers rather than inlining everything. See the
Composition pattern section below.

### Step 5 — Run and verify

```sh
cd ~/personal/shortcut-lib
uv run python examples/<name>.py
```

Then run `uv run shortcut-decode ~/Desktop/<Name>.shortcut --format buzz`
to read back what was written. Sanity-check the variable wiring,
control-flow grouping, and parameter shapes. If the buzz output shows
unexpected empty values or wrong variable names, the error is a signal
to look at your `NamedVar` references — a typed handle returned by
`s.set(...)` is the correct fix, not a string you type by hand.

Then run `uv run pytest` to confirm the existing test suite is still
clean:

```sh
cd ~/personal/shortcut-lib
uv run pytest
```

### Step 6 — Hand off

Tell the user the file path. Quickest import on macOS:

```sh
open ~/Desktop/<Name>.shortcut
```

This prompts Shortcuts.app to import. Alternatively drag it. For macOS
testing once imported: `shortcuts run "<Name>"`.

## Typed handles — the recommended variable pattern

`Shortcut.set(name, value)` stores a variable **and returns a typed
handle** (`NamedVar`) that downstream code uses directly:

```python
# Preferred: capture the return value
note = s.set("Note", clipboard)
polished = s.set(
    "Polished",
    s.add(UseModel(prompt=Text("Polish:\n\n{n}", substitutions={"n": note}))),
)
```

The returned handle replaces the older two-step pattern:

```python
# Discouraged: discard the return, re-fetch by string key
s.add(SetVariable(name="Note", input=clipboard))
s.add(UseModel(prompt=Text("Polish:\n\n{n}", substitutions={"n": NamedVar("Note")})))
```

Both forms produce identical wire format. The difference is that a typo
in `NamedVar("Noet")` is a runtime empty-value bug on iOS; a typo in
the Python identifier `noet` is a `NameError` at static-check time.
This library's primary user is an LLM (you). Typed handles exist to make
your typos loud, not silent.

**Annotate explicitly if you want the type to read at the call site:**

```python
token: NamedVar[str] = s.set("Token", token_text)
```

## Factory methods on `AskForInput`

Prefer the type-specific factories over the direct constructor. They
expose only the parameters valid for that input type, so an invalid
combination is a `TypeError` at the call site, not a `SchemaError` after
construction:

```python
from shortcut_lib.schema.actions.ask import AskForInput

name   = s.add(AskForInput.text(prompt="Your name"))
count  = s.add(AskForInput.number(prompt="How many?", allows_decimal=True))
when   = s.add(AskForInput.datetime(prompt="When should this run?"))
site   = s.add(AskForInput.url(prompt="Target URL"))
```

`allows_decimal` and `allows_negative` are keyword arguments on
`.number()` only — passing them to `.text()` or any other factory is a
`TypeError` at the call site (Python's normal kwarg check), not a
deferred error. The direct constructor `AskForInput(input_type=..., ...)`
still works for runtime-determined input types.

## Composition pattern

Larger shortcuts decompose into Python helper functions that each accept
the builder and append actions to it. The result is one `Shortcut` object
and one emitted `.shortcut` file. **See
`~/personal/shortcut-lib/examples/vault_note_to_git.py` for the
canonical example** — `_add_config`, `_add_polish`, and `_add_push` each
take `s: Shortcut`; `build()` calls all three in sequence.

**Rule of thumb:** If the workflow has more than 3 logical phases,
decompose into `_add_<phase>(s: Shortcut)` helpers; otherwise inline
everything in `build()`. When a helper produces a value the next phase
needs, return it as a typed handle rather than relying on a string key.

Sketch using typed handles throughout:

```python
from shortcut_lib.builder import Shortcut
from shortcut_lib.schema import Text
from shortcut_lib.schema.actions.get_clipboard import GetClipboard
from shortcut_lib.schema.actions.use_model import UseModel
from shortcut_lib.schema.actions.show_notification import ShowNotification
from shortcut_lib.schema.values import NamedVar


def _add_config(s: Shortcut) -> tuple[NamedVar, NamedVar]:
    """Collect Token and Repo via Setup prompts shown at import time."""
    token_text = s.ask_text_on_import(
        question="Your GitHub personal access token",
        default="REPLACE_WITH_GITHUB_PAT",
    )
    token = s.set("Token", token_text)
    repo_text = s.ask_text_on_import(
        question="Target repo (owner/name)",
        default="owner/repo",
    )
    repo = s.set("Repo", repo_text)
    return token, repo


def _add_polish(s: Shortcut) -> NamedVar:
    """Read the clipboard, polish via Apple Intelligence, return typed handle."""
    clipboard = s.add(GetClipboard())
    note = s.set("Note", clipboard)
    polished = s.set(
        "Polished",
        s.add(
            UseModel(
                prompt=Text(
                    "Polish this note:\n\n{n}",
                    substitutions={"n": note},
                ),
                model="Apple Intelligence",
            )
        ),
    )
    return polished


def _add_notify(s: Shortcut, polished: NamedVar) -> None:
    """Show a success notification."""
    s.add(ShowNotification(title="Done", body=polished))


def build() -> Shortcut:
    s = Shortcut(name="Polish Note", surfaces=["share", "quick-action"])
    token, repo = _add_config(s)  # noqa: F841 — used in a real push step
    polished = _add_polish(s)
    _add_notify(s, polished)
    return s
```

Key points:
- `_add_config` returns typed handles so downstream phases reference `token`
  and `repo` as Python identifiers, not string keys.
- `_add_polish` returns a `NamedVar` so the next phase receives it as a
  typed argument, not a `NamedVar("Polished")` string it has to remember.
- `_add_notify` is void-returning — it doesn't produce a value the caller
  needs.
- `build()` sequences the phases; tests and `__main__` call only `build()`.

Helper functions are plain Python — no new concepts, no cross-file
linking, no extra import steps for the user. The entire workflow ships in
one `.shortcut` file.

`RunWorkflow` is still in the schema for the narrow case where a
*genuinely separate trigger* is required — Setup-only auth helpers or
iCloud-shared utilities where each shortcut lives independently on the
device. Do not use it to compose steps within a single logical workflow:
iOS reassigns shortcut UUIDs at import time, so any `workflow_identifier`
baked into a locally-signed `.shortcut` will not resolve after import,
and the user would have to re-select the target shortcut by hand.

## Editing existing shortcuts

For "decode → modify → re-encode" use `Shortcut.from_file(path)`. It
returns a Shortcut wrapper whose actions are `RawAction` instances —
mutate the dicts, call `save_signed(...)`. Works for any identifier
including ones not yet schema-modelled.

## Constraints

- **Use real Apple keys.** When a parameter isn't covered by an existing
  action class, verify against `samples/decoded/*.xml` before adding it.
  Jellycore's parameter names are hints, not ground truth.
- **Don't invent identifiers.** If you don't see the action in
  `list_actions()` or in a decoded sample, ask before guessing.
- **Run the script.** Don't claim a shortcut works until you've actually
  produced and inspected the file.
- **Respect surfaces.** If the user wants a watch shortcut, add `"watch"` to surfaces. Apple gates which actions work on which surface.
