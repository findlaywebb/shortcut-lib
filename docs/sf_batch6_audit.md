# SF-batch6 audit — text-token-string wrapping (skipped)

_Decision date: 2026-05-08. Audited corpus: every `samples/decoded/*.xml`
including the private subfolder, run via a per-slot bare-vs-wrapped count._

## Why this batch existed

The deep review's correctness reviewer flagged plain-string parameters as
a Blocker:

> Every decoded sample shows `WFTextActionText` as
> `{Value: {string: ..., attachmentsByRange: {}}, WFSerializationType:
> "WFTextTokenString"}` (see `samples/decoded/daily_standup.xml`). Same
> applies to `SetVariable.input`, `SetClipboard.input`,
> `TextReplace.input/find/replace`, `ShowNotification.title/body`,
> `AppendVariable.input`, `Base64Encode.input`, `DownloadURL.url`, etc.

Proposed fix: introduce `coerce_text_param(x)`; apply uniformly to
text-typed slots.

## Why we audited before applying it

Two prior signals contradicted the reviewer's certainty:

1. The lift round-trip of `voice_note_to_github` works with bare strings
   in the `WFTextActionText` slot — meaning Apple's import path *does*
   tolerate bare strings, at least for that slot.
2. The reviewer's example file (`daily_standup.xml`) is a single sample;
   "every decoded sample shows the envelope" is a strong claim that
   should be verifiable across the rest of the corpus.

## Audit results (per text-typed slot, across all samples)

| Slot                                | Wrapped | Bare | Verdict                |
|-------------------------------------|--------:|-----:|------------------------|
| `WFTextActionText` (GetText)        | 12      | 5    | Mixed                  |
| `WFNotificationActionTitle`         | 0       | 2    | Apple emits bare       |
| `WFNotificationActionBody`          | 3       | 0    | All 3 are templated    |
| `WFCommentActionText`               | 0       | 3    | Apple emits bare       |
| `WFReplaceTextFind`                 | 1       | 6    | Predominantly bare     |
| `WFReplaceTextReplace`              | 1       | 5    | Predominantly bare     |
| `WFAskActionPrompt`                 | 1       | 12   | Apple emits bare       |
| `WFAskActionDefaultAnswer*`         | 2       | 0    | Wrapped (handled in B3+B4)|
| `WFMenuPrompt`                      | 0       | 7    | Apple emits bare       |
| `WFInput` (data-flow, literal str)  | 21      | n/a  | Apple wraps literals   |

The reviewer's empirical claim doesn't survive the audit: most text-typed
slots Apple emits as bare strings, not as `WFTextTokenString` envelopes.
Uniform wrapping would cause our schema-emitted shortcuts to *diverge
more* from Apple's GUI emission, not less.

## What we did

Skipped the batch in full. The current schema's behaviour matches Apple's
dominant pattern for every slot we have evidence on:

- Action-specific text slots (title, comment, prompt, menu prompt) → bare
  string when caller passes a literal `str`.
- Templated slots → wrapped automatically via `Text.to_param()`.
- Default-answer of `AskForInput` → wrapped (already handled in the
  B3+B4 fix).

## Follow-ups

- **`WFInput` literal-string case (21/21 wrapped).** When a caller does
  `SetVariable(input="literal text")` we currently emit a bare string;
  Apple's GUI emits a `WFTextTokenString`. Worth revisiting if a real
  authoring problem surfaces — but the lift round-trip already proves
  Apple imports our bare-string form cleanly, so this is a "consistency
  with GUI emission" concern, not a correctness one.
- **End-to-end signing test for an authored shortcut.** The deep review
  noted that the only existing tests on the schema-author path are
  structural (`to_action_dict()` shape checks). An end-to-end test that
  signs an authored shortcut and re-decodes it would catch any future
  divergence at once. Worth doing whenever someone has time; not blocked
  on the SF-batch6 question.
