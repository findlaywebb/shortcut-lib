# Review: v15/model-makespokenaudio

**Action**: `is.workflow.actions.makespokenaudiofromtext` ("Make Spoken Audio from Text")
**Files**: `src/shortcut_lib/schema/actions/make_spoken_audio.py` (+113 lines),
`tests/test_action_make_spoken_audio.py` (+248 lines)

---

## 1. Verdict

**Merge with inline disclaimer.** The two corpus-confirmed parameters
(`WFInput` as `WFTextTokenString`, `WFSpeakTextVoice` as bare string) are
implemented correctly. The three jellycore-only parameters expose a genuine
wire-key uncertainty for `language` specifically, and the doc already
disclaims this — but it does not document the strongest available inference
(that jellycore uses lowercase `voice` while the corpus proves the wire key
is `WFSpeakTextVoice`, giving a directly analogous precedent for
`language` → `WFSpeakTextLanguage`). That precedent should be recorded
inline. No blocking issues; the action is safe to use for the confirmed
parameters.

---

## 2. Test result + prek

```
19 passed in 0.78s
```

All prek hooks pass: trim whitespace, end-of-file, YAML, large-file check,
ruff lint, ruff format, uv-lock, ty — clean across the board.

---

## 3. What landed

Single `MakeSpokenAudio` dataclass with five fields: `text: ParamValue = ""`
(required in practice), `voice: str | None = None`, `language: str | None =
None`, `pitch: float | None = None`, `rate: float | None = None`. `_params()`
emits `WFInput` via `coerce_text_field`, `WFSpeakTextVoice` as a bare string,
`language` lowercase, `WFSpeakTextPitch`, and `WFSpeakTextRate` — with all
optional fields guarded by `None` (omit on default). `default_output_name =
"Spoken Audio"`. Registry and identifier present. The 19 tests cover:
identifier/registry, output name, plain-string and empty-string `WFInput`,
`NamedVar` and `ActionOutput` wrapping as `WFTextTokenString`, voice round-trip,
all three jellycore-only fields (emit and omit), and chaining.

---

## 4. The 3 inferred-key uncertainty — position

The three jellycore-only keys fall into two distinct risk categories.

**`WFSpeakTextPitch` and `WFSpeakTextRate` — position: accept as-is.**
Both carry the `WF`-prefix family consistent with `WFSpeakTextVoice`
(corpus-confirmed). Jellycore lists these with the same `WF`-prefix already;
no conflict. Risk is low.

**`language` — position: (c) document and flag, with a strong inference
toward (b) `WFSpeakTextLanguage`.**

The key evidence is that jellycore lists the `makespokenaudiofromtext` voice
parameter as `voice` (lowercase), but the corpus proves the wire key is
`WFSpeakTextVoice`. That is a direct, same-action precedent for jellycore
using an AppIntent-style name while the wire uses a `WF`-prefixed name.
The `speaktext` action (sibling TTS action, iOS 14) also lists `language`
lowercase in jellycore, alongside `WFSpeakTextRate` and `WFSpeakTextPitch`
with their `WF`-prefix — and no corpus sample exercises `language` for
`speaktext` either. The pattern across both TTS actions is: jellycore's
lowercase AppIntent name almost certainly aliases a `WF`-prefixed wire key.

The agent chose option (a) — trust jellycore literally, emit `"language"` —
which is defensible (safest assumption when uncertain) but is likely wrong
given the voice-key precedent. The correct stance is (c): keep the current
emit key as a best guess, but document that `WFSpeakTextLanguage` is the
strongly-inferred correct wire key and mark for corpus verification.

Suggested inline note in `_params()`:

```python
# Wire key uncertain: jellycore lists "language" (lowercase, AppIntent style)
# but the same action's voice parameter is listed as "voice" in jellycore
# yet emitted as "WFSpeakTextVoice" on the wire. By analogy,
# "WFSpeakTextLanguage" is the likely correct key. Emit lowercase until
# a corpus sample or live test confirms.
if self.language is not None:
    out["language"] = self.language  # TODO: verify WFSpeakTextLanguage
```

This does not need to block merge — `language` defaults to `None` and is
omitted in normal use — but the inference should be recorded before it
becomes load-bearing.

---

## 5. `WFInput` envelope verification

**Confirmed `WFTextTokenString`, not `WFTextTokenAttachment`.**

Both corpus appearances carry explicit `WFTextTokenString` envelopes:

- `turn_text_into_audio.xml`: `WFInput` wraps an `ExtensionInput` (share-sheet
  passthrough) in `WFTextTokenString`.
- `dictionary.xml`: `WFInput` wraps an `ActionOutput` reference (chained from
  Transcribe Audio) in `WFTextTokenString`.

`observed_envelope_types.json` corroborates: `.slots["is.workflow.actions.makespokenaudiofromtext"]["WFInput"]`
shows `WFTextTokenString` count 2, both samples listed. The agent's use of
`coerce_text_field` is correct. (Contrast with `makezip` / `makevideofromgif`,
which use `WFTextTokenAttachment` — this slot is genuinely different.)

The test suite exercises both reference types: `NamedVar` and `ActionOutput`
each produce a `WFTextTokenString` envelope with the `￼` sentinel, confirming
the `coerce_text_field` path is exercised.

---

## 6. Source-attribution audit

**Clean.** The docstring makes three distinct source claims and all are
verifiable:

| Claim | Verification |
|---|---|
| `WFInput` is `WFTextTokenString` | `observed_envelope_types.json .slots[identifier][WFInput]` — count 2, both samples |
| `WFSpeakTextVoice` is bare string | `observed_envelope_types.json .bare_string_slots[identifier]` = `["WFSpeakTextVoice"]` |
| `"com.apple.speech.synthesis.voice.Alex"` in `turn_text_into_audio.xml` | Confirmed at `<key>WFSpeakTextVoice</key> <string>com.apple.speech.synthesis.voice.Alex</string>` |
| `language`, `WFSpeakTextPitch`, `WFSpeakTextRate` from jellycore | `jq '.actions[] | select(.identifier == "is.workflow.actions.makespokenaudiofromtext")' data/jellycore_facts.json` — all three listed |

No naive `jq '.["id"]'` patterns. The jellycore query in the docstring
(`select(.identifier == ...)`) matches the correct array-select form. No false
corpus claims for the three unobserved parameters — they are correctly
disclaimed.

One minor note: the docstring cites `observed_envelope_types.json .bare_string_slots`
for the `WFSpeakTextVoice` claim but the actual observed key in `bare_string_slots`
is the correct one. This is fine.

---

## 7. Doc quality

**Score: 4/5.**

Strengths: docstring structure is clear, sources cited for every factual
claim, corpus sample paths named explicitly, all three inferred parameters
correctly disclaimed as "jellycore-listed but never observed in corpus", arg
descriptions carry Apple's expected value ranges for pitch and rate. The
output type ("Spoken Audio", `.m4a`) is documented.

Gap (one point deducted): the `language` key uncertainty is described as
simply "not observed in corpus" but the strongest available evidence — that
jellycore's lowercase `voice` maps to the WF-prefixed wire key `WFSpeakTextVoice`
in the same action — is not cited as a reason to suspect `language` should
be `WFSpeakTextLanguage`. A reader using this action to set the language
would not know the emit key is suspect. A single sentence would close this:
_"Note: by analogy with the `voice` → `WFSpeakTextVoice` precedent in this
action, the true wire key may be `WFSpeakTextLanguage`."_

---

## 8. Issues

**I1 (minor, non-blocking)** — `language` emit key likely wrong.
The agent emits `"language"` (lowercase) for the `language` parameter.
Jellycore lists `voice` (lowercase) for the same action; the corpus proves
the wire key is `WFSpeakTextVoice`. By direct analogy, `"language"` is
probably `"WFSpeakTextLanguage"` on the wire. The parameter defaults to `None`
and is omitted in normal use, so no shortcut currently breaks. Recommend:
add a TODO comment in `_params()` and note the inference in the docstring.
Resolve when a corpus sample or live test is available.

**I2 (cosmetic)** — `default_output_name = "Spoken Audio"` is not verified
against the corpus. Neither `turn_text_into_audio.xml` nor `dictionary.xml`
exercises an `OutputName` key for this action (the second sample chains into
a `previewdocument` but the `OutputName` in the corpus for the chained
`speaktext` output is not shown). The value is consistent with Apple's
naming conventions and the docstring states it ("the synthesised `.m4a`
audio file (`Spoken Audio`)"). Mark as "reasonable inference" rather than
corpus-confirmed if this ever matters for a round-trip fidelity test.

---

## 9. Merge recommendation

**Merge with inline disclaimer.**

Add the `language` TODO comment in `_params()` and one sentence to the
docstring noting the `voice` → `WFSpeakTextVoice` analogy as grounds for
suspecting `WFSpeakTextLanguage`. Neither change requires re-review; the
agent or the author can add them on merge. The action is safe in its current
state because `language` is omitted by default and the two corpus-confirmed
parameters are implemented correctly.
