# shortcut-lib — agent operating notes

A Python library for authoring Apple Shortcuts. **The primary user is an LLM (you), not a human** — error quality, docstring discipline, and registry introspection are load-bearing UX. The human (Findlay) tells the LLM what to make.

## Versioning

- **Pre-1.0 versions are an alpha/beta sequence.** 0.X is the development phase; X just counts significant pre-1.0 cuts. 0.99 → 0.100 is valid before 1.0. **Never imply "0.9 ≈ near 1.0".**
- **v1.0.0 criterion** (set 2026-05-09): *"v1.0.0 will be when we can make any shortcut with any of the existing actions, with clear docs on each action."* Comprehensive corpus action coverage + uniform per-action docs. Many 0.X minors away.
- **v0.1.0 tagged 2026-05-09** at `d1ad7d4` — initial milestone (3 real targets, FU-9, factory methods, Var[T]).
- **The v1.0 tag and repo-public flip are the user's call.** Do not do them autonomously.

## Source confidence ladder (apply to every claim in a docstring)

```
corpus  >  jellycore (parameter_keys)  >  Shortcuts.app UI  >  inference
```

Always label the rung in the docstring. "*Confirmed by corpus at samples/decoded/X.xml:N*", "*jellycore-listed; corpus silent*", "*UI-inferred, pending corpus sample*". Mixing rungs without disclosure rots the discipline elsewhere.

## Wire-format conventions (CRITICAL)

These come from real bugs surfaced this build-out. Follow them on every new action.

1. **`jellycore_facts.json` is `{actions: [...288], structural_identifiers: [...]}`.**
   Always query with the array-select form:
   ```sh
   jq '.actions[] | select(.identifier == "is.workflow.actions.X")' data/jellycore_facts.json
   ```
   `jq '.["is.workflow.actions.X"]'` returns null silently — do not use it.

2. **Jellycore's lowercase keys often alias WF-prefixed wire keys.**
   Pattern proved by `voice` (jellycore) → `WFSpeakTextVoice` (corpus). Same for `noResultBehavior` → `WFNoOutputSurfaceBehavior`, `language` → `WFSpeakTextLanguage`. **Corpus is ground truth for wire spelling.** When corpus is silent on a jellycore-listed lowercase key, infer the WF-prefix by analogy to corpus-confirmed siblings — and label the inference.

3. **Apple's wire keys are inconsistent across sibling actions.** Map family proves it: `gettraveltime: WFDestination`, `getdistance: WFGetDistanceDestination`, `searchmaps: WFInput`, `getdirections: WFDestination`. **Never assume cross-action consistency. Corpus per action.** Wrong-key guesses produce silently malformed shortcuts.

4. **Envelope shape is determined by slot semantics, not value type.** `dnd.set` proves it: same UUID, `Time` slot uses `WFTextTokenString`, `Event` slot uses `WFTextTokenAttachment`. Use `coerce_text_field` for `WFTextTokenString` slots (text with interpolation), `coerce_value` for bare `WFTextTokenAttachment` (single variable ref).

5. **Field minimalism over speculation.** Model only corpus-confirmed parameters. If jellycore lists a key but no corpus sample exercises it, ship it with a "*pending corpus sample*" disclaimer. Don't invent style enums or unit Literals from the UI alone — they decay into wrong wire keys.

## Class naming

- Avoid Python builtin / project-internal collisions. `BuildList` (not `List` — shadows builtin), `StopAndOutput` (not `Output` — collides with `schema.values.Output`), `RandomNumber` (not `number.random`).
- Bare nouns where unambiguous: `Math`, `Statistics`, `GetDistance`. Not `MathAction`, not `GetDate` cleanups for cosmetic suffix consistency.

## Branch + dispatch pattern

The repo uses **autonomous batches** of action-coverage work:

1. Each new action lives on its own `v15/model-<thing>` branch off `main`.
2. Sub-agents dispatched with `isolation: "worktree"` so they work in `~/personal/shortcut-lib/.claude/worktrees/agent-<id>/`.
3. After each agent commits + reports, dispatch a sonnet review sub-agent. Review writes to `docs/architecture-review/v15-reviews/<branch-name>.md`.
4. Main-thread applies inline fixes if the review flags real issues; the worktree commits stay on the branch.
5. `docs/architecture-review/v15-reviews/_SUMMARY.md` is the master index — every branch + verdict + merge-order constraint.
6. **No autonomous merges.** Branches accumulate until the user merges.

**Bundle related actions** (e.g. `Number` + `RandomNumber`, `dnd.set` + `setvolume`) in a single branch when they're semantically tight — saves a review cycle.

**Budget:** sub-agent dispatch costs add up. If the budget hits, slow down and do main-thread reviews instead of more dispatches. Doc-only fixes are safe in main thread.

**Worktree gotcha:** if an agent claims pytest can't import a new module, verify yourself before believing it. The shared `.venv`/editable install handles new files in worktrees fine in practice.

## Where state lives

- `docs/roadmap.md` — phases, decisions log, current state. Update on milestone-level changes.
- `docs/handoff.md` — open follow-ups (FU-N entries) with status flips.
- `docs/architecture-review/v15-reviews/_SUMMARY.md` — every v15 branch, latest head, verdict, merge order.
- `docs/architecture-review/v15-reviews/<branch>.md` — per-branch review.
- `docs/architecture-review/v15-deep-review/` — the 3 opus deep reviews from the V1 seam.
- `docs/wire-format-quirks.md` (on `v15/wire-format-quirks-doc`) — central catalogue. Promote new findings (dual-envelope, map-family inconsistency, etc.) here.
- `data/observed_envelope_types.json` — wire-format-shape oracle (CI artefact).
- `data/jellycore_facts.json` — Apple action catalogue (288 entries; GPL-3.0 attribution).

## What NOT to do

- Don't merge v15/* branches into main without user approval.
- Don't tag a v1.0.0 / v0.X.0 release without user approval.
- The repo is public; push and merge only when the user asks (the v1.0 tag and any release remain the user's call).
- Don't add LLM clients as dependencies — the lib is what LLMs *call into*, not what calls LLMs.
- Don't use `RawAction` as a substitute for typed modelling on Apple-known actions; it's a fallback only.
- Don't replace `coerce_text_field` with hand-rolled `WFTextTokenString` envelope construction — the helper exists for a reason (FU-7 envelope sweep).
- Don't `--no-verify` a hook failure; fix the underlying issue.

## Estimating work in this repo

**Read `.claude/rules/velocity-and-estimation.md` before quoting any time estimate.** This project runs as fan-out of parallel sub-agents in isolated worktrees; default-quoted estimates from single-developer intuition have been 5–20× too long. Routine sessions produce ~40 commits and ~20 modelled actions; quote in those units, not hours.

## Universal rules from `~/.claude/CLAUDE.md`

Google-style docstrings; type-annotate public functions; `pathlib.Path` over `os.path`; `raise ... from exc`; structured logging via `logger_config.setup_logger()`; max 500 lines per file; max 6 args / 10 branches / 40 statements per function. No emojis unless asked.
