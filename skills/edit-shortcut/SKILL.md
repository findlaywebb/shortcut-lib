---
name: edit-shortcut
description: Modify an existing .shortcut file. Decode it, change what the user wants, re-sign, drop the new file in place. Triggers when user asks to "edit", "change", "modify", or "tweak" an existing shortcut, or asks "can you update this shortcut to also X".
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
`~/personal/shortcut-lib` decodes the file to a workflow dict, lets you
make targeted changes, then re-signs.

## When to use

User says any of:
- "edit my shortcut at <path>"
- "change <name> to also …"
- "update this shortcut so it …"
- "tweak the shortcut to …"
- "remove the X step from this shortcut"
- "add X to my shortcut"

If the user wants a brand-new shortcut, use the `make-shortcut` skill instead.

## Mandatory pre-reading

Same as `make-shortcut`:
1. `~/personal/shortcut-lib/docs/roadmap.md`.
2. `~/personal/shortcut-lib/docs/format.md`.
3. The schema registry: `cd ~/personal/shortcut-lib && uv run python -c "from shortcut_lib.schema import list_actions; import json; print(json.dumps(list_actions(), indent=2))"`.

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

**Strategy A — Direct dict edit.** For surgical changes (rename a
variable, change a parameter value, swap a string), load the dict,
mutate it, re-encode. Cheapest. Safe.

```python
from shortcut_lib import decode_file, sign_to_file
decoded = decode_file("/Users/.../X.shortcut")
# walk decoded.workflow["WFWorkflowActions"], find your edit, mutate
sign_to_file(decoded.workflow, "/Users/.../X.shortcut")
```

**Strategy B — Re-author from the decoded shape.** When the change is
substantive (insert several actions, restructure control flow), it may
be cleaner to write the desired result fresh using `Shortcut(...)` and
the schema. Use the decoded buzz as the spec.

**Strategy C — Hybrid.** Decode, identify the unchanged prefix/suffix
of the action list, splice in newly-authored actions in the middle.
Useful when the user only wants to add a step.

Pick A by default. Only escalate if the change can't be expressed as a
small mutation.

### Step 4 — Apply and verify

After the edit, re-decode the new file and run buzz format:

```sh
uv run shortcut-decode "<path>" --format buzz
```

Diff against the original digest in your head; the change should match
what the user asked for and only that.

### Step 5 — Hand off

Tell the user the path. If the edit was non-trivial, ask them to run it
once before deciding it's done — `shortcuts run "<Name>"` on macOS.

## Constraints

- **Don't break unrelated actions.** When mutating a dict in place,
  preserve everything you didn't touch. UUIDs, GroupingIdentifiers,
  inert parameters all matter.
- **Don't re-sign blindly.** If `shortcuts sign` fails, surface the
  error. Don't bypass with `--no-verify` or analogues.
- **Variable references can break.** Renaming a variable means finding
  every reference to it in templated strings (`attachmentsByRange`),
  variable tokens (`OutputUUID`, `VariableName`), and condition inputs.
- **If a shortcut uses unsupported actions.** Some actions in the
  user's file may not be modelled in our schema. Direct dict edits
  still work — the dict is fine without our type knowledge.
