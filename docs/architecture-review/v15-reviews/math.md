# Review: `v15/model-math`

**Branch head:** `2cdc16e` — `schema: model math — Calculate / Math action (v1.0 build-out)`
**Reviewer:** main thread (sub-agent budget exhausted; resets 23:40 London).

## Verdict

**Merge with one inline correction.** Arithmetic mode is corpus-grounded and excellently documented. Scientific mode is wholly speculative, but the docstring overstates the source by attributing it to Jellycore — which has **no entry for `is.workflow.actions.math`**. The fix is small and important; the rest is solid.

## Test result

- `tests/test_action_math.py` — **25 / 25 pass** (`uv run pytest`).
- `prek run --all-files` — green.
- New `pyproject.toml` per-file-ignores for `RUF001`/`RUF002` are correctly scoped to `math.py` and `test_action_math.py` only — the Apple Unicode operator characters trigger ruff's ambiguous-character warnings, and the suppression is the right call.

## What landed

- `Math` action class (identifier `is.workflow.actions.math`).
- Four fields:
  - `input: ParamValue = None` → `WFInput`, encoded via `coerce_value` (yields `WFTextTokenAttachment` envelope for action outputs / variables).
  - `operation: WFMathOperation = "+"` → `WFMathOperation`, omitted when `"+"` (the wire-format default).
  - `operand: ParamValue = None` → `WFMathOperand`.
  - `scientific_operation: WFScientificOperation | None = None` → `scientific` key; suppresses `WFMathOperation` when set.
- Two Literal sets: 5 arithmetic operations (`"+"`, U+2212, U+00D7, U+00F7, `"Modulo"`); 13 scientific operations.
- Two wire-equivalence tests against `dictionary.xml` (lines 373 + 4455).
- Default output name `"Calculation Result"`.

## Sample-grounding

Two corpus appearances examined:

1. **`dictionary.xml:373`** — `WFInput` bound to `"Numbers"` action output via `WFTextTokenAttachment`; no `WFMathOperation`, no `WFMathOperand`.
2. **`dictionary.xml:4455`** — bare action with only a `UUID` key.

Both confirm:

- `WFInput` is a single-attachment slot (correctly encoded with `coerce_value`, *not* `coerce_text_field` — this is a single variable-reference slot, not an interpolated-text slot like `DownloadURL.WFURL`).
- `WFMathOperation` is omitted when default `"+"`.
- `WFMathOperand` is omitted when not specified.

The schema's arithmetic-mode behaviour matches the corpus exactly.

## The scientific-mode source claim — needs correction

The module docstring (line 38) currently reads:

> Wire-format strings sourced from Jellycore's action catalogue and cross-referenced against Apple's Shortcuts.app UI labels (iOS 17 / macOS 14).

This is **false**. `jq '.["is.workflow.actions.math"]' data/jellycore_facts.json` returns `null`. There is no jellycore entry for this identifier. Combined with the absence of any corpus sample exercising scientific mode (`grep -rn "scientific" samples/decoded/` returns nothing), **the entire `WFScientificOperation` Literal set, the `scientific` parameter key name, and the `x^y → WFMathOperand` exponent rule are inferences from Apple's UI alone**.

That doesn't make them wrong — they're plausible — but the docstring should say so honestly. The rest of the project follows a "sample-grounded > jellycore > UI-derived" discipline, and an undeclared UI-only claim corrodes the discipline elsewhere.

**Recommended fix (inline before merge):**

```diff
- # Wire-format strings sourced from Jellycore's action catalogue and
- # cross-referenced against Apple's Shortcuts.app UI labels (iOS 17 / macOS 14).
- # Use the exact codepoints below — do not substitute ASCII approximations.
+ # Wire-format strings inferred from Apple's Shortcuts.app UI labels
+ # (iOS 17 / macOS 14). Neither jellycore nor any decoded corpus sample
+ # confirms the `scientific` parameter key, the operation token strings,
+ # or the x^y exponent rule — they are speculative pending a fresh
+ # sample exercising scientific mode. Use the exact codepoints below;
+ # do not substitute ASCII approximations.
```

A matching one-liner in the class docstring's "Scientific mode" paragraph is also warranted: "*Note: this branch of the action is not corpus-confirmed; see the module docstring.*"

## Doc quality

**Arithmetic section: 5/5.** Apple display name, identifier, RST-table of operators with codepoint commentary, omit-if-default rule, two corpus citations with line numbers, minimum-host annotation, four working examples, all parameters annotated with type / wire-key / encoding / omission rule. This is the bar.

**Scientific section: 4/5 → 5/5 with the source-claim fix.** Same structural quality as arithmetic, but the false jellycore attribution undermines the trust the rest of the docstring earns.

## Issues

1. **Source-claim correction** — see above. Required before merge.
2. **Module-private operator constants** — `_SUBTRACT`, `_MULTIPLY`, `_DIVIDE`, `_SQRT`, `_CBRT` carry leading underscores (signalling private) but the docstring imports them publicly. Either rename them without the underscore (`SUBTRACT = "−"`) or drop them entirely and let users use the literal codepoints (the Literal type already constrains the values). My preference: drop them — five aliases for a 5-Literal set is a clutter trade. Not blocking; can be a follow-up.
3. **Unverified jellycore minimum-host claim** — the docstring states "iOS 14 / macOS 11 (per Jellycore's `lowest_compatible_host` catalogue entry)". Same problem: there is no jellycore entry. Either remove or re-source. Required before merge.
4. **`__post_init__` doesn't validate scientific-only/arithmetic-only field interaction** — e.g. setting both a non-default `operation` and a `scientific_operation` is silently accepted with `operation` ignored. The docstring says "ignored when scientific is set" but the `_params` only acts on it; `__post_init__` could warn or `SchemaError`. Optional follow-up.

## Class-name + naming notes

- `Math` — no builtin collision (math is a stdlib module that's not imported here). Defensible.
- `WFMathOperation` / `WFScientificOperation` Literal type aliases — consistent with project convention.
- The `_SCIENTIFIC_WITH_OPERAND` frozenset is a nice touch; documents the exception cleanly.

## Merge recommendation

Apply the **two source-claim corrections** (scientific-mode comment + minimum-host line) inline before merging. The arithmetic side is excellent; the scientific side becomes excellent once it stops claiming a source it doesn't have. Test count post-merge: +25 (361 total when this and the rest of batch 9 land).

Position in tier: **Tier 3 — action coverage**, no merge-order constraints with any other v15 branch.
