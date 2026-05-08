# Handoff — 2026-05-08

Resume document for a fresh-context agent (or future-Findlay). Self-
contained: do not require the previous conversation. Sections are
ordered shallow → deep — read what you need.

---

## Starter prompt (paste into a new Claude session)

```
You're picking up shortcut-lib at ~/personal/shortcut-lib. It's a
Python library for authoring Apple Shortcuts files programmatically;
the primary user is Claude (LLM-authored shortcuts).

State at handoff:
- 19 commits, 216 tests passing, all prek hooks green.
- Multi-agent deep review complete; 8 blockers identified, 4 fixed,
  ~50 should-fix items, ~40 nits, 7 excellence-tier refactors.
- Today's task: continue closing the deep review action list with
  judgement (some review items were calibrated wrong; fix the real
  bugs, skip the ones that don't apply).

Read in this order before doing anything:
1. docs/handoff.md  — this file. Resume context + open tasks.
2. docs/roadmap.md   — vision, design principles, decisions log.
3. docs/work_log.md  — what's been built and why; append-only.
4. reviews/shortcut-lib-overnight/shortcut-lib-overnight-deep.md
   — the consolidated deep review.

Then pick the next task from this file's "Open tasks" section.
Each task is self-contained.

Coding conventions:
- uv-managed; run things via `uv run pytest -q` and `prek run --all-files`.
- Errors are training signal: SchemaError messages should say what was
  wrong AND what shape was expected.
- Sample-grounded: when in doubt about wire format, decode a real
  sample at samples/decoded/*.xml; don't trust Jellycore parameter
  names blindly.
- Auto-discovery: drop a new action file in src/shortcut_lib/schema/
  actions/ — it registers itself via @register; no shared file edits.
- Working tree commits: when splitting one logical change into
  multiple commits, run `git reset` BEFORE selective `git add`,
  otherwise prior `git add -A` calls leave files staged that will
  get pulled into the next commit.

Spawn sonnet sub-agents for bounded mechanical work, spawn opus sub-agents for
more complicated tasks that require design decisions. Implement critical
code sections yourself. When there is doubt or an important decision to be made,
consult with the user (me) before proceeding.`
```

---

## Project state at handoff

**Repo**: `~/personal/shortcut-lib`, branch `main`, no remote configured.

**Test count**: 216 (up from 41 at the start of the project).

**Action coverage**: 24 leaf actions registered + 5 control-flow + 6 value
types + magic-variable singletons. See `uv run python scripts/print_actions.py`.

**Most recent commits** (newest first):
- `cae21e4` — Deep-review batch: blockers B1, B2, B3+B4, B8 + SF-batch1
  (subprocess hardening) + SF-batch3 (wire-format equivalence tests) +
  Dictionary empty-WFItems fix. NB: this commit absorbed multiple
  intended commits because of a working-tree-staging mistake; the
  *content* is correct, the message understates what's there.
- `f69bda1` — Rename buzz snapshot file (after history rewrite).
- `539a2f0` — Skills: deeper vault-note cross-references.
- `2c10b4e` — Move skills into the repo; symlink back into `~/.claude/skills/`.
- `7caeead` — UseModel + Writing Tools (Apple Intelligence) actions.

**Skills location**: `skills/{make,edit,decode}-shortcut/SKILL.md`,
symlinked from `~/.claude/skills/`. The symlinks are NOT in the repo
(by design — they're per-machine); recreate via:
```
ln -s "$PWD/skills/<name>" ~/.claude/skills/<name>
```

---

## What's done (from the deep review)

- ✅ B1 — `registry.py` `has_default` sentinel: now uses
  `dataclasses.MISSING`. Caveat: most production action classes default
  required-feeling fields to None for caller ergonomics, so the flag
  reflects the dataclass contract honestly but doesn't tell an LLM
  which slots will be rejected at emit time. Improving that signal is
  follow-up FU-1 below.
- ✅ B2 — `If` `_condition_rhs` bool short-circuit: now raises on bool
  RHS with arithmetic/string operators; only valueless ops accept bool.
- ✅ B3+B4 — `AskForInput`: `_VALID_TYPES` enforced in `__post_init__`;
  `default_answer` routes to `WFAskActionDefaultAnswer{,Number,Date,
  DateAndTime}` based on `input_type`. Date/Time `WFAskActionDefault
  AnswerDate` is *inferred* — flag if a real sample contradicts.
- ✅ B8 — `ChooseFromMenu` test coverage (9 tests including empty-cases
  raise, marker sequence, GroupingIdentifier consistency).
- ✅ SF-batch1 — subprocess hardening: shared `run_cli` in
  `_subprocess.py` with `shutil.which` probe, `timeout=60s`,
  `FileNotFoundError` and `TimeoutExpired` re-raised as
  `DecodeError`/`EncodeError`. Cert-parse error wrapped.
- ✅ SF-batch3 — wire-format equivalence tests for top 7 actions
  (6 pass; the failing one surfaced the Dictionary empty-WFItems bug,
  also fixed in this batch).
- ✅ Dictionary empty-WFItems fix — `Dictionary().to_action_dict()`
  now omits `WFItems` entirely (matches Apple GUI emission).

---

## Open tasks

Each task is self-contained. Read its "files to read first" entry, do
the work, run the verify command, mark complete. Don't expand scope.

### B5 — `Shortcut.from_workflow` preserves top-level metadata

- **Status**: open
- **Model**: opus (small refactor + test design)
- **Depends on**: nothing
- **Severity**: blocker (silent data loss on lift round-trip)

**Problem**: `Shortcut.from_workflow` (in `src/shortcut_lib/builder.py`)
captures only `surfaces`, `min_client`, `icon_glyph`, `icon_color`,
`accepted_input`, `output_classes`. Then `Shortcut.to_workflow` hard-
codes `WFQuickActionSurfaces=[]`, `WFWorkflowImportQuestions=[]`,
`WFWorkflowHasOutputFallback=False`, `WFWorkflowHasShortcutInputVariables=False`,
and overwrites `WFWorkflowClientVersion`. Three samples
(`batch_add_reminders`, `set_weekend_chores`, `start_pomodoro`) carry
non-empty `WFWorkflowImportQuestions`, which is destroyed on
lift→emit.

The lift round-trip test
(`tests/test_lift_round_trip.py:test_lift_then_emit_preserves_actions`)
only asserts on `WFWorkflowActions` and `WFWorkflowMinimumClientVersion`,
so the destruction is invisible.

**Fix**:
1. Add `_extra: dict[str, Any] = field(default_factory=dict)` field to
   `Shortcut` to hold un-modelled top-level keys.
2. In `from_workflow`, capture every top-level key not modelled by an
   explicit attribute into `_extra`.
3. In `to_workflow`, build the modelled dict, then merge `_extra` over
   it (with modelled fields winning if there's a key collision —
   shouldn't happen in practice).
4. Strengthen the lift round-trip test: assert the full top-level dict
   round-trips minus a small allowlist (`WFWorkflowClientVersion` may
   legitimately be regenerated; consider preserving it in `_extra` too).

**Files**:
- Read first: `src/shortcut_lib/builder.py`, `tests/test_lift_round_trip.py`.
- Edit: same two.

**Verify**: `uv run pytest tests/test_lift_round_trip.py tests/test_round_trip.py -q`.

**Success criteria**: Every committed sample round-trips through
`from_workflow → to_workflow` with the FULL top-level dict equal to the
decoded original (modulo `WFWorkflowClientVersion` if intentionally
regenerated — document the decision in the test).

---

### B7+E1 — `RunWorkflow` Self sentinel + stable workflow_identifier

- **Status**: open
- **Model**: opus (architectural refactor)
- **Depends on**: nothing
- **Severity**: blocker (composition silently breaks across re-runs)

**Problem A**: `Shortcut.workflow_identifier` is generated fresh on
every `Shortcut(...)` construction (default factory `_new_workflow_uuid`).
Orchestrator shortcuts bake the helper's UUID into a `RunWorkflow`
action at emit time. Re-running the build script produces helpers
with new UUIDs; the orchestrator's stored UUID stops matching, and
`RunWorkflow` silently breaks.

**Problem B**: `RunWorkflow.target` accepts `Shortcut | tuple[str, str]
| Literal["self"]`. The `"self"` magic string is type-clumsy, hard for
an LLM to pattern-match (likely guesses: `"Self"`, `"this"`, `"@self"`),
and requires `_resolve_self_refs` in `Shortcut.to_workflow` to walk
the flat output and substitute `__SELF__` markers — spooky action at
a distance.

**Fix**:
1. Make `Shortcut.workflow_identifier` a **required-but-with-helpful-
   default** parameter. When omitted, derive deterministically from
   `name` (e.g. `uuid5(NAMESPACE_DNS, name)`) so re-runs are stable.
   Document this clearly: change the name → change the identifier.
2. Add a `Self` sentinel singleton (e.g. `class _SelfRef: ...; Self =
   _SelfRef()`) and re-export from `shortcut_lib.schema`.
3. In `Shortcut.add`, when adding a `RunWorkflow` whose target is the
   `Self` sentinel, resolve to the containing `Shortcut`'s identity
   immediately — no post-hoc walk needed.
4. Delete `_resolve_self_refs` and the `__SELF__` marker scheme.
5. Type `RunWorkflow.target` as `Shortcut | tuple[str, str] | _SelfRef`.

**Files**:
- Read first: `src/shortcut_lib/schema/compose.py`,
  `src/shortcut_lib/builder.py`, `tests/test_schema_tier0.py`,
  `examples/quick_pomodoro.py`, `examples/vault_note_to_git.py`.
- Edit: compose.py, builder.py, schema/__init__.py (export `Self`),
  the two examples (replace `target="self"` with `target=Self`),
  the test.

**Verify**: `uv run pytest -q` and re-run both examples
(`uv run python examples/quick_pomodoro.py` and
`uv run python examples/vault_note_to_git.py`).

**Success criteria**:
- All existing tests pass.
- New test: `Shortcut(name="X")` constructed twice produces the same
  `workflow_identifier` (deterministic).
- New test: `RunWorkflow(target=Self)` resolves at emit time to the
  containing shortcut's identity.
- `_resolve_self_refs` is gone.
- The two examples still produce signed shortcuts that decode cleanly.

---

### SF-batch2 — dead code + indirection cleanup

- **Status**: open
- **Model**: sonnet
- **Depends on**: nothing (parallelisable with B5/B7 if those touch
  different files)

**Items** (each ~5-line change, batch them):

1. Delete `Otherwise` class in `src/shortcut_lib/schema/control.py`
   (dead — `If.otherwise` is a list parameter, never inspects for
   `Otherwise` instances). Remove from `schema/__init__.py` exports
   and `__all__`. Remove `Otherwise` import from
   `tests/test_schema_tier0.py` (currently `# noqa: F401`'d).
2. Delete `_coerce_param` wrapper in `control.py` (the comment
   claims circular-import avoidance, but `base.py` doesn't import
   from `control.py` — verify with `grep -n 'from shortcut_lib.schema.control' src/shortcut_lib/schema/base.py`,
   should return nothing). Import `coerce_value` at module top with
   `coerce_token` instead. Replace every call site.
3. Delete `_grouping_uuid` in `control.py` — it's a wrapper around
   `uuid4().upper()` identical to `fresh_uuid` already imported from
   base. Use `fresh_uuid` directly as the `default_factory` for
   `grouping_identifier`.
4. Move the inline `from shortcut_lib.schema.base import SchemaError`
   in `src/shortcut_lib/schema/actions/get_variable.py` to a top-
   level import (matches every other action file).
5. Add an explanatory comment to `_close_grouping` in `control.py`:
   `# Only valid for simple open → body → close constructs. If and
   ChooseFromMenu have interleaved markers and emit their own.`

**Verify**: `uv run pytest -q && prek run --all-files`.

**Success criteria**: No behavioural change; tests still pass; lint
clean.

---

### SF-batch4 — validation passes

- **Status**: open
- **Model**: sonnet
- **Depends on**: nothing

**Items**:

1. `AdjustTone.tone` (in `src/shortcut_lib/schema/actions/writing_tools.py`):
   no validation. Add a closed-set validator in `__post_init__` against
   the supported tones. Verify the actual tone strings against
   `samples/decoded/intelly.xml` — only `"professional"` is in there;
   document any inferred set with a comment, raise `SchemaError` for
   anything outside it.
2. `TextSplit.separator` (in `actions/text_split.py`): currently
   permissive — only `"Custom"` is gate-checked. Either add a closed
   set (`{"New Lines", "Spaces", "Every Character", "Custom"}`) or
   document the permissive intent. Picking strict is more LLM-friendly.
3. `FormatDate.date_style` / `time_style`: the `__post_init__`
   validation exists but has zero test coverage. Add
   `test_format_date_invalid_style_raises` and
   `test_format_date_invalid_time_style_raises`.
4. `SetVariable(name="")`: currently emits `WFVariableName=""`
   silently. Either add a guard + test, or document permissive
   behaviour with a test that asserts the current emission. Pick
   guard — consistent with `AppendVariable` which already raises.
5. `Dictionary._TYPE_URL=1`: dead code. `_detect_item_type` never
   returns it (strings always resolve to `_TYPE_TEXT`). Either
   remove the constant + branch, or add a `URL` wrapper class
   (`class URL(str): ...`) that detection checks before falling
   through. Pick remove for now; URL strings work correctly as
   `_TYPE_TEXT`.
6. `DownloadURL` `body_type="Form"`: the source has a
   `TODO: confirm WFFormValues` comment. No sample confirms the key.
   Until verified, raise `SchemaError("body_type='Form' is not yet
   verified against samples; use 'JSON' or 'Plain Text' instead")`.
7. `Dictionary._TYPE_ARRAY` (currently flattens via `str()` + newline
   join): an `Action` or `NamedVar` in a list value would emit as
   Python `repr` text. Raise `SchemaError` if a list entry contains
   a non-primitive, with a hint to use a templated string instead.

**Files**:
- `src/shortcut_lib/schema/actions/writing_tools.py`
- `src/shortcut_lib/schema/actions/text_split.py`
- `src/shortcut_lib/schema/actions/set_variable.py`
- `src/shortcut_lib/schema/actions/dictionary.py`
- `src/shortcut_lib/schema/actions/download_url.py`
- `tests/test_action_writing_tools.py` (new or extend existing),
  `tests/test_action_text_split.py`, `tests/test_action_format_date.py`,
  `tests/test_action_set_variable.py`, `tests/test_action_dictionary.py`,
  `tests/test_action_download_url.py`.

**Verify**: `uv run pytest -q`.

**Success criteria**: Each validation has at least one test for the
happy path AND one for the raise path.

---

### SF-batch5 — registry hardening

- **Status**: open
- **Model**: sonnet
- **Depends on**: nothing

**Items**:

1. Narrow `except Exception` in `describe_action` (in
   `src/shortcut_lib/schema/registry.py`) to `(NameError,
   AttributeError, TypeError)`. The current bare catch silently
   swallows all type-resolution failures; an LLM gets stale string
   annotations and no signal.
2. Add `tests/test_registry_visibility.py` cases:
   - `test_register_collision_raises` — registering a different class
     under an existing identifier raises `ValueError`.
   - `test_register_empty_identifier_raises` — registering a class
     with empty `identifier` raises `ValueError`.
   - `test_describe_action_handles_unresolvable_forward_ref` — define
     a synthetic action with an annotation that fails to resolve;
     assert `parameters` is returned (even if types are best-effort).

**Files**:
- `src/shortcut_lib/schema/registry.py`
- `tests/test_registry_visibility.py`

**Verify**: `uv run pytest tests/test_registry_visibility.py -q`.

---

### SF-batch6 — text-token-string envelope consistency (demoted from blocker)

- **Status**: open
- **Model**: sonnet (mostly mechanical) but verify against samples
- **Depends on**: nothing

**Background**: the deep review's correctness reviewer flagged plain-
string params as a blocker on the grounds that "Apple expects
WFTextTokenString". Empirical evidence (our existing round-trip on
voice_note_to_github with bare strings) shows Apple is permissive —
both forms work. Demoted to should-fix on the grounds of *consistency
with Apple GUI emission*, not correctness.

**What to do**:
1. Add a helper in `src/shortcut_lib/schema/base.py`:
   `def coerce_text_param(x: Any) -> Any` — when `x` is a plain `str`,
   wrap as `{"Value": {"string": x, "attachmentsByRange": {}},
   "WFSerializationType": "WFTextTokenString"}`. Otherwise delegate to
   `coerce_value` (Action / Value / Text).
2. Apply to text-typed parameter slots:
   - `GetText.text` (`WFTextActionText`)
   - `SetClipboard.input`, `SetVariable.input`, `AppendVariable.input`
     where the input is text — actually `WFInput` accepts mixed types.
     Don't wrap if the input is an `Output`/`NamedVar`.
   - `ShowNotification.title`, `body`
   - `TextReplace.input`, `find`, `replace`
   - Comment `WFCommentActionText`
3. Run `uv run pytest tests/test_round_trip.py tests/test_lift_round_trip.py -q` —
   these MUST still pass. The samples were decoded from real Apple files;
   if the schema now emits a different shape than what the lift
   captures, the round-trip will fail.
4. Run `uv run pytest tests/test_wire_format_equivalence.py -q` — this
   should now pass for more actions if the previously-failing ones were
   blocked on the envelope wrapping.

**CRITICAL**: do NOT change behaviour for samples that use bare
strings — those are existing, working shortcuts. The wrapping should
apply only to NEWLY-AUTHORED shortcuts via the schema. If
`coerce_text_param` is applied uniformly and it makes any current
test fail, back off and consult.

**Files**: see above.

**Verify**: full pytest, plus manually re-run
`uv run python examples/note_to_github.py` and
`uv run shortcut-decode "/Users/findlaywebb/Desktop/Note to GitHub.shortcut" --format buzz`
to inspect the result.

**Success criteria**: All tests still pass; the buzz output for newly
authored shortcuts shows templated-string envelopes consistently.

---

### SF-batch7 — excellence-tier refactors

- **Status**: open
- **Model**: opus (architectural)
- **Depends on**: B7+E1 (Self sentinel) lands first

**Items**:

1. **`ParamValue` type alias** replacing `input: Any` slot type.
   Define in `src/shortcut_lib/schema/base.py`:
   ```python
   type ParamValue = (
       str | int | float | bool | None | "Action" | "Value" | dict[str, Any] | list[Any]
   )
   ```
   (PEP 695 syntax, Python 3.13+.) Apply to action class field types
   that currently use `Any` for polymorphic parameter slots. Note:
   `describe_action` will then surface `ParamValue` instead of `Any`,
   which is more useful.

2. **`CONDITION_CODES` → `IntEnum`** in `control.py`. Currently a
   `dict[str, int]` and the same dict appears as an inline literal in
   `summary.py`. Promote to `class WFCondition(IntEnum): EQ = 0;
   LT = 1; GT = 2; ...`. Have `If.op` accept either the enum or the
   string keys (back-compat). Replace the duplicate in `summary.py`.

3. **`WFLLMModel` enum** for `UseModel.model` (in
   `src/shortcut_lib/schema/actions/use_model.py`): currently a free
   string. Promote to a `Literal["Apple Intelligence", "Private Cloud
   Compute", "On-Device", "Extension", "Ask Each Time"]`. Add a TODO
   comment that lists potential additions per the best-practices
   review (`"On-Device with Reasoning"`, `"Cloud (Verifiable)"`,
   `"Custom Endpoint"`, `"ChatGPT"`) — these need verification against
   a real iOS 26 sample.

**Verify**: `uv run pytest -q && prek run --all-files`.

---

### N-batch — nits (do as a final pass)

These are small but accumulate into noticeable friction. Tackle in
one commit at the end.

- `tests/conftest.py` doesn't exist; `SAMPLES_DIR = Path(__file__).parent.parent / "samples"` is duplicated in 5 test files. Extract to a single `samples_dir` fixture.
- `WFWorkflowClientVersion = "4033.0.4.3"` is hardcoded in
  `builder.py:to_workflow`. Promote to a module constant
  `_CLIENT_VERSION` with a comment naming the iOS/macOS version it
  came from.
- Make the `Shortcut.save_signed` default path = `Path.home() / "Desktop" / f"{self.name}.shortcut"` so `name` and filename agree. Or warn loudly when the file stem doesn't match `self.name`.
- `tests/test_from_file.py` hardcodes `len(actions) == 2` and
  `name == "dictate_to_clipboard"`. Replace with `Path(sample).stem`
  and `>= 2`.
- `tests/test_example_note_to_github.py` uses `in identifiers` —
  doesn't catch duplicate emit. Use `identifiers.count(...)` for
  expected-once actions.
- `decode.py`: add a module-docstring sentence explaining the trust
  model (the file self-vouches; Apple validates chain at import).
- `Shortcut.add` doesn't reject duplicate-add (same Action instance
  twice) or cross-shortcut-add. Add an `id(action)` set; raise on
  re-add with a hint that `Action` instances aren't shareable.
- `Shortcut.extend` and `Shortcut.add` non-Action guards have no
  tests.
- `DictateText.locale` and `stop_listening` non-default paths
  untested.
- `ShowNotification` empty-title/body suppression untested.
- `Action.custom_output_name` propagation untested (both
  `to_action_dict` emission AND `Action.output()` name resolution).
- `RepeatCount` with variable count untested.
- `RepeatEach(items=None)` raise untested.
- `RunWorkflow` with `(identifier, name)` tuple target untested.
- `Text` empty-template, no-substitution, repeated-name,
  `to_token` raise untested.
- `coerce_token` plain-scalar raise untested.
- `decode.decode_bytes` non-zero-profile, missing-cert-chain raise
  paths untested.
- `summary.py` for-each, repeat, menu, else formatting paths
  untested (only the start_pomodoro snapshot covers it).

---

## Follow-ups (not scoped to a specific task)

**FU-1 — `has_default` reflects dataclass contract, not runtime
required-ness.** Most actions default required-feeling fields to
`None` and validate at `_params` time. The flag is honest about the
dataclass but tells an LLM the wrong thing. Possible fix: add a
class-level `_required: ClassVar[set[str]]` that the registry
exposes alongside `has_default`, OR introspect `_params` for raises.
Punt until a concrete LLM-author experience reveals the right shape.

**FU-2 — `WFWorkflowClientVersion` brittleness.** Currently hard-
coded `"4033.0.4.3"`. Apple may eventually start rejecting stale
versions on import. Mitigation: expose as a `Shortcut` field; bump
the default whenever the user encounters an import warning.

**FU-3 — Wire-format equivalence for unmodelled samples.** SF-batch3
covered 7 actions. Many remain. Add equivalence tests opportunistically
when modifying an action's schema.

**FU-4 — `samples/private/voice_note_to_github.shortcut` PAT.**
The original file may have a live GitHub PAT baked in. The gitignore
keeps it local but rotate it if not already.

**FU-5 — Format `--format outline` alias for `--format buzz`.**
The user picked "buzz" but `outline` was a contender; both could
coexist with one as the canonical name. Punt unless someone asks.

**FU-6 — iOS 26 `Use Model` extra fields.** Best-practices review
suggested `WFLLMModelExtension` (when `model="Extension"`) and
`WFLLMSystemPrompt`. Both unverified against samples. Wait for a
real iOS 26 export that uses ChatGPT before adding.

---

## Coding conventions that matter for resume

1. **Don't mass-stage before splitting commits.** `git add -A` then
   `git add <subset>` does NOT unstage the previously-staged files.
   `git reset` first if you want a clean index.
2. **Sample-grounded over spec-grounded.** When schema disagrees with
   a decoded sample, the sample is right. Jellycore's parameter names
   are hints only.
3. **Auto-discovery via `pkgutil`.** Add a new action by dropping
   `src/shortcut_lib/schema/actions/<name>.py` with `@register` on
   the dataclass. No `__init__.py` edits.
4. **Errors are training signal.** Every `SchemaError` should state
   what was wrong AND what shape was expected. Bad: `"invalid input"`.
   Good: `"AskForInput.allows_decimal only applies to input_type='Number'; got input_type='Text'"`.
5. **Public API curation lives in `src/shortcut_lib/schema/__init__.py`.**
   The `# noqa: F401` re-export of `actions` is a side-effect import
   for registration — leave it.
6. **Don't use `--no-verify` on commits.** If a hook fails, fix the
   failure. The pre-push hooks are ruff lint + ruff format + uv-lock + ty.
7. **Buzz format is informational.** The summary format
   (`shortcut-decode --format buzz`) is for LLM consumption; it does
   NOT round-trip. For round-trip, work with the workflow dict
   directly.
8. **Skill files live in `skills/`** in the repo and are symlinked
   into `~/.claude/skills/`. Modifying the in-repo file affects
   Claude Code's skill discovery on the same machine.

---

## Where to look for context

- `docs/roadmap.md` — vision + design principles + decisions log.
- `docs/work_log.md` — append-only narrative of decisions and
  surprises.
- `docs/format.md` — Apple Shortcuts file format reference.
- `docs/sources.md` — third-party reverse-engineering attribution
  (Open-Jellycore, shortcuts-js, sebj/iOS-Shortcuts-Reference).
- `docs/agent_tasks.md` — earlier agent task queue (historical;
  superseded by THIS file for active work).
- `docs/product_review.md` — earlier product/staff review (mostly
  acted on).
- `reviews/shortcut-lib-overnight/shortcut-lib-overnight-deep.md` —
  the deep review that drove most of today's task list.
- `reviews/shortcut-lib-overnight/shortcut-lib-overnight-*.md` —
  the 7 specialist sub-reports underpinning the deep review.
- `~/Documents/FMP/tech/Apple_Shortcuts/*.md` — 8 vault notes
  capturing Apple's design intent (distilled from
  `docs/apple_raw/`).
- `data/jellycore_facts.json` — action-fact dataset projected from
  Open-Jellycore. See `NOTICE`.
