# Review: v15/model-gettraveltime

**Verdict: green**
**Branch:** `v15/model-gettraveltime` (head: `aae1eeb`)
**Reviewer:** Claude Sonnet 4.6 (autonomous, 2026-05-09)

---

## Test result

14/14 passed, 0 failures, 0 skipped. All pre-commit hooks pass (ruff lint,
ruff format, ty, uv-lock).

---

## What landed

Two files changed (+329 lines):

- `src/shortcut_lib/schema/actions/get_travel_time.py` — 76 lines. Typed
  schema for `is.workflow.actions.gettraveltime`. Three fields, one Literal
  alias, `__post_init__` validation, clean `_params()` with inline comments
  explaining each wire-key decision.
- `tests/test_action_get_travel_time.py` — 253 lines. 14 tests covering all
  four transport modes (emission and omission), invalid-mode rejection,
  `WFDestination` envelope shape, `None`-destination and `None`-origin
  omission, registry lookup, `default_output_name`, and three wire-format
  equivalence tests pinned to real corpus indices.

---

## Corpus appearances confirmed

Exactly 3 appearances, independently verified from raw XML:

| File | Index | WFDestination | WFTransportType |
|---|---|---|---|
| `running_late.xml` | 1 | `WFTextTokenAttachment` / "Calendar Events" | absent (Driving) |
| `dictionary.xml` | 114 | `WFTextTokenAttachment` / "Halfway Point" | absent (Driving) |
| `dictionary.xml` | 320 | `WFTextTokenAttachment` / "Maps URL" | absent (Driving) |

All three appearances confirmed. All three use the Driving default; the
`WFTransportType` key is absent in each case. No sample uses a non-default
transport type — this is a genuine corpus limitation for this action,
acknowledged explicitly in the test docstring for
`test_gettraveltime_default_transport_omits_key`.

---

## The corpus correction: `coerce_value` not `coerce_text_field`

The brief speculated `WFDestination` might use a `WFTextTokenString` envelope
(as `coerce_text_field` would produce). The agent overrode this and used
`coerce_value` (bare `WFTextTokenAttachment` envelope) instead. This is
correct. All three corpus samples carry:

```xml
<key>WFDestination</key>
<dict>
    <key>Value</key>
    <dict>
        <key>OutputName</key><string>…</string>
        <key>OutputUUID</key><string>…</string>
        <key>Type</key><string>ActionOutput</string>
    </dict>
    <key>WFSerializationType</key>
    <string>WFTextTokenAttachment</string>
</dict>
```

No `WFTokenAttachmentsByRange`, no outer `string` key — the signature of
`WFTextTokenString` is entirely absent. The agent correctly read the samples
and overrode the brief's speculation. This was the right call and is
well-documented in the implementation docstring and inline comments. The three
wire-format equivalence tests pass, which would fail if the wrong coerce
function were used.

---

## The `origin` field: speculative but adequately marked

`WFFromAddress` does not appear in any of the three corpus samples. The agent
modelled it based on Apple's Shortcuts action surface (the Maps action has an
explicit From/To pair). The docstring states clearly:

> "When omitted, Shortcuts uses the device's current location. Corresponds to
> Apple's `WFFromAddress` parameter."

The implementation omits the key entirely when `origin=None`, which is the
safe default. The key spelling `WFFromAddress` is inferred — it does not
appear in `jellycore_facts.json` (the action `is.workflow.actions.gettraveltime`
is absent from that dataset entirely). No Jellycore fact to cross-check against.

Compared with the `addnewreminder` discipline: the reminder review flagged
`"When I Leave"` as needing a one-line speculation comment (minor, not a
blocker). The `gettraveltime` docstring names the Apple parameter and explains
the default behaviour but does not explicitly mark `WFFromAddress` as
corpus-unverified. This is a minor gap — a note such as `# WFFromAddress —
modelled from Apple surface; not observed in corpus samples` in `_params()`
would bring it to the same standard.

The risk level is low: emitting the key with a bad spelling would simply fail
at Shortcuts runtime, not silently corrupt the workflow. The field is optional
and gated on `origin is not None`, so callers who don't use it are entirely
unaffected.

---

## Issues

### Blockers

None.

### Design opportunities

**1. `WFFromAddress` corpus-unverified annotation is missing.**

The docstring describes the field's semantics but does not flag it as sample-
unverified. A one-line inline comment in `_params()` (mirroring the treatment
applied to similar speculative fields elsewhere) would make the assumption
explicit. Consistent with the `addnewreminder` "When I Leave" note — apply
before merge if easy, not a hard blocker.

**2. All three corpus samples use Driving; no sample validates non-default transport emission.**

The four non-default transport modes (Walking, Transit, Cycling) are exercised
by unit tests only. This is correct V1 behaviour for a small corpus, but means
the `WFTransportType` string values are sourced from Apple docs reasoning, not
confirmed round-trips. The `WFTransportType` Literal comment in the source
notes this explicitly. If a corpus sample with a non-default mode is found in
future, a wire-equivalence test should be added.

**3. `origin` accepts `ParamValue` but only `WFTextTokenAttachment` is tested.**

The `test_gettraveltime_origin_emits_wffromaddress` test uses an `Output`
(which becomes a `WFTextTokenAttachment`). A bare string origin (which would
emit differently) is untested. Low risk given V1 scope, but worth noting.

---

## Merge recommendation

**Merge.** All 14 tests pass, full pre-commit suite is clean. The agent's
override of the brief on `coerce_text_field` → `coerce_value` is correct and
evidenced by three independent wire-format equivalence tests that would fail
under the wrong choice. The `origin` field is speculative but safe, gated on
`is not None`, and consistent with Apple's known action surface. The one minor
documentation gap (no explicit corpus-unverified annotation on `WFFromAddress`)
can be addressed in a follow-up pass or squashed into the commit before merge
— it does not block correctness.

## 2026-05-10 merge-readiness pass

**Verdict:** Fail-Sonnet → Pass (fixed inline at `0d9718f`)

**Branch HEAD:** `0d9718f` (diverges from _SUMMARY.md record `aae1eeb` — one review: commit added)

**Merge against main:**
- Result: clean
- Conflict files: none
- Resolution: Automatic merge succeeded with no conflicts. Main has advanced 17 commits (new review files, docs, CLAUDE.md, .gitignore) but none touch the branch's two new files.

**Pytest on merged state:** 345 passed, 6 skipped, 3 xfailed — all green

**prek:** green (all hooks pass on the correction commit: ruff lint, ruff format, ty)

**Drift / observations:**
- Main has gained many new action models and review files since the branch was cut; none overlap with `get_travel_time.py` or its tests.
- `WFFromAddress` wire key remains unobserved in corpus across all newly merged actions — no drift contradiction found.
- `WFDestination` envelope choice (`coerce_value` / `WFTextTokenAttachment`) is consistent with the pattern used by sibling map-family actions on main (`getdistance`, `maps`).
- Transport mode Literal values (`Driving`, `Walking`, `Transit`, `Cycling`) are consistent with Apple surface; no corpus sample on main contradicts them.

**Minor corrections applied:**
- `src/shortcut_lib/schema/actions/get_travel_time.py:44-47` — added "Wire key inferred from Apple action surface — not observed in corpus samples; no jellycore entry." to `origin` arg docstring (commit `0d9718f`)
- `src/shortcut_lib/schema/actions/get_travel_time.py:71-73` — added inline comment `# WFFromAddress — modelled from Apple action surface; not observed in corpus samples and absent from jellycore_facts.json.` in `_params()` (commit `0d9718f`)

**Concerns for higher-tier review:**
- none
