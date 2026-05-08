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
3. `~/Documents/FMP/tech/Apple_Shortcuts/Design_Intent.md` — Apple's mental model.
4. `~/Documents/FMP/tech/Apple_Shortcuts/Magic_Variables.md` if the shortcut uses CurrentDate/Clipboard/etc.
5. The lib's available actions: `cd ~/personal/shortcut-lib && uv run python -c "from shortcut_lib.schema import list_actions; import json; print(json.dumps(list_actions(), indent=2))"`

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

### Step 3 — Write Python

Write a script under `~/personal/shortcut-lib/examples/<name>.py` (or wherever fits).

Pattern:

```python
from pathlib import Path
from shortcut_lib.builder import Shortcut
from shortcut_lib.schema import Text, NamedVar, CurrentDate, If
from shortcut_lib.schema.actions.ask import AskForInput
from shortcut_lib.schema.actions.show_notification import ShowNotification

def build() -> Shortcut:
    s = Shortcut(name="My Shortcut", surfaces=["share"])
    answer = s.add(AskForInput(prompt="What's up?"))
    s.add(ShowNotification(title="Hi", body=Text("You said: {x}", substitutions={"x": answer})))
    return s

if __name__ == "__main__":
    out = Path.home() / "Desktop" / f"{build().name}.shortcut"
    build().save_signed(out)
    print(f"wrote {out}")
```

### Step 4 — Run and verify

```sh
cd ~/personal/shortcut-lib
uv run python examples/<name>.py
```

Then run `uv run shortcut-decode ~/Desktop/<Name>.shortcut --format buzz`
to read back what was written. Sanity-check the variable wiring,
control-flow grouping, and parameter shapes.

### Step 5 — Hand off

Tell the user the file path. Quickest import on macOS:

```sh
open ~/Desktop/<Name>.shortcut
```

This prompts Shortcuts.app to import. Alternatively drag it. For macOS
testing once imported: `shortcuts run "<Name>"`.

## Composition pattern

Larger shortcuts decompose into helpers + an orchestrator, like Python
modules. **See `~/personal/shortcut-lib/examples/vault_note_to_git.py`
for a worked example** — a polish helper, a push helper, and a top-level
orchestrator linked via `RunWorkflow`.

Sketch:

```python
# Helper: takes text input via ShortcutInput, returns polished text
polish = Shortcut(name="Polish With LLM")
polish.add(SetVariable(name="Note", input=ShortcutInput))
# ... polish actions

# Orchestrator: composes helpers
main = Shortcut(name="Vault To Git")
text = main.add(GetClipboard())
polished = main.add(RunWorkflow(target=polish, input=text))
main.add(ShowNotification(body=polished))
```

Each helper is its own `.shortcut` file and gets imported separately.
Orchestrator references helpers by their `workflow_identifier` (set at
construction). This is the "module" pattern for Shortcuts.

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
