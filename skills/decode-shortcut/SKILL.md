---
name: decode-shortcut
description: Quick "what does this shortcut do" digest for any .shortcut file. Use when the user asks to "look at", "inspect", "read", "explain", or "describe" a shortcut, or asks "what does this shortcut do".
allowed-tools:
  - Bash
  - Read
---

# Decode Shortcut

Read an Apple `.shortcut` file and explain what it does in plain
language. Pure read-only — never modifies or signs.

## When to use

User says any of:
- "what does this shortcut do?"
- "explain <path>"
- "inspect <path>"
- "look at this .shortcut"
- "what's in <path>"

For modifications use `edit-shortcut`. For authoring, `make-shortcut`.

## Workflow

### Step 1 — Run the buzz digest

```sh
cd ~/personal/shortcut-lib
uv run shortcut-decode "<path>" --format buzz
```

This is the LLM-readable summary: header (surfaces, action count),
indented control flow, variables as `${Name}`, templated strings
inlined. Roughly 10× smaller than the XML.

### Step 2 — Translate to natural language

Read the buzz output and explain to the user:

1. **The high-level intent** — what category of task is this. ("This is
   a clipboard utility that…", "This is an automation that posts a
   note to GitHub…")
2. **The flow** — walk the major steps in order. Don't recite every
   action; group by purpose.
3. **The branches** — note any `if`/`menu`/`repeat` blocks and what
   they gate.
4. **External integrations** — flag any HTTP calls (`downloadurl`),
   third-party app intents (`com.<vendor>…`), or features that need
   particular OS versions.
5. **Watchouts** — hardcoded credentials, brittle assumptions, things
   the user may want to know.

Don't explain Apple Shortcuts itself — assume the user knows what
shortcuts are. Focus on what *this* shortcut does.

### Step 3 — Optional deep dive

If the user wants more detail, fall back to the XML:

```sh
uv run shortcut-decode "<path>" --format xml -o /tmp/<name>.xml
```

Then read specific sections. The XML is verbose; only do this when
needed.

## Constraints

- **Read-only.** Never sign, never write to the source path.
- **Watch for secrets.** If you see hardcoded credentials (API keys,
  GitHub PATs, passwords) in `gettext` actions, mention it explicitly
  and recommend rotation — those land in plain text inside the bplist
  and travel with the file.
- **Identifier coverage gaps.** If the shortcut uses an identifier the
  schema doesn't model, you can still describe it from the buzz
  output — the decoder doesn't need schema knowledge.
