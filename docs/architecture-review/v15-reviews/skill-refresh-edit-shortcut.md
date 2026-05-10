# Review: skill-refresh-edit-shortcut

Branch: `v15/skill-refresh-edit-shortcut` (head: `8f4c73c`)
Reviewer: Claude Sonnet 4.6 (autonomous review pass)
Date: 2026-05-09

---

## 1. Verdict

**Approve with one minor note.** The refresh is thorough and accurate. The five
new sections land cleanly, all code patterns are executable, and the SKILL now
correctly reflects the V1.5 `from_file()` path as the primary entry point.
The one item worth a follow-up is a small imprecision in the `_extra` section
(see Issues) — it does not block merge.

---

## 2. Sections added

The agent accurately reports five new sections:

| Section | Purpose |
|---|---|
| "Lifting a shortcut — `Shortcut.from_file()`" | Attribute table, round-trip guarantee, `_extra` explanation |
| "The `_extra` round-trip guarantee" | Tells the LLM what it does and doesn't need to preserve |
| "Surgical edits via `RawAction` mutation" | Four copy-paste patterns: find / mutate / delete / add |
| "Re-author from scratch (Strategy B)" | Cross-link to `make-shortcut/SKILL.md` |
| "Decode for inspection only" | Cross-link to `decode-shortcut` skill |

The Strategy A/B/C reframing in Step 3 replaces an earlier unstructured paragraph.
Strategy C (hybrid splice) is new and includes a concrete code block showing
`s.add()` followed by `s.actions.remove()` / `s.actions.insert()`.

The `setup_questions` duplication gotcha appears in the Constraints section as its
own bullet, and the "Unmodelled actions are fine" constraint is also new.

---

## 3. LLM-author walkthrough

**Would Claude succeed first-shot on "modify this shortcut to also do X"?**

Reading top-to-bottom as a receiving agent:

- **Routing** — The "When to use" triggers are clear: "edit", "change",
  "modify", "tweak" all land here. The negative cases (brand-new → make-shortcut,
  inspect only → decode-shortcut) are called out explicitly.
- **Pre-reading** — Mandatory pre-reading list is identical to make-shortcut:
  `roadmap.md`, `format.md`, and `print_actions.py`. Consistent, appropriate.
- **Decode first (Step 2)** — The skill correctly teaches Claude to run
  `shortcut-decode --format buzz` before touching any code. This is the right
  discipline: understand before you edit.
- **Strategy selection (Step 3)** — Strategy A is named the default. An agent
  reading this would pick A for small dict mutations (correct), escalate to B
  when a re-author is cheaper (correct), and reach for C (hybrid splice) for the
  middle case. The escalation ladder is clear and the code block for C is
  concrete enough to follow.
- **From-file snippet** — The opening code block in the Strategy A description
  is minimal and correct: import, call `from_file`, print `len(s.actions)`,
  call `save_signed`. An LLM can copy and adapt this with no ambiguity.
- **Surgical edits** — The four `RawAction` patterns (find, mutate, delete, add)
  are correctly written Python. The `raw_identifier` match pattern, the
  `raw_params` dict mutation, the `del s.actions[i]` drop, and the `s.add()` +
  `s.actions.remove()` / `s.actions.insert()` splice are all executable. Spot-
  checking "Replace a parameter value" against the source: `RawAction.raw_params`
  is defined as `dict(params)` in `from_workflow` (line 449 of builder.py), so
  it is a plain mutable dict — the pattern is correct.
- **Verify step (Step 4)** — Re-decode + buzz diff + `uv run pytest` is exactly
  right. An LLM following this would catch a bad variable wire-up before handing
  off.

**First-shot success probability: high.** The gap between "Strategy A preferred"
and "Strategy C concrete code" is narrow enough that an agent would likely reason
straight to the correct approach. No dead ends, no retired APIs in the
recommended flow.

---

## 4. The `setup_questions` duplication gotcha — accuracy check

**Claimed behaviour:** If a shortcut was lifted via `from_file()` and the file
had `WFWorkflowImportQuestions`, those questions are in `s.setup_questions`. If
the user also adds a `WFWorkflowImportQuestions` key to `_extra` directly, there
will be a duplicate on re-emit (the `out.update(self._extra)` call at line 358
of builder.py overwrites the list that `to_workflow` built from `setup_questions`
at line 345).

**Is the concern real?**

Yes, and the code confirms it. In `to_workflow`, the emit order is:

1. Line 345: `"WFWorkflowImportQuestions": import_questions` — emitted from
   `self.setup_questions`.
2. Line 358: `out.update(self._extra)` — runs after, unconditionally.

If `_extra` contains a `WFWorkflowImportQuestions` key, it will silently overwrite
the value built from `setup_questions`. The normal lift path does not put
`WFWorkflowImportQuestions` into `_extra` — `_ATTRIBUTE_KEYS` explicitly excludes
it (line 131 of builder.py) so `from_workflow` never captures it there. However,
if questions were malformed or out-of-range, `from_workflow` falls back to storing
the raw list in `_extra["WFWorkflowImportQuestions"]` (line 483). In that narrow
case, both `setup_questions` (empty, because malformed) and `_extra` (populated
with the fallback raw list) are in play, and `out.update` produces the correct
wire format — the fallback case is intentional and safe.

The SKILL's warning is aimed at a different failure mode: an LLM that manually
constructs `_extra["WFWorkflowImportQuestions"]` on top of an existing
`setup_questions` list would silently lose the `setup_questions` data. That
scenario is realistic for an over-eager agent who read the `_extra` docs and
tried to be helpful. The warning is accurate and appropriately flagged.

**Minor imprecision:** The SKILL says "don't also add a `WFWorkflowImportQuestions`
key to `_extra` or you'll get a duplicate on re-emit." Strictly, you would not
get a duplicate — you would get a silent overwrite (the `_extra` version would
win). The word "duplicate" could mislead. "Overwrite" or "silent replacement" is
more accurate. This is cosmetic, not a behaviour error.

---

## 5. Cross-skill style consistency with the make-shortcut refresh

Both skills were read end-to-end. Style is consistent across:

- **Tone** — imperative, direct, no hedging. "The preferred V1.5 path." matches
  "The lib's full authoring surface" in make-shortcut.
- **Section ordering** — When to use / Mandatory pre-reading / Workflow steps /
  named reference sections / Constraints. Both follow this pattern.
- **Code block conventions** — Python blocks use 4-space indent, include imports,
  use snake_case for all locals. Shell blocks use the same `cd ~/personal/shortcut-lib`
  header line. Consistent.
- **Cross-reference style** — Both use bare filename references ("see
  `make-shortcut/SKILL.md`") rather than absolute paths. Consistent.
- **Constraints section** — Both end with a bulleted Constraints block using the
  same bold-verb pattern ("Don't break", "Don't re-sign", "Use real Apple keys").

One small divergence: make-shortcut uses explicit step numbers through Step 6;
edit-shortcut ends at Step 5 (no "Run and verify" as its own top-level step —
verification is folded into Step 4). This is appropriate given the different
workflow shape, not an inconsistency.

The two SKILL files read as authored by the same writer. A receiving agent would
experience consistent framing across both.

---

## 6. Issues

**Issue 1 — "duplicate" vs "overwrite" in the gotcha constraint (minor)**

Location: Constraints section, last bullet.

> "don't also add a `WFWorkflowImportQuestions` key to `_extra` or you'll get a
> duplicate on re-emit."

`out.update(self._extra)` overwrites the prior value — there is no duplicate
key in the output dict, just a silent replacement. The risk is data loss (the
`setup_questions`-derived list is discarded), not a malformed plist. Suggested
replacement: "you'll silently overwrite the `setup_questions`-derived list on
re-emit."

This is cosmetic. The practical warning (do not manually add that key) is
correct.

**No other issues found.** The `decode_file` + `sign_to_file` low-level path is
absent from the recommended-strategy section (it does not appear anywhere in the
Workflow steps), confirming it has been correctly retired from the primary flow.
The existing Step 1 (locate), Step 2 (decode + buzz digest), and Step 5 (hand
off) are intact and unchanged in substance. Pre-commit hooks pass clean (all 8
checks pass on `--all-files`).

---

## 7. Merge recommendation

**Merge.** The one imprecision ("duplicate" vs "overwrite") is cosmetic and does
not affect agent behaviour — an LLM following the constraint would correctly
avoid adding that key regardless of which word describes the failure mode. The
substantive content — the lifting flow, the `_extra` guarantee, the surgical edit
patterns, the duplication gotcha, and the Strategy A/B/C ladder — is accurate,
executable, and well-framed. The SKILL is a meaningful improvement over the V1
version and is consistent with its companion `make-shortcut` refresh.

## 2026-05-10 merge-readiness pass

**Verdict:** Fail-Sonnet → Pass (fixed inline at `ecd0ce5`)

**Branch HEAD:** `ecd0ce5` (diverges from _SUMMARY.md record `8f4c73c` — one additional inline-fix commit added during this pass)

**Merge against main:**
- Result: clean
- Conflict files: none
- Resolution: `git merge main --no-commit --no-ff` completed automatically; no conflicts in `docs/known_identifiers.md` or anywhere else. All `main`-only files are additions (new review docs, CLAUDE.md, .gitignore updates) with no overlap with this branch's single changed file (`skills/edit-shortcut/SKILL.md`).

**Pytest on merged state:** 330 passing, 6 skipped, 3 xfailed, 8 warnings

**prek:** skipped (doc-only branch; no Python files changed; hook suite passed during fix commit)

**Drift / observations:**
- Branch changes exactly one file: `skills/edit-shortcut/SKILL.md`. Main's 14-commit advance adds only review docs, CLAUDE.md, and minor infra. No schema, test, or envelope changes that could contradict this branch.
- No `docs/known_identifiers.md` conflict — the file was not touched by this branch at all (the brief's note about a potential dirty-worktree `M docs/known_identifiers.md` did not materialise).
- Cross-skill style with the `make-shortcut` refresh (confirmed by prior review) is unaffected by main's advance.

**Minor corrections applied:**
- `skills/edit-shortcut/SKILL.md:293` — "you'll get a duplicate on re-emit" → "you'll silently overwrite the `setup_questions`-derived list on re-emit". Fixes the wording nit flagged in the 2026-05-09 review: `out.update(self._extra)` overwrites, it does not produce a duplicate key. (commit `ecd0ce5`)

**Concerns for higher-tier review:**
- none
