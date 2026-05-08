# Agent task queue

Self-contained briefs for sub-agents working on shortcut-lib. Each task names
the model best suited, its dependencies, and the success criteria. A fresh
Claude session can pick up any task by reading **only** the brief and the
linked context — nothing from prior conversations.

## How to use

1. Pick a task with `status: open` and all dependencies `done`.
2. Read the linked context files first.
3. Run `prek run --all-files` and `uv run pytest -q` before reporting done.
4. Update the task's status in this file as part of the same change.
5. Surface blockers as comments inline; **don't expand scope**.

## Conventions

- **opus** for tasks needing design judgement, debugging, architecture.
- **sonnet** for bounded mechanical implementation, research, content
  generation. Default to sonnet unless the task explicitly needs opus.
- **haiku** for very narrow mechanical conversions if any arise.
- Tasks marked `parallel_with:` can run concurrently with the listed tasks.

---

## TASK-A1 — Implement bplist encoder + sign helper

- **status**: open
- **model**: opus (bplist quirks need diagnosis)
- **dependencies**: none
- **parallel_with**: TASK-B1, TASK-B2
- **context to read**:
  - `docs/format.md` (envelope structure)
  - `src/shortcut_lib/decode.py` (the inverse pipeline)
  - One decoded XML at `samples/decoded/start_pomodoro.xml` for shape reference
- **what to build**:
  1. `src/shortcut_lib/encode.py` with two public functions:
     - `encode_to_bplist(workflow: dict) -> bytes` — binary plist via `plistlib.dumps(fmt=FMT_BINARY)`
     - `sign_to_file(workflow: dict, output: Path, mode: Literal["anyone", "people-who-know-me"] = "anyone") -> None` —
       writes bplist to a temp file, shells out to `shortcuts sign -i <tmp> -o <output>`, raises `EncodeError` on failure
  2. Mirror the `_run` helper from decode.py for subprocess invocation.
  3. Re-export from `__init__.py`.
- **success criteria**:
  - For every committed sample: `plistlib.loads(encode_to_bplist(decode_file(s).workflow)) == decode_file(s).workflow` (deep equality)
  - At least one sample produces a signed `.shortcut` that imports successfully into the macOS Shortcuts.app (manual smoke check; document the path in the task notes)
- **expected friction**: dict key order, bool vs int(0/1), bytes vs str, NSDate handling. If a sample fails round-trip, log the diff and pick the smallest fix that doesn't violate the format spec.

---

## TASK-A2 — Round-trip identity tests for all samples

- **status**: blocked (needs A1)
- **model**: opus (debug-driven)
- **dependencies**: TASK-A1
- **what to build**:
  - Add `tests/test_round_trip.py` parametrised over `samples/*.shortcut`.
  - For each sample: decode → encode_to_bplist → re-decode → assert deep-equal on the workflow dict.
  - Where deep equality fails, document the divergence (key order? bool/int?) in `docs/format.md` under a new "Encoding quirks" section, then fix the encoder so the test passes.
- **success criteria**: `uv run pytest tests/test_round_trip.py -q` passes for all 21 samples (incl. private one).

---

## TASK-A3 — LLM-readable decode format

- **status**: open
- **model**: sonnet
- **dependencies**: none (independent of encoder)
- **parallel_with**: TASK-A1, TASK-B1, TASK-B2
- **context to read**: one decoded XML (e.g. `samples/decoded/start_pomodoro.xml`) plus `docs/format.md`
- **what to build**:
  - Add `--format buzz` (suggested name) to `shortcut-decode` CLI.
  - Output is one line per action, indented for control flow grouping (`if`/`else`/`end`, `for`/`end`, `menu`/`case`/`end`).
  - Variables shown as `${OutputName}` not full UUIDs.
  - Templated strings shown with `{var}` substitutions inline.
  - Goal: ~10× fewer tokens than XML, fully unambiguous for re-author by Claude.
- **success criteria**:
  - Output for `samples/start_pomodoro.shortcut` is under 80 lines.
  - A reviewer can describe what the shortcut does from the output alone.
  - Add one snapshot test: encoded form for one sample matches a committed expected file.

---

## TASK-B1 — Crawl Apple Shortcuts official docs

- **status**: open
- **model**: sonnet
- **dependencies**: none
- **parallel_with**: TASK-A1, TASK-A3
- **context to read**: this file, `docs/roadmap.md` (Phase B)
- **what to build**:
  - WebFetch the following URLs (and follow links one level deep where they're docs subpages, not deeper):
    - `https://support.apple.com/guide/shortcuts/welcome/ios`
    - `https://support.apple.com/guide/shortcuts-mac/welcome/mac`
    - `https://support.apple.com/en-us/125148` (iOS 26 changelog)
    - `https://support.apple.com/en-us/101583` (general "What's new")
  - For each substantive page: extract a clean markdown copy with provenance footer (`Source: <url>, retrieved 2026-05-08`).
  - Save raw extracts under `~/personal/shortcut-lib/docs/apple_raw/<slug>.md` (gitignored — they're a working set, not committed).
- **success criteria**: at least 20 distinct topic pages saved, indexed in `docs/apple_raw/INDEX.md` with one-line summaries.

---

## TASK-B2 — Distil Apple docs into vault notes

- **status**: blocked (needs B1)
- **model**: sonnet
- **dependencies**: TASK-B1
- **context to read**: TASK-B1 output (`docs/apple_raw/`), `~/Documents/FMP/CLAUDE.md` (vault conventions)
- **what to build**: vault notes at `~/Documents/FMP/tech/Apple_Shortcuts/`:
  - `Design_Intent.md` — Apple's mental model: input/output, content items, magic variables, surfaces, automation triggers.
  - `Magic_Variables.md` — types, lifecycle, scope, the reserved set (CurrentDate, Clipboard, Ask, ShortcutInput, RepeatItem, etc.).
  - `Content_Item_Classes.md` — the 17+ types and what each accepts/produces.
  - `URL_Schemes.md` — `shortcuts://` reference and known patterns.
  - `Automation_Triggers.md` — personal automation triggers (the runtime context our shortcuts execute in).
  - `Action_Reference_Index.md` — link to Apple's per-category action lists, our coverage doc, and Jellycore.
  - One file per major concept. Snake_Case filenames. Frontmatter with `author: external`, `tags: [project/shortcut-lib, type/reference, source/apple-docs]`. Provenance footer.
  - Wikilink between related notes; link inbound from `~/Documents/FMP/tech/CLAUDE.md` if it lists tech topics.
- **success criteria**: Six+ notes, each linked to the others; index entry in vault tech CLAUDE.md or top-level tech index.

---

## TASK-C1 — Tier 0 schema (control flow + values + composition)

- **status**: blocked (needs A2)
- **model**: opus (architectural — sets the pattern for every C-tier task)
- **dependencies**: TASK-A2
- **context to read**: `docs/format.md`, `data/jellycore_facts.json`, several decoded XMLs (especially `dictionary.xml` for control-flow shapes)
- **what to build**:
  - `src/shortcut_lib/schema/__init__.py` — registry pattern.
  - `src/shortcut_lib/schema/values.py` — `Var`, `Output`, `CurrentDate`, `Clipboard`, `Ask`, `ShortcutInput`, `Text` (templated string with UTF-16 range computation), `Quantity`, `TimeOffset`.
  - `src/shortcut_lib/schema/control.py` — `If`/`Else`, `RepeatEach`, `RepeatCount`, `ChooseFromMenu`. Nested in the DSL; flat-with-grouping on emit.
  - `src/shortcut_lib/schema/compose.py` — `RunWorkflow(target_shortcut, input=...)`. First-class composition operator.
  - `src/shortcut_lib/builder.py` — `Shortcut` class that collects actions, mints UUIDs, flattens control flow, emits the workflow dict.
- **success criteria**:
  - Round-trip test: build a Python expression that produces the same workflow dict as one of our decoded samples (start with `start_pomodoro.shortcut` — small, has conditional + ask + adjustdate).
  - Registry exposes a `list_actions()` and `describe_action(identifier)` callable.
  - `RunWorkflow` accepts another `Shortcut` instance and resolves its identifier on encode.

---

## TASK-C2-x — Schema model for action `<X>`

These are bulk tasks dispatchable in parallel once C1 sets the pattern.

- **status**: blocked (needs C1)
- **model**: sonnet (mechanical given a known pattern)
- **dependencies**: TASK-C1
- **context to read**:
  - `src/shortcut_lib/schema/values.py` and `control.py` for the pattern.
  - `data/jellycore_facts.json` entry for `<X>`.
  - At least two decoded samples that use `<X>`.
- **what to build**: a typed model in `src/shortcut_lib/schema/actions/<dsl_name>.py` plus registry registration plus a unit test that round-trips the action against a real sample's parameters.
- **success criteria**: `pytest -k <dsl_name>` passes; `prek run` clean.

Tier 1 tasks (one per action): `setvariable`, `gettext`, `ask`, `comment`,
`getclipboard`, `setclipboard`, `format.date`, `text.replace`, `text.split`,
`notification`.

---

## TASK-D1 — `make-shortcut` skill

- **status**: blocked (needs C1, C2 tier 1)
- **model**: opus (skill design + integration)
- **dependencies**: TASK-C1, TASK-C2-tier1
- **what to build**: a Claude Code skill at `~/.claude/skills/make-shortcut/SKILL.md` that:
  - Reads `docs/roadmap.md`, `docs/format.md`, the schema registry.
  - Asks Claude to draft Python using the lib's API.
  - Runs the draft via `uv run`, signs the output, places `.shortcut` in `~/Desktop/` for the user to drag into Shortcuts.app.
  - Reports the action breakdown and any unsupported requests.
- **success criteria**: invoking the skill with a small prompt ("a shortcut that copies clipboard and shows it in a notification") produces a working `.shortcut` file.

---

## TASK-E1 — Goal shortcut: vault note → LLM → git

- **status**: blocked (needs C3, D1)
- **model**: opus (real-target validation; ambiguity in tool choices)
- **dependencies**: TASK-C2-tier1, TASK-C3 (vault-target actions), TASK-D1
- **what to build**: four shortcuts authored in Python under
  `examples/vault_to_git/` — three helpers + one orchestrator, demonstrating
  composition. Each is signed and importable. Document setup in
  `examples/vault_to_git/README.md`.
- **success criteria**: imported on iPhone, runs on a sample note, opens a
  PR on a vault repo (or commits directly).

---

## Notes on parallelism

- A1, A3, B1 can all run concurrently. Dispatch B1 and A3 to sonnet sub-agents
  while A1 stays with opus.
- B2 follows B1 sequentially.
- C2-tier1 tasks parallelise once C1 lands. Up to ~5 sonnet sub-agents at
  once is reasonable; the registry pattern guards against collisions.
- D1, E1 are integration tasks — opus, sequential.

## Notes on context cost

- Sub-agents start fresh; the brief above must be enough. If you find a brief
  isn't, edit it before dispatching, not during.
- Don't paste decoded XML into prompts; reference paths.
- Don't paste this whole file; reference the task ID.
