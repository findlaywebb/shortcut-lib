# Review: v15/model-calculateexpression

**Action**: `is.workflow.actions.calculateexpression`
**Files**: `src/shortcut_lib/schema/actions/calculate_expression.py` (+130 lines),
`tests/test_action_calculate_expression.py` (+236 lines)

---

## 1. Verdict

**Merge.** The wire-key claim, envelope type, jellycore attribution, and
required-field policy are all correct and verifiable against the corpus.
Doc quality is the strongest seen in this review series. No issues require
blocking.

---

## 2. Test result + prek

```
12 passed in 0.09s
```

All 8 prek hooks pass: ruff lint, ruff format, uv-lock, ty — clean.

---

## 3. What landed

Single action class (`CalculateExpression`) with one field (`expression:
ParamValue = None`). `_params()` is four lines: a None guard, then
`{"Input": coerce_text_field(self.expression)}`. Registry integration,
`default_output_name`, and `identifier` are all present. 12 tests cover
identifier/registry, plain string, variable interpolation (NamedVar and
Output), two full corpus wire-equivalence round-trips, chaining, and the
SchemaError guard.

---

## 4. Wire-key claim verification — `Input` vs `WFInput`

**Verified correct.** Both corpus appearances confirm the capitalised `Input`
key unambiguously:

```xml
<key>Input</key>
<dict>
    <key>Value</key>
    ...
    <key>WFSerializationType</key>
    <string>WFTextTokenString</string>
</dict>
```

The docstring's claim that this is "distinct from Math's `WFInput` slot" is
also correct: `math.py`'s `_params()` emits `out["WFInput"] = ...` (confirmed
in the sibling worktree). The `Input`/`WFInput` distinction is a meaningful
difference between the two actions and the docstring handles it cleanly.

Minor precision note: the docstring's source-notes section says "lines
396-424" but the enclosing `<dict>` opens at line 394. The identifier is on
line 396. This is cosmetically imprecise but not misleading — the test file
uses slightly tighter language ("Lines 394-424"), which is more accurate.
Not a blocker.

---

## 5. Envelope claim verification — `WFTextTokenString` with `attachmentsByRange`

**Verified correct.** Both corpus appearances follow the pattern exactly:

```xml
<key>WFSerializationType</key>
<string>WFTextTokenString</string>
```

with `Value` containing:

```xml
<key>string</key>
<string>&#xFFFC;</string>     <!-- U+FFFC object-replacement placeholder -->
<key>attachmentsByRange</key>
<dict>
    <key>{0, 1}</key>
    <dict>
        <key>Type</key>    <string>ActionOutput</string>
        <key>OutputName</key>  <string>Calculation Result</string>
        <key>OutputUUID</key>  <string>...</string>
    </dict>
</dict>
```

No `WFTextTokenAttachment` appears anywhere. The docstring's contrast with
Math's `WFTextTokenAttachment` is accurate. `coerce_text_field` is the right
helper here.

---

## 6. Source-attribution audit

No jellycore confabulation. `jq '.["is.workflow.actions.calculateexpression"]'
jellycore_facts.json` returns `null`. The docstring states this plainly:

> `data/jellycore_facts.json`: **no entry** for
> `is.workflow.actions.calculateexpression` — jellycore has not catalogued
> this action; all parameter names here are inferred from corpus inspection,
> not from jellycore.

Every claim in the docstring traces to a specific corpus line range. The
`OutputName` claim ("Calculation Result") is confirmed by both corpus
appearances independently. Attribution is exemplary.

---

## 7. Required-field policy — defensible?

**Yes, and well-justified by the corpus.** Both corpus appearances have
`Input` populated; neither is a bare `{UUID: ...}` action. A bare
`CalculateExpression` with no expression would be inert on-device — the
runtime has nothing to evaluate. Contrast with `Math`, where a bare instance
(no operands) is at least structurally valid (default-operator behaviour may
apply). The required-field guard here is appropriate given a 2/2 corpus rate
of `Input` presence and the action's semantic requirement for an expression
string.

The policy is consistent with the stated SchemaError convention elsewhere in
the codebase, and the error message (`"CalculateExpression requires
\`expression\`"`) matches the format the test asserts against.

---

## 8. Doc quality — 5/5

The best-documented action in the v15 series. Specific strengths:

- **Comparison prose** is accurate and actionable (when to use
  `CalculateExpression` vs `Math`, not just a vague disclaimer).
- **Wire-format block** in the docstring is a literal-XML approximation that
  matches the actual corpus structure — a reader can cross-check it directly.
- **Source notes** section is explicit about what came from the corpus, what
  came from jellycore, and what came from neither. No false certainty.
- **Args section** names the wire key and serialisation type inline, which is
  exactly the level of detail a SDK author needs.
- **Examples** cover all three realistic call forms (literal, NamedVar,
  chained output) without being padded.
- **Note** on runtime expression syntax is appropriately hedged ("The exact
  set of supported functions is not documented by Apple") rather than
  inventing capability claims.

No inflation, no over-hedging. The docstring does exactly what it needs to do.

---

## 9. Issues

None requiring action. The one cosmetic finding:

- Docstring source note says "lines 396-424"; the `<dict>` opens at 394.
  The test file is more precise ("Lines 394-424"). Consider updating the
  docstring's source note to "lines 394-424" for consistency, but this is
  not a merge blocker.

---

## 10. Merge recommendation

**Merge as-is.** The line-number imprecision in the docstring is cosmetic and
can be fixed in a follow-up if desired. All substantive claims are verified,
the guard policy is defensible, the test suite covers the corpus faithfully,
and the documentation sets the bar for this series.

## 2026-05-10 merge-readiness pass

**Verdict:** Fail-Sonnet → Pass (fixed inline at `24f46b5`)

**Branch HEAD:** `24f46b5` (diverges from _SUMMARY.md record `97f730d` — branch has 3 commits ahead of main: original schema commit `97f730d`, follow-up jellycore correction `ee83557`, and inline review fix `24f46b5`)

**Merge against main:**
- Result: clean
- Conflict files: none
- Resolution: No conflicts; main changes (CLAUDE.md, action-modelling.md, new v15-review files) merged without any overlap with branch additions.

**Pytest on merged state:** 342 passing, 0 failing, 7 skipped, 3 xfailed

**prek:** green (all 8 hooks passed on inline correction commit)

**Drift / observations:**
- Branch HEAD is `24f46b5` (3 commits ahead of main), not the `97f730d` recorded in _SUMMARY.md. The extra commit `ee83557` corrected a stale "no jellycore entry" claim — jellycore does have an entry for `is.workflow.actions.calculateexpression` with `parameter_keys: ["Input"]`. This was verified with the array-select form. The docstring on the branch correctly reflects the jellycore corroboration.
- Jellycore entry confirmed: `jq '.actions[] | select(.identifier == "is.workflow.actions.calculateexpression")' data/jellycore_facts.json` returns `display_name: "Calculate Expression"`, `parameter_keys: ["Input"]`. Both jellycore and corpus agree on the bare `Input` wire key.
- No sibling action drift found: the `Math` action's use of `WFInput` (distinct from this action's `Input`) remains correct per the review. No new sibling actions on main contradict the wire-key or envelope claims.
- The review file for this branch existed only on main (not on the branch) — written to the branch here so the section lands correctly on merge.

**Minor corrections applied:**
- `src/shortcut_lib/schema/actions/calculate_expression.py:61` — corrected corpus line citations from "396-424 and 4464-4492" to "394-424 and 4462-4492" (opening `<dict>` at those lines, consistent with test file citation style) (commit `24f46b5`)

**Concerns for higher-tier review:**
- none
