# v15/model-number-actions Review: `Number` + `RandomNumber`

**Branch:** `v15/model-number-actions` (head: `1c3c8cf`)
**Date:** 2026-05-10
**Reviewer:** Claude Sonnet 4.6 (automated)

---

## 1. Verdict

**Merge with one clarification.** Both actions are cleanly implemented, all
19 tests pass, prek is green, and every wire key is jellycore-confirmed. One
attribution gap exists: `default_output_name = "Number"` for the `Number`
class is not corpus-confirmed (the output is never referenced downstream),
and the docstring doesn't say so. The `RandomNumber` output name
(`"Random Number"`) is corpus-confirmed twice. No blocking issues.

---

## 2. Test Result + Prek

```
19 passed in 0.80s
```

All prek hooks passed (trailing whitespace, YAML, large files, ruff lint,
ruff format, uv-lock, ty). Clean.

---

## 3. What Landed — Per Action

### `Number` (`is.workflow.actions.number`)

- Single optional param `number: ParamValue = None`.
- When `None`, emits no `WFNumberActionNumber` key (corpus-accurate).
- When `0` (explicit int), emits the key with value `0` — correctly
  distinguished from `None` so users can write an explicit zero without
  getting omit behavior.
- 9 tests: identifier, default_output_name, registry, None-omits-key,
  int-literal, float-literal, zero-emits-key, chaining, corpus wire
  equivalence.

### `RandomNumber` (`is.workflow.actions.number.random`)

- Two optional params `minimum: ParamValue = None`,
  `maximum: ParamValue = None`.
- Each omitted independently when `None` — allows one-sided bounds.
- 10 tests: identifier, default_output_name, registry, no-bounds-omits,
  min-only, max-only, both, float-bounds, chaining, corpus wire
  equivalence.

---

## 4. Wire-Key Verification

### `Number`

| Key | Jellycore | Corpus | Implementation |
|-----|-----------|--------|----------------|
| `WFNumberActionNumber` | confirmed (`parameter_keys: ["WFNumberActionNumber"]`) | absent (both appearances UUID-only) | present, gated on `number is not None` |

Wire contract is correct. The key must be omittable (corpus) and must be
writable when provided (jellycore). Both are handled.

### `RandomNumber`

| Key | Jellycore | Corpus | Implementation |
|-----|-----------|--------|----------------|
| `WFRandomNumberMinimum` | confirmed | absent (UUID-only) | present, gated on `minimum is not None` |
| `WFRandomNumberMaximum` | confirmed | absent (UUID-only) | present, gated on `maximum is not None` |

Both keys correct. The independent-omission pattern is appropriate since
the Shortcuts UI treats them as separate fields.

---

## 5. Source-Attribution Audit

The agent that discovered the jellycore jq bug (`jq '.["id"]'` on an array
rather than `jq '.actions[] | select(.identifier == ...)'`) demonstrated
real verification discipline — catching the failure rather than trusting
null output. That improves confidence in the rest of the jellycore data.

Specific checks:

**`WFNumberActionNumber`** — correct. Jellycore lists it as the sole
parameter key for `is.workflow.actions.number`.

**`WFRandomNumberMinimum` / `WFRandomNumberMaximum`** — correct. Jellycore
confirms both. Corpus is silent (defaults only) but does not contradict.

**`default_output_name = "Random Number"`** — corpus-confirmed. Both
downstream `round` actions (lines 314 and 4592 in `dictionary.xml`)
reference `OutputName: "Random Number"` pointing to the random-number UUID.
The docstring correctly cites this (lines 314 and 4592).

**`default_output_name = "Number"`** — NOT corpus-confirmed. The two
`number` action UUIDs (`BF31D62D` and `EE1262AB`) appear exactly once each,
only in their own action's UUID field. Neither appears as an `OutputUUID` in
any downstream action. The name "Number" is reasonable (matches Apple's
display name per jellycore: `"display_name": "Number"`) but the docstring
does not acknowledge the gap. The `round` actions in both corpus samples
reference the `random_number` output, not the `number` output. The `number`
action is effectively a dead branch in both corpus samples.

This is a documentation gap, not an implementation bug. The
`default_output_name` convention across this library appears to be "use
Apple's display name when corpus is silent" — which is fine, but should be
stated.

---

## 6. Doc Quality

### `Number` — 4/5

Strong. Explains the "numeric equivalent of Text", correctly describes the
corpus omit-default behavior, distinguishes `None` vs explicit `0`,
documents the wire format precisely. Loses one point because it claims the
output name is "Number" without noting that this is inferred from the
display name, not confirmed by a downstream `OutputUUID` reference. The
corpus notes at the bottom don't mention the output-name source.

### `RandomNumber` — 5/5

Excellent. Explicitly cites the corpus line numbers for both the action and
the downstream `round` reference. Notes Apple's apparent UI default (0–100).
Honestly documents the jellycore jq bug that led to the data being found
late. The return value section is precise. The attribution is transparent.

---

## 7. Bundling — Defensible?

Yes. The two actions are semantically paired (Number + Random Number appear
together in both corpus samples, always followed by a `round` action), share
the same iOS 14 floor, use the same review checklist, and are short files
(60 and 77 lines). Bundling saves two review cycles for nearly identical
work. The atomicity cost is real — a reviewer who wants `Number` but not
`RandomNumber` is stuck — but given the quality level here (both clean,
both tested, prek green) the risk of needing to split is low. Acceptable.

---

## 8. Issues

**Issue 1 (documentation, non-blocking):** `Number.default_output_name`
is inferred from the Apple display name, not confirmed by a downstream
corpus reference. The `RandomNumber` docstring explicitly cites corpus line
numbers for its output name. `Number` should acknowledge the inference
source ("inferred from Apple display name; corpus samples do not reference
this output downstream").

No other issues found.

---

## 9. Merge Recommendation

**Merge.** All tests pass, prek is clean, wire keys are jellycore-confirmed,
and the source attribution is honest for `RandomNumber`. Fix the `Number`
docstring (one sentence to note the display-name inference) either in this
branch before merge or as a follow-on, per preference. Not a blocker.
