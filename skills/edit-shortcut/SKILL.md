---
name: edit-shortcut
description: Modify an existing .shortcut file. Lift it via Shortcut.from_file(), change what the user wants, re-sign, drop the new file in place. Triggers when user asks to "edit", "change", "modify", or "tweak" an existing shortcut, or asks "can you update this shortcut to also X".
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
---

# Edit Shortcut

Modify an existing Apple `.shortcut` file. The library at
`~/personal/shortcut-lib` lifts the file into an editable `Shortcut`
wrapper, lets you make targeted changes, then re-signs.

## When to use

User says any of:
- "edit my shortcut at <path>"
- "change <name> to also …"
- "update this shortcut so it …"
- "tweak the shortcut to …"
- "remove the X step from this shortcut"
- "add X to my shortcut"

If the user wants a brand-new shortcut, use the `make-shortcut` skill instead.
If the user just wants to understand what a shortcut does without changing it,
use the `decode-shortcut` skill instead.

## Mandatory pre-reading

1. `~/personal/shortcut-lib/docs/roadmap.md`.
2. `~/personal/shortcut-lib/docs/format.md`.
3. The schema surface: `cd ~/personal/shortcut-lib && uv run python scripts/print_actions.py`.

Plus the vault notes most relevant to the edit:
- `~/Documents/FMP/tech/Apple_Shortcuts/Design_Intent.md` — Apple's data-flow model.
- `~/Documents/FMP/tech/Apple_Shortcuts/Magic_Variables.md` — if you'll touch variable references.
- `~/Documents/FMP/tech/Apple_Shortcuts/Control_Flow.md` — if you'll add or remove If / Repeat / Menu blocks (mind GroupingIdentifier pairing).
- `~/Documents/FMP/tech/Apple_Shortcuts/Action_Reference_Index.md` — to navigate the rest.

## Workflow

### Step 1 — Locate the file

If the user gave a path, use it. If not, ask. Common locations:
- `~/Desktop/<Name>.shortcut` — recently authored
- `~/Documents/<Name>.shortcut` — manual exports

### Step 2 — Decode and present a digest

```sh
cd ~/personal/shortcut-lib
uv run shortcut-decode "<path>" --format buzz
```

The buzz format is compact — one line per action, indented for control
flow, variables as `${Name}`. Show this output to the user and confirm
which lines they want changed.

If the user's edit is structural enough that the digest is ambiguous,
also produce the XML for reference:

```sh
uv run shortcut-decode "<path>" --format xml -o /tmp/<name>.xml
```

### Step 3 — Decide on edit strategy

There are three viable strategies, in increasing order of cost:

**Strategy A — Lift and mutate via `Shortcut.from_file()`.** The
preferred V1.5 path. Lifts the file into an editable `Shortcut` wrapper;
you mutate `RawAction.raw_params` dicts, call `save_signed`. Works for
any action including ones not yet modelled in our schema. Safe — the
`_extra` round-trip mechanism (see below) preserves top-level keys you
don't touch.

```python
from shortcut_lib.builder import Shortcut

s = Shortcut.from_file("path/to/some.shortcut")
# s.actions is a list of RawAction; s.setup_questions, s.surfaces,
# s.icon_glyph, s.icon_color etc. are populated from the file.
# s._extra holds any top-level WFWorkflow* keys not covered by explicit
# attributes — they'll be re-emitted unchanged.
print(len(s.actions), "actions lifted")
# … make your changes (see "Surgical edits" below) …
s.save_signed("path/to/some.shortcut")
```

**Strategy B — Re-author from scratch.** When the change is substantive
enough that editing the existing action list would be harder than
writing the desired result fresh, decode to understand the structure
then re-author using the typed schema. Use the decoded buzz as the spec
and cross-reference `make-shortcut/SKILL.md` for the authoring pattern.

**Strategy C — Hybrid splice.** Lift via `from_file()`, identify the
unchanged prefix/suffix of `s.actions`, splice in newly-authored typed
actions in the middle. Mix of `RawAction` (unchanged, lifted) and typed
`Action` subclasses (the new additions) is fine — both go through
`s.add()` the same way.

Pick Strategy A by default. Only escalate if the change can't be
expressed as a small dict mutation.

### Step 4 — Apply and verify

After the edit, re-decode the new file and run buzz format:

```sh
uv run shortcut-decode "<path>" --format buzz
```

Diff against the original digest in your head; the change should match
what the user asked for and only that. Then confirm the test suite is
still clean:

```sh
cd ~/personal/shortcut-lib
uv run pytest
```

### Step 5 — Hand off

Tell the user the path. If the edit was non-trivial, ask them to run it
once before deciding it's done — `shortcuts run "<Name>"` on macOS.

---

## Lifting a shortcut — `Shortcut.from_file()`

`Shortcut.from_file(path)` is the entry point for the lift→inspect→modify→re-emit
flow. It calls `decode_file(path)` internally and builds a `Shortcut`
wrapper from the resulting workflow dict.

```python
from shortcut_lib.builder import Shortcut

s = Shortcut.from_file("~/Desktop/My Shortcut.shortcut")
```

After lifting:

| Attribute | What it contains |
|---|---|
| `s.actions` | `list[RawAction]` — one per entry in `WFWorkflowActions` |
| `s.setup_questions` | `list[ImportQuestion]` — lifted from `WFWorkflowImportQuestions` |
| `s.surfaces` | List of `WFWorkflowTypes` strings from the file |
| `s.icon_glyph`, `s.icon_color` | Icon glyph number and colour from the file |
| `s.accepted_input`, `s.output_classes` | Content-item class lists |
| `s._extra` | Any top-level `WFWorkflow*` keys not covered by the attributes above |

Actions are `RawAction` instances — the typed schema layer is not reverse-applied.
This means every action works, including identifiers not yet modelled in the lib.

### The `_extra` round-trip guarantee

When you load a `.shortcut` via `Shortcut.from_file()`, any top-level
`WFWorkflow*` keys not represented by an explicit `Shortcut` attribute
are captured into `_extra`. On `to_workflow()` / `save_signed()`, those
keys are re-emitted unchanged (via `out.update(self._extra)`).

**What this means for edits:** You can safely change anything the lib
understands (`icon_glyph`, `surfaces`, `accepted_input`, `output_classes`,
`setup_questions`, the `actions` list) and the full top-level dict passes
through for everything else. You do not need to audit or preserve
`WFWorkflowNoInputBehavior`, `WFQuickActionSurfaces`, `WFWorkflowClientVersion`,
or any other key you didn't touch.

Exception: `WFWorkflowImportQuestions` is lifted into `setup_questions`,
not into `_extra`. Editing `setup_questions` after a lift is supported —
the modified list is re-serialised on emit.

---

## Surgical edits via `RawAction` mutation

Lifted actions are `RawAction(raw_identifier, raw_params)`. The
`raw_params` dict is a direct copy of `WFWorkflowActionParameters` from
the plist. Edits are plain dict mutations.

### Find a specific action

Walk `s.actions` and match by `raw_identifier`:

```python
for i, action in enumerate(s.actions):
    if action.raw_identifier == "is.workflow.actions.urlencode":
        print(i, action.raw_params)
```

### Replace a parameter value

Mutate `raw_params` directly:

```python
for action in s.actions:
    if action.raw_identifier == "is.workflow.actions.notification":
        action.raw_params["WFNotificationActionBody"] = "New body text"
        break
```

### Drop an action

```python
# Remove the action at index i
del s.actions[i]
```

Removing an action that is part of a control-flow pair (e.g. an `If`
head without its `Otherwise` / `EndIf`) will corrupt the workflow. Read
`Control_Flow.md` and inspect the GroupingIdentifier UUIDs before
dropping control-flow actions.

### Append a new typed action

Typed actions can be mixed with `RawAction` instances — add them via
`s.add()` exactly as in a from-scratch workflow:

```python
from shortcut_lib.schema.actions.show_notification import ShowNotification

s.add(ShowNotification(title="Done", body="All steps complete."))
```

### Splice typed actions into the middle

Replace a slice or insert at a position by modifying `s.actions`
directly after adding via `s.add()`. Because `s.add()` appends to the
end, build the new actions first then re-order:

```python
from shortcut_lib.schema.actions.show_result import ShowResult

new_action = s.add(ShowResult(text="Finished."))
# Move it to position 3 (before the existing action at index 3)
s.actions.remove(new_action)
s.actions.insert(3, new_action)
```

---

## Re-author from scratch (Strategy B)

Sometimes the cleanest edit is: decode → understand the structure via
buzz output → re-author from scratch using the typed schema. This avoids
fighting with `raw_params` dicts and gets you full type-checking and
factory-method ergonomics.

See `make-shortcut/SKILL.md` for the full authoring pattern, typed-handle
variable wiring, and credential setup via `ask_text_on_import`.

---

## Decode for inspection only

If the user just wants to know what a shortcut does — without making any
changes — use the `decode-shortcut` skill. It runs:

```sh
uv run shortcut-decode "<path>" --format buzz
```

and presents a human-readable digest. The `edit-shortcut` skill builds
on the same decoder, but you don't need the full edit flow just to
inspect.

---

## Constraints

- **Don't break unrelated actions.** When mutating a dict in place,
  preserve everything you didn't touch. UUIDs, GroupingIdentifiers, and
  inert parameters all matter. The `_extra` round-trip guarantees the
  top-level dict, but within `WFWorkflowActions` you own what you edit.
- **Don't re-sign blindly.** If `shortcuts sign` fails, surface the
  error. Don't bypass with `--no-verify` or analogues.
- **Variable references can break.** Renaming a variable means finding
  every reference to it in templated strings (`attachmentsByRange`),
  variable tokens (`OutputUUID`, `VariableName`), and condition inputs.
- **Unmodelled actions are fine.** `Shortcut.from_file()` lifts every
  action as a `RawAction` regardless of whether the lib has a typed
  model for it. Direct dict edits still work — the dict is valid without
  our type knowledge.
- **Setup questions after lift.** `setup_questions` is lifted from
  `WFWorkflowImportQuestions`. If the shortcut used import prompts,
  they'll be in `s.setup_questions` and re-serialised on emit. Editing
  them is supported; don't also add a `WFWorkflowImportQuestions` key
  to `_extra` or you'll get a duplicate on re-emit.
