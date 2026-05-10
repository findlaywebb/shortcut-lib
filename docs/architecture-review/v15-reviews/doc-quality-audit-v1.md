# Review: v15/doc-quality-audit-v1

**Branch head:** 31239d8
**Reviewer:** claude-sonnet-4-6
**Date:** 2026-05-10
**Verdict:** YELLOW — merge with inline fixes

---

## 1. Verdict

The docstring pass is a genuine quality improvement: every V1 leaf action
now has a structured, coherent docstring where most had none. No logic was
changed. All tests pass. prek is green. The branch earns a YELLOW rather
than GREEN because three sample citations on `DownloadURL` carry incorrect
descriptions (wrong HTTP method / wrong header presence for each cited
invocation), and one RecordAudio citation describes a key that the cited
sample does not actually contain. These are documentation bugs, not
correctness bugs, but they set a bad standard for the citation discipline
this branch is meant to establish. The fixes are one-liners; merge after
fixing them inline.

---

## 2. Behaviour-preservation evidence

| Check | Result |
|---|---|
| `prek run --all-files` | All 8 hooks passed |
| Tests (branch worktree) | 330 passed, 6 skipped, 3 xfailed |
| Tests (main) | 336 passed, 2 skipped, 3 xfailed |
| Logic diff | Zero — only docstrings, comments, and a roadmap update changed |

The six-test delta is a worktree environment artefact: the worktree at
`.claude/worktrees/agent-ab5993a7e27b1459d/` does not symlink
`samples/decoded/private/` (gitignored), so the four
`test_wire_format_equivalence` tests that parameterise over
`voice_note_to_github.xml` skip rather than run, and the two lift/round-trip
tests for that sample are not collected at all. This is expected and does not
indicate a regression.

Diff stat covers 22 action source files, the roadmap, and the batch summary.
No test files were touched. No non-docstring lines in action files changed.

---

## 3. Source-attribution audit (jellycore claims)

Only two jellycore claims were added in the diff:

**Claim 1 — `AskForInput` quirks section:** "Jellycore names the field
`type`; the real plist key is `WFInputType`."

Verified: `jellycore_facts.json` entry for `is.workflow.actions.ask` lists
`parameter_keys: ["WFAskActionPrompt", "type", "WFAskActionDefaultAnswer",
...]`. The key `type` is present; `WFInputType` is confirmed in decoded
samples. Claim is accurate.

**Claim 2 — `RecordAudio` quirks section:** "Jellycore lists additional
parameters (`quality`, `end`, `WFRecordingTimeInterval`) that do not appear
in any decoded corpus sample."

Verified: `jellycore_facts.json` entry for `is.workflow.actions.recordaudio`
lists `parameter_keys: ["quality", "start", "end", "WFRecordingTimeInterval"]`.
The docstring omits `start` from the listed unverified trio, which is fair
because `start` is the implemented field (`WFRecordingStart`). However,
`start` (the jellycore camelCase alias) maps to a different wire key than
the implementation uses — this is a minor accuracy gap but not a
confabulation.

**`UseModel` and `DictateText`:** Neither docstring contains any jellycore
attribution. `is.workflow.actions.askllm` is not present in
`jellycore_facts.json` at all. The UseModel docstring is clean on this
front.

No false jellycore confabulations found. The math-branch pattern (citing
jellycore for a non-existent entry) did not recur.

---

## 4. Doc-quality assessment of spot-checked actions

### UseModel (`use_model.py`)

Strong. The five model options are listed correctly with their exact
wire-format strings, sourced from `intelly.xml:63` (confirmed: the sample
does contain `WFLLMModel: "Apple Intelligence"` and a `WFTextTokenString`-
wrapped `WFLLMPrompt`). The WFTextTokenString envelope requirement is
stated. The `__post_init__` validation path and the `_params` null-guard
are both documented in Args. The "Returns" section is present and matches
`default_output_name = "Model Response"`. No jellycore claims.

The docstring correctly avoids claiming jellycore sourcing, which is right:
`askllm` is absent from `jellycore_facts.json`.

### DownloadURL (`download_url.py`)

Structurally good but the four sample citations are all mis-described.
The `get_contents_of_url.xml` sample contains four `downloadurl`
invocations, but none match the descriptions given:

| Cited line | Docstring claim | Actual content |
|---|---|---|
| :11 | "plain GET" | GET with `ShowHeaders=True` and headers dict |
| :59 | "GET with headers" | PUT with no body, no headers |
| :92 | "POST with JSON body" | PATCH with no body, no headers |
| :125 | "POST with JSON body and custom headers" | POST with no body, no headers |

The WFTextTokenString quirk for `WFURL` is correctly documented. The
`body_type="Form"` guard is documented in the Args and the Note section.
The module-level docstring correctly attributes JSON-body confirmation to
`voice_note_to_github.xml` (a private sample that does contain
`WFHTTPMethod: PUT` + `WFJSONValues`). The per-field logic is sound.

**Action required:** Correct the four line-level descriptions before merge.

### AskForInput (`ask.py`)

Excellent. The per-type default-answer key table is accurate: `"Text"` and
`"URL"` → `WFAskActionDefaultAnswer`, `"Number"` →
`WFAskActionDefaultAnswerNumber`, `"Date and Time"` →
`WFAskActionDefaultAnswerDateAndTime` (verified: `add_expiry_reminder.xml:52`
contains this key). `"Date"` and `"Time"` alone are honestly flagged
"inferred by analogy ... not been verified". The six factory methods match
the table precisely. The `WFAskActionImmediateDictation` quirk is noted,
sourced to the correct sample line (`add_expiry_reminder.xml:11` — the key
is at line 16, but the action starts at 11). The "Returns" section is
present.

### DictateText (`dictate_text.py`)

Correct but thin on epistemics. The `stop_listening` values (`"After
Pause"`, `"After Short Pause"`, `"On Tap"`) are described as "Known values
observed in Apple's UI" — the honesty hedge is there, but the brief's
criterion was "UI-observed, not corpus-confirmed". The sample
(`dictate_to_clipboard.xml:11`) contains no `WFDictateTextStopListening`
key and no `WFSpeechLanguage` key — the sample's params dict is empty.

One additional gap: jellycore lists `language` and `endTrigger` for this
action (camelCase aliases). The code emits `WFSpeechLanguage` and
`WFDictateTextStopListening` — wire keys that are not in any decoded
sample. There is no comment noting this discrepancy.

These are mild issues; the docstring is still a large improvement over
nothing.

---

## 5. Sample-citation accuracy

**Accurate citations:**

- `AskForInput`: `add_expiry_reminder.xml:11` (correct) and
  `add_expiry_reminder.xml:47` (correct, `WFAskActionDefaultAnswerDateAndTime`
  at line 52, params block starts at 47).
- `TextSplit`: `batch_add_reminders.xml:190` correctly identified as
  "New Lines default (no separator key emitted)". `dictionary.xml:794` is
  correctly located but described as "explicit separator value" — the actual
  sample at that line has no separator key either (both invocations use the
  default). This is a minor mis-description.
- `UseModel`: `intelly.xml:63` — confirmed, `askllm` action starts at line 63.
- `RecordAudio`: `dictionary.xml:1531` — action is at that line, but the
  params dict is empty (UUID only). The docstring says
  `WFRecordingStart: Immediately (default mode)`. The intent (demonstrating
  the default encoding) is fine, but the description implies the key is
  present when it isn't. "Empty params (device default)" would be more accurate.
- `DictateText`: `dictate_to_clipboard.xml:11` — correct; params dict is
  empty, which matches "no locale or stop_listening keys emitted".

**Inaccurate descriptions (not fabricated lines — the line numbers are right,
but the summaries are wrong):**

- `DownloadURL`: all four citations (see §4 above).

---

## 6. The 5 surfaced quirks

**1. `AskForInput.WFAskActionImmediateDictation` not exposed**

Categorised: **(a) handoff fodder.** Correctly documented in the Quirks
section with a `RawAction` escape hatch and a corpus citation. The
documentation placement is right; there is no missing implementation work
the author failed to do.

**2. `TextSplit` wire-key mismatch (`input` → plist `text`)**

Categorised: **(a) handoff fodder.** Surfaced and documented in the Quirks
section ("The Python field is named `input` ... but the plist key is
`text`"). The code already handles this correctly in `_params`; the doc
catch is doing its job.

**3. `DownloadURL.body_type="Form"` raises `SchemaError` unconditionally**

Categorised: **(b) actionable now** — with the recommendation below.

**4. `RecordAudio` jellycore params unverified**

Categorised: **(c) needs a sample.** The Quirks section names the
unverified keys and defers to `RawAction`. Nothing else can be done without
a decoded sample that uses them.

**5. `DictateText.stop_listening` values UI-observed, not corpus-confirmed**

Categorised: **(b) mildly actionable.** The current wording ("Known values
observed in Apple's UI") is half-honest but should be one phrase stronger:
"UI-observed only — not present in any decoded corpus sample." A one-line
edit before merge is reasonable.

---

## 7. The `body_type="Form"` question

**Current behaviour:** raises `SchemaError` at `_params()` time (i.e. on
`.build()` / encode, not on construction). An LLM authoring a shortcut can
construct `DownloadURL(body_type="Form", body={...})` without error, then
hit the wall when building.

**Recommendation:** Move the guard to `__post_init__`. The "Form" type is
unimplemented and the error is intentional — raising at construction time
is strictly better than at build time because it surfaces the problem before
the author has assembled a larger shortcut around this action. The message is
already good ("use `RawAction` if you need it now"); just move the check.

This is a two-line change and worth doing before merge since the branch is
already about doc quality — an early-guard is part of the same "errors are
training signal" philosophy.

---

## 8. Issues

**Issue 1 (merge-blocker):** `DownloadURL` sample citations are all
mis-described. Fix the four descriptions to match actual sample content:

```
samples/decoded/get_contents_of_url.xml:11 — GET with ShowHeaders and headers dict.
samples/decoded/get_contents_of_url.xml:59 — PUT with WFTextTokenString URL, no body.
samples/decoded/get_contents_of_url.xml:92 — PATCH with WFTextTokenString URL, no body.
samples/decoded/get_contents_of_url.xml:125 — POST with WFTextTokenString URL, no body.
```

**Issue 2 (pre-merge nice-to-have):** `RecordAudio` citation text: change
"WFRecordingStart: Immediately (default mode)" to "empty params — device
default (no WFRecordingStart key)".

**Issue 3 (pre-merge nice-to-have):** `TextSplit` dictionary.xml:794 —
change "explicit separator value" to "action-chained input, default New
Lines separator (no separator key emitted)".

**Issue 4 (pre-merge nice-to-have):** `DictateText` stop_listening — add
"(not confirmed in any decoded sample)" after the list of observed values.

**Issue 5 (architectural, merge-gated recommendation):** Move
`body_type="Form"` guard from `_params()` to `__post_init__` in
`DownloadURL`.

---

## 9. Merge recommendation

**Merge AFTER fixing Issues 1 and 5 inline.** Issues 2–4 are desirable but
not blocking. This branch sets the citation discipline standard for all
subsequent action-coverage branches — incorrect sample descriptions
undermine that goal.

Once the two inline fixes land, this is a GREEN doc-only branch with no
logic risk. It should merge **early in the tier order** — before any action-
coverage branches — so the docstring patterns it establishes are available as
a reference when future action branches write their own docstrings.

Suggested position in the merge sequence: after `v15/wire-format-quirks-doc`
(foundational tier, no deps) and before any batch-2+ action coverage branch.
