# V1.5 Section B — Schema Infrastructure Deep Review

**Branches under review**

- `v15/fu10-downloadurl-factories` (head `92157ba`) — DownloadURL factory methods
- `v15/fu12-validate-workflow` (head `be92ca1`) — `validate_workflow()` consolidated entry
- `v15/schema-gaps-inventory` (head `63fca34`) — `docs/schema-gaps.md`

**Reviewer:** opus deep-review (cross-cutting, post-individual-review)
**Date:** 2026-05-09

---

## 1. Verdict per branch

### FU-10 — DownloadURL factory methods — GREEN

A faithful lift of `AskForInput`'s factory pattern. Method shapes are correct,
body-type routing in `_params` is unchanged, the direct constructor remains
backward-compatible, and `test_factory_round_trip_equals_direct` walks both
paths through `to_action_dict()` so any divergence would surface. The only
legitimate critique is API completeness — the four methods cover everything the
corpus has confirmed, but the namespace will need to grow when `Form` and
`Multipart` are verified (§2). Not blocking; the direct constructor is the
escape hatch.

### FU-12 — `validate_workflow()` — YELLOW

Entry point is well-scoped, four validators wired correctly, finding shape
is cleanly JSON-serialisable, tests are solid. Two issues hold this back from
green: (a) `variable-not-set` has a confirmed false-negative on use-before-set
in flat flows — I reproduced it empirically (§3.4); (b) the public-surface
story is inconsistent — the function is importable from `shortcut_lib.validate`
but is *not* in `shortcut_lib/__init__.py`'s `__all__`, while `decode_file`
*is* exported. A validator pitched as "the V1.5 MCP server's primary tool"
should be on the package's main namespace alongside `decode_file`.

### Schema-gaps inventory — YELLOW

The doc is accurate in its broad strokes (29 modelled, 364 unmodelled, batch
ordering sensible) and the recommended-batches section is genuinely useful.
But factual errors a careful reader will notice:

1. `is.workflow.actions.getwebpagecontents` is listed twice — once correctly
   at line 216 ("Get Web Page Contents"), again at line 248 mislabelled as
   "Contents of URL". The second row is wrong: "Contents of URL" is
   `downloadurl`, which is *already modelled* (Section 5).
2. Counts disagree with the oracle. The doc was generated against public-only
   (20 samples, 661 invocations); the oracle includes private (21 samples,
   687 invocations). Per-identifier counts are off (e.g. `downloadurl` shows
   5 in the doc, 7 in the full corpus).
3. Per-action key counts disagree with the oracle for at least four Tier-1
   actions (§4.1).
4. **No regenerate script.** Every other freshness artefact in this repo has
   one. The doc is set up to drift the moment the corpus changes.

None blocking, but the corrections in §4 should be applied before merge.

---

## 2. FU-10 — API completeness, sample call sites, back-compat

### 2.1 Method coverage versus the real HTTP surface

| HTTP shape | Factory | Notes |
|---|---|---|
| GET (no body) | `.get(url, headers)` | Covered |
| POST/PUT/PATCH/DELETE + JSON | `.json(url, body, method, headers)` | Covered |
| POST/PUT/PATCH/DELETE + raw text | `.plain_text(url, body, …)` | Covered |
| POST/PUT/PATCH/DELETE + file | `.file(url, body, …)` | Covered |
| POST + form-encoded (`Form`) | **Not present, deliberate** | `_params` raises `SchemaError("body_type='Form' is not yet verified")`. Correct. |
| POST + `Multipart` | **Not present** | Listed in the docstring but unverified; falls through to the `WFRequestVariable` branch. Correct deferral. |
| `HEAD` / `OPTIONS` | Not on factory `Literal["POST", "PUT", "PATCH", "DELETE"]` | Apple's UI doesn't expose these. Correct. |
| GET + body | Disallowed by `.get`'s signature | `test_get_factory_no_body_kwarg` covers it. |

The deliberate omission of `.form()` is right — when `Form` is verified, drop
the `SchemaError` guard and add `.form(url, body, method, headers)`. The
class-module docstring (lines 1–12) is **inconsistent**: it says "*three*
body-encoding modes observed" then lists four bullets (JSON, Form, Plain Text,
File). Edit to say "four observed types and one deferred (`Form`)".

### 2.2 Direct-constructor back-compat

Verified end-to-end via `test_factory_round_trip_equals_direct`. No existing
call site needs migration — `examples/note_to_github.py:107–124` and
`examples/voice_note_to_git.py:202–215, 230–243` continue to work.

One asymmetry worth noting (not a bug): direct constructor accepts any
`method: str`; factory constrains to `Literal["POST", "PUT", "PATCH",
"DELETE"]`. That's the right outcome for the factory (narrow surface, ty
catches bad calls). The direct constructor is the escape hatch when `method`
is determined at runtime — already implied by the existing class docstring.

### 2.3 Sample call-site comparison

Hypothetical migration of `examples/note_to_github.py:107–124`:

```python
# Before
s.add(
    DownloadURL(
        url=url_text, method="PUT",
        headers={"Authorization": auth_header, "Accept": "...", ...},
        body={"message": Text("Add note {base}", ...), "content": NamedVar("ContentB64")},
        body_type="JSON",
    )
)

# After
s.add(
    DownloadURL.json(
        url_text,
        {"message": Text("Add note {base}", ...), "content": NamedVar("ContentB64")},
        method="PUT",
        headers={"Authorization": auth_header, "Accept": "...", ...},
    )
)
```

Reads better. "This is a JSON-bodied request" is the first thing the eye lands
on; the redundant `body_type="JSON"` trailing kwarg is gone; positional
`url, body` matches REST mental model. Recommend opportunistically migrating
the two examples so the canonical V1.5 reference shows the preferred shape.

### 2.4 FU-10 follow-ups

- **Should fix before merge:** module docstring "three body-encoding modes"
  vs four-item list.
- **Nit:** `.file`'s docstring defaults to `POST`, but real callers
  (`voice_note_to_git.py`) use `PUT`. Add a one-line hint.
- **V1.5+:** add `.form()` when sample-confirmed.
- **V1.5+:** migrate the two examples to the factory pattern.

---

## 3. FU-12 — API design, MCP-readiness, validator coverage

### 3.1 `ValidationFinding` shape critique

The current shape (`severity, code, message, action_index, action_identifier,
parameter_key`) is the right starting point. `dataclasses.asdict(f)` returns
a JSON-serialisable dict including `null` for unset Optional fields — verified.
The three-tier severity (`error`/`warning`/`info`) maps cleanly onto MCP
result severity and LLM-author triage.

**What's right:** stable short `code`, "training signal" messages (state what
was wrong + what's expected), enough location info for a clickable surface,
deterministic stable sort by `(action_index, code)`.

**What's missing or worth changing:**

- **`suggested_fix: str | None = None`** — `envelope-mismatch` always knows
  the *correct* type (the oracle gives it). `import-question-action-index-out-of-range`
  has a clamped suggestion (`max(0, min(idx, n-1))`). Pulling the fix out of
  the prose `message` into a separate field lets an MCP server return
  actionable diffs. Purely additive.
- **`workflow_path: list[str | int] | None`** — for nested findings (a future
  validator that walks into `WFJSONValues` items). Defer until needed.
- **`sample_citations: list[str]`** for `envelope-mismatch` — the oracle has
  these. Defer; bloats the shape.

**Verdict:** good for V1.5. Add `suggested_fix` opportunistically; defer the
rest.

### 3.2 Public-surface recommendation

Today: `from shortcut_lib import decode_file` works; `from shortcut_lib import
validate_workflow` raises `ImportError`. That's the wrong asymmetry given
the brief positions this as the MCP server's primary tool. Fix:

```python
# src/shortcut_lib/__init__.py
from shortcut_lib.decode import DecodedShortcut, decode_file
from shortcut_lib.encode import EncodeError, encode_to_bplist, sign_to_file
from shortcut_lib.validate import ValidationFinding, validate_workflow

__all__ = [
    "DecodedShortcut", "EncodeError", "ValidationFinding",
    "decode_file", "encode_to_bplist", "sign_to_file", "validate_workflow",
]
```

`shortcut_lib.schema` is *not* the right home — that module is the typed
authoring layer. `validate_workflow` is a transformation over the wire dict;
top-level package is the right place.

### 3.3 MCP tool readiness — concrete sketch

```python
from dataclasses import asdict
from shortcut_lib import decode_file, validate_workflow

@server.tool()
def validate_shortcut(path: str) -> dict[str, Any]:
    decoded = decode_file(path)
    findings = validate_workflow(decoded.workflow)
    return {
        "ok": all(f.severity != "error" for f in findings),
        "findings": [asdict(f) for f in findings],
        "counts": {sev: sum(1 for f in findings if f.severity == sev)
                   for sev in ("error", "warning", "info")},
    }
```

That works as-is. Three minor frictions:

1. No `Findings.to_dict()` or `findings_to_json()` helper — every consumer
   will write `[asdict(f) for f in findings]`. Defer; one line.
2. No `has_errors(findings) -> bool` rollup. Defer.
3. No `validate_workflow(workflow, only=[...])` filter parameter — would
   power "fast envelope check" vs "full validation" surfaces. Defer until
   a consumer asks.

**Verdict:** function is MCP-ready as written. Export it (§3.2), then the
wrapper above lands in <50 lines.

### 3.4 Missing validators / coverage gaps

**CONFIRMED FALSE NEGATIVE — variable use-before-set.** The YELLOW review's
claim is real. Repro:

```python
workflow = {
    "WFWorkflowActions": [
        # action 0: SetClipboard reading MyVar (not yet set)
        {"WFWorkflowActionIdentifier": "is.workflow.actions.setclipboard",
         "WFWorkflowActionParameters": {
             "UUID": "AAAA…", "WFInput": {
                 "Value": {"VariableName": "MyVar", "Type": "Variable"},
                 "WFSerializationType": "WFTextTokenAttachment"}}},
        # action 1: SetVariable that binds MyVar
        {"WFWorkflowActionIdentifier": "is.workflow.actions.setvariable",
         "WFWorkflowActionParameters": {"UUID": "BBBB…", "WFVariableName": "MyVar"}},
    ],
    "WFWorkflowImportQuestions": [],
}
validate_workflow(workflow)  # → []  (should flag MyVar at action 0)
```

iOS resolves `MyVar` as empty at action 0. The validator misses it because
`_collect_set_variable_names` pre-collects all bound names before the
reference walk. **Fix before merge:** walk sequentially, accumulate
`bound_names` per action, check each reference against names bound *strictly
before* the current action. ~5-line refactor inside
`_validate_variable_not_set`. Add `test_validate_variable_use_before_set_flagged`.

The current docstring acknowledges the conservative-by-design choice ("a name
set inside a `Repeat` body is visible after the loop"), but that's the wrong
framing — iOS *does* enforce sequential scope at runtime in flat flows.

**Other validators worth adding (V1.5 backlog, not blocking):**

- **`_validate_setup_question_parameter_key`** — `WFWorkflowImportQuestions`
  entries with a `ParameterKey` that doesn't exist on the target action's
  params dict. ~15 lines. High value for LLM-author UX.
- **`_validate_control_flow_balance`** — open/close marker pairing for
  `If`/`Repeat`/`ChooseFromMenu`. A stray `ControlFlowMode=2` without a
  matching open fails to import silently. ~25 lines.
- **`_validate_min_client_compatibility`** — V2: needs a per-action
  `min_client` map. Defer.
- **Action-output type-compatibility** — V2+. Defer indefinitely; the schema
  already prevents most type mismatches at construction.

**Magic-var hardcoding fragility.** `_MAGIC_VAR_TYPES` is a duplicated literal
of values from `values.py`. The comment claims it "originates from
`values.py` MagicVar.to_token()['Type']" but the values are hardcoded. **Fix
before merge:**

```python
from shortcut_lib.schema.values import (
    Ask, Clipboard, CurrentDate, RepeatIndex, RepeatItem, ShortcutInput,
)
_MAGIC_VAR_TYPES: frozenset[str] = frozenset(
    mv.type_name for mv in (Ask, Clipboard, CurrentDate, RepeatIndex, RepeatItem, ShortcutInput)
)
```

Two lines. Today the values match by coincidence; the next magic-var added to
`values.py` would break this silently.

### 3.5 FU-12 follow-ups (priority order)

1. **Blocking before merge** — sequential `variable-not-set` walk + regression
   test.
2. **Blocking before merge** — derive `_MAGIC_VAR_TYPES` from `values.py`.
3. **Should fix before merge** — export `validate_workflow` and
   `ValidationFinding` from `shortcut_lib/__init__.py`.
4. **Should fix before merge** — note "structural validation only" in the
   `validate_workflow` docstring so consumers don't expect semantic / runtime
   checks.
5. V1.5 — `suggested_fix` field on `ValidationFinding`.
6. V1.5 — `_validate_setup_question_parameter_key`.
7. V1.5 — `_validate_control_flow_balance`.
8. V1.5 — cache `all_observed_types` once at the top of `_validate_envelope`.
9. V1.5 — `has_errors(findings) -> bool` helper.

---

## 4. Schema-gaps doc — accuracy and currency

### 4.1 Confirmed factual errors

- **Duplicate `is.workflow.actions.getwebpagecontents`.** Lines 216 ("Get
  Web Page Contents", 2 occurrences) and 248 (mislabelled "Contents of
  URL", 2 occurrences). Delete the line-248 row.
- **§1 invocation count mismatch.** Doc says "661 invocations across 20
  samples"; oracle says "687 across 21 samples" (public + private). Either
  regenerate against the same corpus the oracle uses, or scope §1
  explicitly to public-only.
- **Tier-1 per-action key counts disagree with the oracle:**
  - `text.combine` doc: 3 keys (`text`, `WFTextSeparator`, `Show-text`).
    Oracle: 2 (`WFTextSeparator`, `text`). `Show-text` not in the corpus.
  - `addnewreminder` doc: 10 keys including `WFFlag`. Oracle: 9, no
    `WFFlag`.
  - `sendmessage` doc: 3 keys including `IntentAppDefinition`. Oracle: 2.
    `IntentAppDefinition` does exist on `timer.start` — looks like a
    cross-action confusion.
  - `alert` doc: 3 keys including `WFAlertActionCancelButtonShown`.
    Oracle: 2.

These don't change the doc's batch-ordering recommendations but undermine
the "sample-grounded" credibility (handoff §3 names this as a project
principle). **Fix before merge.**

### 4.2 Currency story — staleness path

The doc has no regenerate script. Every other freshness artefact does:

| Artefact | Regenerator |
|---|---|
| `data/observed_envelope_types.json` | `scripts/scan_envelope_types.py` |
| `docs/known_identifiers.md` | `scripts/decode_all.py` |
| `docs/coverage_<sample>.md` | `scripts/coverage_report.py` |
| `docs/schema-gaps.md` | **none — hand-curated** |

This is the wrong shape for the doc's purpose ("what to model next"). The
answer changes when:
- A new sample lands (counts shift).
- An identifier moves unmodelled → modelled (Section 5 grows).
- Jellycore facts refresh.

**Three-tier fix:**

1. **Immediate (before merge):** add an HTML comment header pinning state:

   ```markdown
   <!--
   Generated 2026-05-09 against:
     - main @ <commit>
     - samples/decoded/*.xml (public, 20 samples, 661 invocations)
     - data/observed_envelope_types.json (197 actions, 214 slots)
   To regenerate: scripts/build_schema_gaps.py (TODO).
   -->
   ```

2. **V1.5 follow-up:** `scripts/build_schema_gaps.py` — auto-generates §1
   snapshot, §2/§3 tier tables (from the oracle), §5 modelled list (from
   `list_actions()`). §4 cluster table and §6 batch recommendations stay
   hand-curated — that's where human judgement adds value.

3. **CI-in-spirit:** a `make check-schema-gaps` target that diffs regenerated
   vs committed. PR diff makes drift visible.

The schema-gaps-inventory review's "post-merge postscript" idea is a nice
touch but doesn't address the underlying problem — postscripts also drift.

### 4.3 Tier boundaries and batches

The 4+ / 2-3 / 1-occurrence buckets reflect a real signal. The
`Apparent complexity` annotation is the most useful column — it separates
"trivially modellable next sprint" from "needs new infrastructure first"
(the filter-predicate problem). Keep it.

The "Recommended Next Batches" section is the doc's most valuable output and
worth keeping hand-curated even when the rest is regenerated. Batches A–G
read like a sprint plan and aren't easy to derive mechanically.

### 4.4 Schema-gaps follow-ups

1. **Blocking before merge** — fix the four factual errors in §4.1.
2. **Should fix before merge** — HTML comment header pinning state.
3. **Should fix before merge** — clarify §1 scoping ("public corpus only").
4. V1.5 — `scripts/build_schema_gaps.py`.
5. V1.5 — `make check-schema-gaps` staleness diff.

---

## 5. The implied future-state — does the trio compose?

These three pieces compose cleanly into a "typed schema + structural
validator + roadmap" stack. The validator's oracle dependency, the schema
layer's `coerce_text_field` work (FU-7), and the gaps doc's
recommended-batches all share the same `data/observed_envelope_types.json`
substrate. That's good architecture.

The implied workflow:

- A user writes shortcuts via the typed schema; `DownloadURL.json(...)` and
  `AskForInput.text(...)` factories make call sites readable.
- Their authoring tool — the V1.5 MCP server — calls
  `validate_workflow(s.to_workflow())` after each construction step; findings
  are returned as structured `(severity, code, action_index, parameter_key,
  message)` records.
- An audit CLI runs the same `validate_workflow` over decoded existing
  shortcuts to find pre-existing envelope-mismatch issues.
- `docs/schema-gaps.md` (regenerated each sprint) shows what to model next.

**Where it leaks:**

- **Factory pattern is undocumented as a convention.** Today there are two
  examples (`AskForInput`, `DownloadURL`) and no `roadmap.md` entry saying
  "actions with 3+ wire-shape variants governed by a discriminator field
  should provide factories". When `addnewreminder` lands per the gaps doc,
  the next batch author won't know factories are expected.
- **Validator scope is undocumented as "structural only".** The docstring
  describes the four checks but doesn't say what's *out of scope* (semantic
  errors, runtime permissions, action-output type compatibility). MCP
  consumers will likely ask the validator to do more than it should.
- **Gaps doc's Batch A is "what's already in flight."** Four V1.5 parallel
  branches model the four Batch A actions. A reader on `main` post-merge
  will misread Batch A as "do this next" — the HTML comment header
  recommended in §4.2 fixes this if it pins to a commit.

---

## 6. Followups consolidated (ranked)

### Blocking — fix before merging the respective branch

1. **FU-12 — sequential `variable-not-set` walk.** Confirmed false-negative.
   Add a regression test.
2. **FU-12 — derive `_MAGIC_VAR_TYPES` from `values.py` singletons.**
3. **Schema-gaps — fix the four factual errors in §4.1.**

### Should fix — before merge if the branch is otherwise green

4. **FU-12 — export `validate_workflow` and `ValidationFinding`** from
   `shortcut_lib/__init__.py`.
5. **FU-12 — add "structural only" scope note** to the `validate_workflow`
   docstring.
6. **FU-10 — fix the inconsistent module docstring** ("three body-encoding
   modes" + four-item list).
7. **Schema-gaps — HTML comment header** pinning corpus / commit / oracle.
8. **Schema-gaps — clarify §1 scoping** as "public corpus only".

### V1.5 follow-ups (track in `docs/handoff.md`)

9. **FU-12** — `_validate_setup_question_parameter_key` validator (15 lines).
10. **FU-12** — `_validate_control_flow_balance` validator (~25 lines).
11. **FU-12** — `suggested_fix: str | None` field on `ValidationFinding`.
12. **FU-12** — `has_errors(findings) -> bool` helper.
13. **FU-12** — cache `all_observed_types` in `_validate_envelope` (perf).
14. **Schema-gaps** — `scripts/build_schema_gaps.py` regenerator.
15. **Schema-gaps** — `make check-schema-gaps` CI-style staleness diff.
16. **FU-10** — `.form()` factory when sample-confirmed.
17. **FU-10** — migrate the two examples to the factory pattern.

### Architectural / V2

18. **Document the factory pattern as a convention** in `roadmap.md`. When
    an action has 3+ wire-shape variants on a discriminator field, the
    `@register` class should provide factories. Two examples, zero docs.
19. **`validate_workflow(workflow, only=[...])`** filter parameter for the
    MCP "fast envelope check" surface.
20. **`ValidationReport` wrapper** with `findings`/`error_count`/etc — defer
    until the MCP server actually wraps it.
21. **Min-client-version validator** — needs a per-action `min_client` map
    built from the registry.
