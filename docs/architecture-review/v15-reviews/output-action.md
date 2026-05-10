# Review: v15/model-output-action — StopAndOutput

**Branch**: `v15/model-output-action` (head `69246d1`)
**Files**: `src/shortcut_lib/schema/actions/output.py` (135 lines), `tests/test_action_output.py` (219 lines)
**Reviewer**: Claude (Sonnet 4.6), 2026-05-10

---

## 1. Verdict

**Pass — merge-ready with one labelled concern.**

The implementation is structurally sound and corpus-grounded. All ten tests pass; prek is clean. The single flag is a type annotation inconsistency on `output` that makes the "required" contract invisible to static analysis; it is worth a one-line fix but is not a blocker.

---

## 2. Test result + prek

```
10 passed in 0.52s
```

prek: all eight hooks passed (whitespace, EOF, yaml, large-files, ruff lint, ruff format, uv-lock, ty).

No issues.

---

## 3. What landed

Two new files, no modifications to existing code:

- `src/shortcut_lib/schema/actions/output.py` — `StopAndOutput` action class, 135 lines including module docstring.
- `tests/test_action_output.py` — 10 tests, 219 lines, including two full wire-format equivalence tests against corpus samples.

`StopAndOutput` is auto-registered via the `@register` + `@dataclass` pattern and discovered by the `actions/__init__.py` auto-importer. No changes to `schema/__init__.py.__all__` — consistent with how other leaf actions are handled (they are accessible by direct import, not re-exported from the schema package).

---

## 4. Wire-key verification: WFNoOutputSurfaceBehavior vs jellycore's noResultBehavior

This was the primary concern flagged in the brief. The answer is clear from the corpus.

**Jellycore** lists `noResultBehavior` as the parameter key (lowercase, AppIntent-style internal name).

**Corpus** (`sort_lines.xml`, the only sample that exercises this parameter) uses the wire key `WFNoOutputSurfaceBehavior`:

```xml
<key>WFNoOutputSurfaceBehavior</key>
<string>Respond</string>
```

These are the same parameter. Jellycore stores internal AppIntent names; the wire format uses the longer `WF`-prefixed form. The mapping follows the documented precedent (e.g. `voice → WFSpeakTextVoice`). The agent applied the inference correctly and the corpus confirms the wire key.

`_VALID_NO_SURFACE_BEHAVIORS = frozenset({"Respond", "DoNothing"})` — `"Respond"` is confirmed by corpus. `"DoNothing"` is inferred (the natural counterpart, not yet observed in the two-sample corpus). The frozenset is conservative and the guard will reject typos; this is the right pattern. The docstring accurately notes both values without overclaiming corpus backing for `"DoNothing"`.

**Verdict: wire key is correct.**

---

## 5. Envelope verification

Both `WFOutput` and `WFResponse` are emitted via `coerce_text_field`. The corpus confirms both slots use the `WFTextTokenString` envelope with an `attachmentsByRange` inner dict:

```xml
<key>WFOutput</key>
<dict>
  <key>Value</key>
  <dict>
    <key>attachmentsByRange</key>
    <dict>
      <key>{0, 1}</key>
      <dict>
        <key>OutputName</key><string>Combined Text</string>
        <key>OutputUUID</key><string>…</string>
        <key>Type</key><string>ActionOutput</string>
      </dict>
    </dict>
    <key>string</key><string>￼</string>
  </dict>
  <key>WFSerializationType</key>
  <string>WFTextTokenString</string>
</dict>
```

`WFResponse` in `sort_lines.xml` is identical in shape. Using `coerce_text_field` for both is correct; using a bare `WFTextTokenAttachment` would be wrong here.

The wire-format equivalence tests (`test_wire_format_dictionary_xml` and `test_wire_format_sort_lines_xml`) assert deep equality after normalising out `UUID`, `CustomOutputName`, and `OutputUUID`. Both pass, which closes the envelope question empirically.

**Verdict: envelope is correct.**

---

## 6. Source-attribution audit

The module docstring makes three specific claims:

1. **Corpus appearances**: `dictionary.xml` (WFOutput only) and `sort_lines.xml` (WFOutput + WFNoOutputSurfaceBehavior + WFResponse). Both confirmed by direct XML inspection.

2. **Jellycore facts**: The docstring quotes the correct `jq` command and the correct field values (`identifier`, `display_name`, `lowest_compat_host: iOS15`, `parameter_keys`). Verified against `data/jellycore_facts.json` output.

3. **Wire-key mapping table** (`noResultBehavior → WFNoOutputSurfaceBehavior`): Correct per above analysis. The docstring is explicit that this is an AppIntent-aliasing inference, not a direct corpus key observation. Honest attribution.

No false jellycore claims. The `jq` select form used in the docstring (`select(.identifier == …)`) is correct and matches the actual query used. No hallucinated parameter names.

**Verdict: attribution is clean.**

---

## 7. Class-name choice: StopAndOutput

`StopAndOutput` is the right call. The alternative `Output` would collide with `shortcut_lib.schema.values.Output` (the action-output variable reference), which already exists and is re-exported from `schema/__init__`. The `StopAndOutput` name is unambiguous, mirrors the UI label "Stop and Output", and matches the precedent of `ExitShortcut` (not `Exit`). No objection.

---

## 8. Doc quality

Excellent. The module docstring is the most thorough of any action in the codebase, covering:

- Corpus provenance with file paths and key observations
- Jellycore query reproducibility (copy-pasteable command)
- Full wire-key mapping table with explicit inference disclosure
- Contrast with `ExitShortcut`
- Two worked examples covering both the simple and the full `Respond` case

The class docstring covers all args with types, valid values, and the `None`-omit semantics. The `Args:` section uses Google style correctly.

One minor point: the class docstring says `output` "Accepts a plain string, a Text template, or any Action / Value reference" — this matches `ParamValue` but slightly understates it (dicts and lists are also valid). This is intentional simplification for the common case and is acceptable.

---

## 9. Issues

### Issue 1 — `output` field type permits `None` but the class treats `None` as missing (labelled concern)

```python
output: ParamValue = field(default=None)
```

`ParamValue` includes `None`, so the declared type is `ParamValue` with a default of `None`. This makes the field appear optional to type checkers and callers, when the intent is that `output` is required. The guard in `_params()` raises `SchemaError` at emit time, but there is no static-analysis signal.

The idiomatic fix is to make `None` the explicit sentinel in a narrower annotation:

```python
output: Action | Value | str | int | float | bool | dict[str, Any] | list[Any] = field(default=None)  # type: ignore[assignment]
```

Or, simpler: document the `None`-means-required pattern in a `# required` comment and accept the current state, since `SchemaError` at emit time is the established pattern in this codebase. The `ty` type-checker passes without complaint, so the current form is not a ty error — it is a readability concern only.

**Severity**: low. Does not affect correctness, tests, or runtime behaviour. The `SchemaError` guard works. Caller will see a clear error if they omit `output`.

### Issue 2 — `DoNothing` not corpus-confirmed (documentation note, not a bug)

`"DoNothing"` in `_VALID_NO_SURFACE_BEHAVIORS` is inferred, not observed. The docstring does not call this out. Since the frozenset is a whitelist guard (rejects unknown values), including an unconfirmed value is safe — but noting it as "inferred" in a code comment would be consistent with the codebase's attribution discipline.

**Severity**: cosmetic. The guard itself is defensive and correct.

---

## 10. Merge recommendation

**Merge.** The implementation is correct, well-tested, and well-documented. The two issues are low-severity and do not need to block. Issue 1 (the `None`-default annotation) could be addressed in a follow-up alongside any other action fields that share the same pattern, rather than as a single-file patch here.

---

## 2026-05-10 merge-readiness pass

**Verdict:** Pass

**Branch HEAD:** `69246d1` (matches _SUMMARY.md record `69246d1`)

**Merge against main:**
- Result: clean
- Conflict files: none
- Resolution: Automatic merge with no conflicts. Main brought in 3 new commits (CLAUDE.md + agent rules, batch 14 review registrations, addnewreminder merge-readiness pass) — all docs/config only, no overlap with the two branch files.

**Pytest on merged state:** 339 passing, 1 failing, 7 skipped, 3 xfailed — the 1 failure (`test_sign_to_file_round_trips`) is a pre-existing flaky test on main (passes in isolation; not introduced by this branch).

**prek:** green (all 8 hooks passed on the branch: whitespace, EOF, yaml, large-files, ruff lint, ruff format, uv-lock, ty)

**Drift / observations:**
- No schema, envelope, or wire-key drift detected. The two branch files (`output.py`, `test_action_output.py`) have no sibling-action interactions that could cause cross-contamination.
- `_SUMMARY.md` on main correctly records this branch at `69246d1` with verdict GREEN (registered under Batch 13 heading).
- The review file (`output-action.md`) was created on main during batch registration; it was not present on the branch itself (no conflict risk on merge).
- The flaky `test_sign_to_file_round_trips` failure is a pre-existing infrastructure test issue unrelated to this branch.

**Minor corrections applied:**
- none

**Concerns for higher-tier review:**
- none
