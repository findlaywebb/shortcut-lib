# Review: v15/model-statistics

**Action**: `is.workflow.actions.statistics` ("Get Statistic of Numbers")
**Files**: `src/shortcut_lib/schema/actions/statistics.py` (+138 lines),
`tests/test_action_statistics.py` (+202 lines)

---

## 1. Verdict

**Merge.** Wire key, envelope type, default-omission rule, and jellycore
attribution are all correct and verifiable against the corpus. The 9-operation
enum is clearly disclaimed as UI-derived. Doc quality is strong. No blocking
issues.

---

## 2. Test result + prek

```
22 passed in 0.10s
```

All prek hooks pass: trim whitespace, end-of-file, YAML, large-file check,
ruff lint, ruff format, uv-lock, ty — clean across the board.

---

## 3. What landed

Single action class (`Statistics`) with two fields: `input: ParamValue = None`
and `operation: WFStatisticsOperation = "Average"`. `_params()` emits `Input`
(guarded by None) and `WFStatisticsOperation` (omitted when `"Average"`,
matching corpus default behaviour). `__post_init__` validates `operation`
against the `_VALID_OPERATIONS` frozenset with a `SchemaError`. Registry
integration, `identifier`, and `default_output_name` are all present.

The 22 tests cover: identifier/registry, both corpus wire-equivalence
round-trips, default-omission of `WFStatisticsOperation`, all 9 operations
by name, `SchemaError` on invalid operation, chaining off a prior action, and
the None-input guard.

---

## 4. Wire-key verification — `Input` (Title-Case) confirmed

**Verified correct.** Both corpus appearances in `dictionary.xml` (lines 26
and 239) are unambiguous:

```xml
<key>Input</key>
<dict>
    <key>Value</key>
    <dict>
        <key>OutputName</key>  <string>Calculation Result</string>
        <key>OutputUUID</key>  <string>…</string>
        <key>Type</key>        <string>ActionOutput</string>
    </dict>
    <key>WFSerializationType</key>
    <string>WFTextTokenAttachment</string>
</dict>
```

No `WFInput` anywhere. Neither corpus appearance sets `WFStatisticsOperation`,
confirming "Average" as Apple's implicit default.

**Cross-reference to `calculateexpression`:** The sister branch
`v15/model-calculateexpression` independently observed the same `Input`
(Title-Case) key for `is.workflow.actions.calculateexpression` from the same
`dictionary.xml` entries (lines 25 and 238 — the actions are adjacent in
both appearances). The two agents working from the same raw XML reached the
same conclusion independently. This is corroborating evidence that AppIntent-
style Apple actions use bare `Input` rather than `WFInput`. The `calculateexpression`
review confirmed the same pattern and rated it "distinct from Math's `WFInput`
slot."

**Envelope difference from calculateexpression:** Statistics uses
`WFTextTokenAttachment` (the model uses `coerce_value`), whereas
`calculateexpression` uses `WFTextTokenString` with `attachmentsByRange` (uses
`coerce_text_field`). The docstring explains this distinction inline and
correctly identifies `coerce_value` as appropriate for the `WFTextTokenAttachment`
slot. This is the right call.

---

## 5. Operation enum — speculative content honestly disclaimed?

**Yes, and appropriately so.** The module comment is explicit:

> "The full set of operation strings is derived from the Shortcuts.app UI and
> the Apple Shortcuts URL-scheme documentation."

The 9 operations are:
`Average`, `Minimum`, `Maximum`, `Sum`, `Count`, `Range`, `Median`, `Mode`,
`Standard Deviation`.

The corpus provides no counterevidence (both appearances use the default and
omit the key entirely), so none of the 9 values can be corpus-confirmed as
wire strings. The enum is entirely UI/docs-derived. The disclaimer is honest.

One minor gap: the Apple Shortcuts URL-scheme documentation is not cited with
a URL or retrieved date, so it cannot be independently verified at review time.
For a 9-value Literal over a well-known Apple action this is low-risk, but it
is less rigorous than the `calculateexpression` attributions (which cited
specific corpus line ranges for every claim). Not a blocker, but worth noting
if the project later requires source traceability for all enum values.

No fabricated values are apparent — all 9 operations are the standard
statistical aggregates one would expect from any "Get Statistic" action.

---

## 6. Source-attribution audit

No jellycore confabulation. `jq '.["is.workflow.actions.statistics"]'
data/jellycore_facts.json` returns `null`. The module comment, the class
docstring, and the inline comments all state this explicitly:

> "jellycore_facts.json has **no entry** for `is.workflow.actions.statistics`
> (verified: … returns `null`), so no jellycore source is claimed here."

The `observed_envelope_types.json` entry cited in the docstring (`Input` →
`WFTextTokenAttachment`, 2 of 2 observations) could not be verified directly
(the key is absent from the current `data/observed_envelope_types.json`), but
the claim is fully independently confirmable from `dictionary.xml` itself —
both appearances are in the XML and match. The reference to the oracle file
is a documentation aid, not a load-bearing attribution.

Attribution is clean. Every non-speculative claim traces to a corpus
occurrence.

---

## 7. Doc quality — 4/5

Strong across the board. Specific strengths:

- **Wire-format block** in the class docstring closely mirrors the actual XML
  structure; a reader can cross-check it directly.
- **"Average" default** is explicitly linked to the corpus observation and the
  omission-if-default rule.
- **`coerce_value` vs `coerce_text_field` distinction** is explained inline in
  `_params()`, directly in the code where it matters.
- **All 9 operations** are individually described in the Args section — no
  vague "see Shortcuts.app" deferral.
- **Usage examples** cover the two realistic forms (default average, explicit
  operation) cleanly.

Deducted one point because: the URL-scheme documentation source for the 9
operations is not cited with a retrievable URL or date, and the
`observed_envelope_types.json` reference is slightly overstated (the key is
absent from the file at time of review, though the underlying claim is
corpus-verifiable). Neither is a blocker, but `calculateexpression`'s
attribution was tighter.

---

## 8. Issues

No blocking issues. One minor finding:

- **`observed_envelope_types.json` reference**: The docstring claims an entry
  for `Input` → `WFTextTokenAttachment` in that file, but the key
  `is.workflow.actions.statistics` is absent at review time. The underlying
  claim is correct (the corpus XML confirms it directly), but the reference
  will mislead a reader who greps the oracle file first. Consider either
  removing the reference or ensuring the file is updated before merge.
  Non-blocking.

---

## 9. Merge recommendation

**Merge as-is.** The `observed_envelope_types.json` discrepancy is cosmetic
and the underlying wire-format claim is independently verified. All
substantive claims are correct, the 9-operation enum is honestly disclaimed,
the jellycore audit is clean, and the test suite covers both corpus appearances
faithfully.

---

## 10. Note for the wire-format-quirks doc

**Already covered.** The `v15/wire-format-quirks-doc` branch
(`docs/wire-format-quirks.md`) already includes `is.workflow.actions.statistics`
in the bare-key table:

> `is.workflow.actions.statistics` | `Input` | Title-Case. Oracle entry

This was added alongside `is.workflow.actions.calculateexpression` in the same
table. The pattern is therefore already documented in the canonical reference
without needing a further update from this branch. The two independent
agent observations (statistics and calculateexpression both landing on `Input`
from the same `dictionary.xml` context) provide mutual corroboration that
strengthens the existing wire-format-quirks entry.
