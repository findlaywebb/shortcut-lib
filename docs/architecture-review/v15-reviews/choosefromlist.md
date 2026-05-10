# Review: v15/model-choosefromlist

**Branch:** `v15/model-choosefromlist` (head: 925054d)
**Reviewer:** automated (agent)
**Date:** 2026-05-09

---

## 1. Verdict

Approved. The schema is well-grounded, the wire keys are exactly right, field
omission behaviour matches Apple's corpus, and all 16 tests pass cleanly. The
`select_all_initially` field is correctly signalled as Jellycore-only. The only
notable item is the `docs/known_identifiers.md` update, which is a full
corpus regeneration rather than a targeted append — this is a clean side-effect
but reviewers should understand what they are approving.

---

## 2. Test result

```
16 passed in 0.09s
```

All 16 tests pass. Pre-commit (ruff lint, ruff format, ty, uv-lock) is clean.

---

## 3. What landed

Three files added or modified:

- `src/shortcut_lib/schema/actions/choose_from_list.py` — 64 lines, new action schema.
- `tests/test_action_choose_from_list.py` — 267 lines, 16 tests.
- `docs/known_identifiers.md` — updated.

The diff stat also shows four `.md` files deleted from
`docs/architecture-review/v15-reviews/`. These are earlier review documents
(filter-calendarevents, previewdocument, schema-gaps-inventory, sendmessage)
that were present on the branch but have been removed. This is unrelated to
the choosefromlist work itself and should be confirmed as intentional before
merge.

**`docs/known_identifiers.md` — regeneration, not targeted append.** The
full diff reveals that the corpus underlying the table changed: the
`voice_note_to_github` sample was removed and an `intelly` sample was added.
The `choosefromlist` entry (`| 2 | ... | dictionary, set_weekend_chores |`)
appears correctly. Counts and "seen in" lists for several other identifiers
shifted accordingly (e.g. `setvariable` 27→19, `gettext` 18→12,
`text.replace` 8→6). This is a clean regeneration — no invented entries, no
corruption — but it is broader in scope than the action schema change.
Reviewers accepting this PR accept the corpus swap too.

---

## 4. Sample grounding

**Two corpus appearances confirmed** — exactly as claimed:

| Sample | Action index | Key fields present |
|---|---|---|
| `set_weekend_chores.xml` | 1 | `WFChooseFromListActionPrompt`, `WFChooseFromListActionSelectMultiple=true`, `WFInput` |
| `dictionary.xml` | 13 | `WFInput` only |

**Wire key capitalisation** (`WFChooseFromListActionPrompt`) confirmed correct
with capital P. The raw XML at line 162 of `dictionary.xml` and in
`set_weekend_chores.xml` both use exactly this key. The schema emits the same
string verbatim.

**`default_output_name = "Chosen Item"`** is grounded in `set_weekend_chores.xml`
where the `repeat.each` loop references the output of this action by that name.

**`select_all_initially` / `WFChooseFromListActionSelectAll`** does not appear
in either corpus sample. The class docstring references Jellycore as the
source, but the field docstring does not contain an explicit
"sample-unverified" or "Jellycore-only" warning at the parameter level — only
the class-level docstring implies it by listing only the four confirmed-against-
samples fields. A sentence like `# Jellycore-only; no corpus sample observed`
inline in `_params()` or the field docstring would make this clearer. This is
a minor nit, not a blocker.

The two equivalence tests (`test_choose_from_list_wire_format_minimal` and
`test_choose_from_list_wire_format_multi_select`) reconstruct the corpus UUIDs
verbatim and compare normalised dicts — both pass, confirming exact wire parity.

---

## 5. Issues

**Minor — `select_all_initially` unverified status not surfaced at field level.**
The class docstring mentions the four confirmed parameters by name, which
implicitly marks `WFChooseFromListActionSelectAll` as unconfirmed, but a reader
looking only at the field definition or `_params()` body gets no signal. Add a
one-line comment in `_params()` above the `select_all_initially` branch, e.g.:

```python
# WFChooseFromListActionSelectAll: Jellycore-only; absent from all corpus samples.
if self.select_all_initially is not None:
```

This follows the pattern the codebase uses elsewhere for speculative fields.

**Observation — four v15-review docs deleted.** The branch removes
`filter-calendarevents.md`, `previewdocument.md`, `schema-gaps-inventory.md`,
and `sendmessage.md` from the review directory. These may have been superseded
or cleaned up intentionally, but the change is unrelated to the choosefromlist
work. Confirm intent before merge.

**No issues with correctness, identifier, types, or registry registration.**

---

## 6. Merge recommendation

**Merge after confirming** the two observations above:

1. The deletion of four v15-review `.md` files is intentional (one-word
   confirmation sufficient).
2. Either accept the `select_all_initially` docstring nit as-is or apply the
   one-line comment fix — either is fine; it does not affect correctness.

The schema itself is production-quality: correct identifier, correct wire keys,
correct omission semantics, two passing wire-format equivalence tests, and
clean pre-commit output.

## 2026-05-10 merge-readiness pass

**Verdict:** Fail-Sonnet → Pass (fixed inline at `db270b3`)

**Branch HEAD:** `db270b3` (diverges from _SUMMARY.md record `925054d` — one inline correction commit added during this pass)

**Merge against main:**
- Result: clean
- Conflict files: none
- Resolution: Automatic merge succeeded with no conflicts. `docs/known_identifiers.md` was regenerated on the branch but the merge resolved cleanly without manual intervention.

**Pytest on merged state:** 347 passing, 6 skipped, 3 xfailed

**prek:** green (pre-commit hooks passed on inline correction commit)

**Drift / observations:**
- The four v15-review docs that were deleted on this branch (`filter-calendarevents.md`, `previewdocument.md`, `schema-gaps-inventory.md`, `sendmessage.md`) all reappear via main — no net deletion after merge. This was a pre-existing observation from the original review and is now moot.
- No sibling actions on main contradict the wire-key conventions or envelope choices used here. `WFInput` as a bare attachment slot and `WFChooseFromListActionPrompt` as a `WFTextTokenString` slot are consistent with the envelope oracle.
- 9 warnings from test_envelope_oracle.py (oracle gaps for choosefromlist prompt, comment text, getvariable, notification title) — pre-existing, not introduced by this branch.

**Minor corrections applied:**
- `src/shortcut_lib/schema/actions/choose_from_list.py:62` — added `# WFChooseFromListActionSelectAll: Jellycore-only; absent from all corpus samples.` comment above the `select_all_initially` branch in `_params()`, as recommended by the original review (commit `db270b3`)

**Concerns for higher-tier review:**
- none
