# Wire-format quirks — LLM author reference

**Scope:** parameter conventions *inside* actions. File-envelope structure
(AEA1 → AA → bplist) is covered in `docs/format.md` and not repeated here.

**Oracle:** `data/observed_envelope_types.json` — 687 action observations across
21 decoded samples. When in doubt, grep the decoded samples; this doc
describes patterns, not an exhaustive enum.

---

## 1. Bare parameter keys (no `WF` prefix)

The `WF`-prefixed CamelCase convention (`WFInput`, `WFDate`, `WFURL`) is
widespread but not universal. A significant minority of Apple actions use
bare, lower-case, or otherwise unprefixed parameter keys. Assuming every
key starts with `WF` will produce silently broken output.

### First-party `is.workflow.actions.*` bare keys confirmed in corpus

| Action identifier | Bare key | Notes |
|---|---|---|
| `is.workflow.actions.count` | `Input` | Title-Case, no prefix. `coerce_value` path. Confirmed: `combine_screenshots_and_share.xml:2`, `dictionary.xml:4` |
| `is.workflow.actions.showresult` | `Text` | Title-Case, no prefix. `coerce_text_field` path. Confirmed: `start_pomodoro.xml:10`, `dictionary.xml` |
| `is.workflow.actions.text.split` | `text` | Lowercase. List input slot. Confirmed: `batch_add_reminders.xml:9`, `sort_lines.xml` |
| `is.workflow.actions.text.split` | `separator` | Lowercase. Separator-choice slot. Confirmed: `batch_add_reminders.xml:9` |
| `is.workflow.actions.text.combine` | `text` | Lowercase. List input slot. Confirmed: `dictionary.xml:40`, `sort_lines.xml:2` |
| `is.workflow.actions.calculateexpression` | `Input` | Title-Case. Confirmed: `dictionary.xml:25`, `dictionary.xml:238` |
| `is.workflow.actions.converttimezone` | `Date` | Title-Case. Confirmed: `dictionary.xml:34` |
| `is.workflow.actions.correctspelling` | `text` | Lowercase. Confirmed: `dictionary.xml:46` |
| `is.workflow.actions.dnd.set` | `Event`, `Time` | Title-Case. Confirmed: `start_pomodoro.xml:9` |
| `is.workflow.actions.runjavascriptforautomation` | `Input` | Title-Case. Oracle entry |
| `is.workflow.actions.showdefinition` | `Word` | Title-Case. Oracle entry |
| `is.workflow.actions.statistics` | `Input` | Title-Case. Oracle entry |
| `is.workflow.actions.text.changecase` | `text` | Lowercase. Oracle entry |
| `is.workflow.actions.text.match` | `text` | Lowercase. Oracle entry |
| `is.workflow.actions.text.match.getgroup` | `matches` | Lowercase. Oracle entry |
| `is.workflow.actions.url.expand` | `URL` | All-caps, no prefix. Oracle entry |
| `is.workflow.actions.deletephotos` | `photos` | Lowercase. Oracle entry |

Third-party app intent actions (identifiers under `com.apple.*`) also use
bare keys universally — `audioFile`, `target`, `board`, `entities`, etc.
This appears to be the Intents/AppIntents convention for those bundles.

### Why this pattern exists

Apple's `is.workflow.actions.text.*` family predates the `WF`-prefix
convention. The `count`, `showresult`, and `calculateexpression` actions
also carry non-prefixed primary input keys. There is no mechanical rule for
predicting which side a given action falls on — check the decoded samples.

### How the library handles bare keys

The library's `_params()` implementation in each action class emits the
correct key directly. There is no schema-wide transformation. When you
write a new action, use the corpus key verbatim — do not add a `WF` prefix
just because it looks familiar. The `coerce_value` and `coerce_text_field`
helpers in `src/shortcut_lib/schema/base.py` are agnostic to the key name;
what matters is choosing the right helper for the envelope type (see §4).

---

## 2. Title-Case-with-hyphen keys

A handful of parameter keys combine CamelCase words with a literal hyphen.
This is distinct from both `WFCamelCase` and bare-lowercase keys.

| Action identifier | Hyphenated key | Python field | Notes |
|---|---|---|---|
| `is.workflow.actions.text.split` | `Show-text` | `show_text` | Boolean UI toggle. V1.5 branch `v15/fu13-textsplit-showtext`. Confirmed: `sort_lines.xml:16`, `batch_add_reminders.xml:193` |
| `is.workflow.actions.text.combine` | `Show-text` | `show_text` | Same shape. V1.5 branch `v15/model-text-combine`. Confirmed: `sort_lines.xml:72` |
| `is.workflow.actions.downloadurl` | `ShowHeaders` | _(not a field)_ | UI flag; auto-emitted when headers are present. One word, no hyphen — listed here for contrast |

The `Show-text` key is the only confirmed hyphenated key in the corpus.
The boolean value (`True`/`False`) emits as a plain plist boolean, not
wrapped in any envelope. Apple appears to use the hyphenated form for
boolean UI-state toggles that control editor visibility without affecting
runtime behaviour.

---

## 3. Wire-key vs Python field name mismatches

The Python dataclass field name follows Python conventions (snake_case,
descriptive). The wire key follows Apple's convention (whatever that is for
the action). They are often different.

| Action class | Python field | Wire key | Envelope type |
|---|---|---|---|
| `FormatDate` | `input` | `WFDate` | `WFTextTokenString` |
| `FormatDate` | `date_style` | `WFDateFormatStyle` | bare string |
| `FormatDate` | `time_style` | `WFTimeFormatStyle` | bare string |
| `TextSplit` | `input` | `text` | `WFTextTokenAttachment` |
| `TextSplit` | `separator` | `separator` | bare string |
| `TextSplit` | `show_text` | `Show-text` | bare bool |
| `TextCombine` | `input` | `text` | `WFTextTokenAttachment` |
| `TextCombine` | `show_text` | `Show-text` | bare bool |
| `Count` | `input` | `Input` | `WFTextTokenAttachment` |
| `Count` | `count_type` | `WFCountType` | bare string |
| `ShowResult` | `text` | `Text` | `WFTextTokenString` |
| `GetItemFromList` | `input` | `WFInput` | `WFTextTokenAttachment` |
| `GetItemFromList` | `specifier` | `WFItemSpecifier` | bare string |
| `GetItemFromList` | `index` | `WFItemIndex` | coerced value |
| `AddNewReminder` | `title` | `WFCalendarItemTitle` | `WFTextTokenString` |
| `AddNewReminder` | `calendar` | `WFCalendarItemCalendar` | bare string |
| `AddNewReminder` | `notes` | `WFCalendarItemNotes` | bare string |
| `AddNewReminder` | `alert_enabled` | `WFAlertEnabled` | bare string |
| `AddNewReminder` | `alert_custom_time` | `WFAlertCustomTime` | `WFTextTokenString` |
| `AddNewReminder` | `url` | `WFURL` | bare string |
| `AddNewReminder` | `parent_task` | `WFParentTask` | `WFTextTokenAttachment` |
| `DownloadURL` | `url` | `WFURL` | `WFTextTokenString` |
| `DownloadURL` | `body_type` | `WFHTTPBodyType` | bare string |
| `DownloadURL` | `method` | `WFHTTPMethod` | bare string |

Source files: `src/shortcut_lib/schema/actions/` for all actions above.
V1.5-only rows are on their respective branches pending merge.

### Map family — same conceptual slot, four different wire keys

Apple uses different wire-key names for the destination/input slot
across the four map-family actions. Cross-action consistency cannot be
assumed; per-action corpus confirmation is mandatory.

| Action | Identifier | Destination wire key | Envelope |
|---|---|---|---|
| `GetTravelTime` | `is.workflow.actions.gettraveltime` | `WFDestination` | `WFTextTokenAttachment` |
| `GetDistance` | `is.workflow.actions.getdistance` | `WFGetDistanceDestination` | `WFTextTokenAttachment` |
| `SearchMaps` | `is.workflow.actions.searchmaps` | `WFInput` | `WFTextTokenAttachment` |
| `GetDirections` | `is.workflow.actions.getdirections` | `WFDestination` | `WFTextTokenAttachment` |

Cited from the per-branch reviews of `model-gettraveltime`, `model-getdistance`,
and `model-maps`. The same value type (a single variable reference) uses
the same envelope across all four — but the *wire key* differs by action.

---

## 4. Slot-envelope conventions

Every parameter slot that accepts a dynamic value (a variable reference,
a template, or a coerced Action output) uses one of the following
serialisation envelopes. The outer shape is always
`{Value: {…}, WFSerializationType: "<type>"}`.

### `WFTextTokenString` — templated string

Used when Apple's runtime reads the slot as a string that may contain
embedded variable references. Even single-variable references must be
wrapped in this envelope for these slots (a bare `WFTextTokenAttachment`
reads as empty/disconnected at runtime).

**Use `coerce_text_field(x)` from `base.py` for these slots.** It
rewraps a `WFTextTokenAttachment` envelope as a one-attachment
`WFTextTokenString` automatically.

Common slots in this category (confirmed via oracle):

| Action | Slot |
|---|---|
| `downloadurl` | `WFURL` |
| `addnewreminder` | `WFCalendarItemTitle`, `WFAlertCustomTime` |
| `ask` | `WFAskActionDefaultAnswer`, `WFAskActionPrompt` |
| `adjustdate` | `WFDate` |
| `format.date` | `WFDate` |
| `showresult` | `Text` |
| `notification` | _(title slots)_ |
| `askllm` | `WFLLMPrompt` |
| `conditional` | `WFConditionalActionString` (RHS string comparison) |

### `WFTextTokenAttachment` — single variable reference

Used when the slot accepts exactly one variable token (no mixed
literal/variable template). A plain `WFTextTokenAttachment` is correct
here — do **not** use `coerce_text_field`.

**Use `coerce_value(x)` for these slots.**

Common slots in this category (confirmed via oracle):

| Action | Slot |
|---|---|
| `setvariable` | `WFInput` |
| `base64encode` | `WFInput` |
| `repeat.each` | `WFInput` |
| `count` | `Input` |
| `text.split` | `text` |
| `text.combine` | `text` |
| `getitemfromlist` | `WFInput` |
| `addnewreminder` | `WFParentTask` |
| `downloadurl` | `WFRequestVariable` |
| `choosefromlist` | `WFInput` |
| `avairyeditphoto` | `WFDocument` |
| `recordaudio` | _(output)_ |

### `WFDictionaryFieldValue` — key-value dictionary

Used for dictionary-structured parameters (HTTP headers, JSON body). The
outer envelope wraps a `WFDictionaryFieldValueItems` array where each
entry has `WFItemType`, `WFKey`, and `WFValue` — each key and value is
itself a `WFTextTokenString` envelope. See `DownloadURL._encode_wf_dict`
in `src/shortcut_lib/schema/actions/download_url.py` for the reference
implementation.

| Action | Slot |
|---|---|
| `downloadurl` | `WFHTTPHeaders` |
| `downloadurl` | `WFJSONValues` |

### `WFContactFieldValue` — contact handle

Used for recipient fields. The `Value` inner dict contains a
`WFContactFieldValues` array whose entries hold contact-handle data
(CNDB record IDs, phone/email hashes) written by Shortcuts.app at
authoring time. The internal format is iOS-version-dependent; the library
accepts a pre-built wire dict passed as `ParamValue`.

| Action | Slot |
|---|---|
| `sendmessage` | `WFSendMessageActionRecipients` |

### `WFQuantityFieldValue` — magnitude with unit

For numeric inputs that carry a unit (duration, distance). The `Value`
inner dict contains `Magnitude` (number or token) and `Unit` (string).

| Action | Slot |
|---|---|
| `addnewreminder` | `WFAlertLocationRadius` |
| `adjustdate` | `WFDuration`, `WFAdjustOffsetPicker` |

### `If` operand — two-layer variable wrapper

The `If` action's `WFInput` slot uses a non-standard two-layer envelope:

```python
{"Type": "Variable", "Variable": <WFTextTokenAttachment envelope>}
```

This is different from a plain `WFTextTokenAttachment`. `RepeatEach` uses
a plain `WFTextTokenAttachment` for its `WFInput`. The distinction is
confirmed against corpus samples (see `_wrap_variable_input` in
`src/shortcut_lib/schema/control.py`).

### Envelope is determined by slot semantics, not by value type

`is.workflow.actions.dnd.set` (`SetDoNotDisturb`) is the cleanest known
demonstration: the *same UUID* — i.e. a reference to the same upstream
variable — is wrapped in *different envelopes* depending on which slot
it lands in within the same action.

In `samples/decoded/start_pomodoro.xml`, the same `Date` variable UUID
appears in two adjacent dnd.set invocations:

- `Time` slot → `WFTextTokenString` envelope (the slot is a templated
  string that may interpolate the variable).
- `Event` slot → bare `WFTextTokenAttachment` (the slot is a single
  variable reference, no template).

The library therefore selects the helper based on the slot, not the
value type:

| Slot semantics | Helper | Envelope produced |
|---|---|---|
| Text-with-interpolation (`WFTextTokenString`) | `coerce_text_field(x)` | one-attachment `WFTextTokenString` |
| Single-variable ref (`WFTextTokenAttachment`) | `coerce_value(x)` | bare `WFTextTokenAttachment` |

Cited from the per-branch review of `model-system-controls`.

---

## 5. Default-omission patterns

Apple omits parameter keys when the value equals the action's built-in
default. The library matches this behaviour: optional fields with defaults
typically emit nothing, not the default value. Do not emit the default
explicitly unless corpus evidence shows Apple does so for that action.

| Action | Parameter key | Default value | Library policy | Sample evidence |
|---|---|---|---|---|
| `text.split` | `separator` | `"New Lines"` | Always omit | `batch_add_reminders.xml:9` (5 samples) |
| `text.combine` | `WFTextSeparator` | `"New Lines"` | Omit | `dictionary.xml` (omits); `daily_standup.xml` writes it — fidelity loss on that sample |
| `getitemfromlist` | `WFItemSpecifier` | `"First Item"` | Omit | `dictionary.xml`, `tile_last_2_windows.xml` |
| `count` | `WFCountType` | `"Items"` | Always emit | `combine_screenshots_and_share.xml` writes it; `dictionary.xml` omits — we over-emit on the latter |
| `downloadurl` | `WFHTTPMethod` | `"GET"` | Omit for GET | All GET samples carry no `WFHTTPMethod` key |
| `alert` | `WFAlertActionMessage` | `""` | Omit when empty | Schema omits; Apple emits `""` in some samples — known divergence |

**Policy:** the library chooses minimal output when Apple allows it. Round-trip
fidelity is imperfect for verbose Apple emissions (e.g. `daily_standup.xml`'s
explicit `WFTextSeparator`). An `emit_defaults` flag is a V2 escape hatch.

### `WFItemIndex` co-emission quirk

`tile_last_2_windows.xml` contains a `getitemfromlist` invocation with
`WFItemSpecifier="Last Item"` **and** `WFItemIndex="2"` emitted together.
The library drops `WFItemIndex` on round-trip for `"Last Item"` — this is
a known fidelity loss for that specific sample. The pairing is uncommon;
the simpler schema is the right call at V1.5.

---

## 6. Action-specific quirks not yet generalised

### `RawAction.uuid` injection

`RawAction.to_action_dict` injects `self.uuid` into `raw_params` to
keep the emitted UUID in sync with the value `.output()` references.
When `self.uuid` is empty (lifted from a corpus action that carried no
`UUID` key, e.g. `start_pomodoro.xml:9` / `dnd.set`), the UUID key is
omitted, preserving that wire-format quirk. See
`src/shortcut_lib/schema/base.py`.

### `If` operand wrapping vs `RepeatEach`

`If` wraps its operand in a two-layer `{Type: "Variable", Variable: …}`
envelope. `RepeatEach` uses a plain `WFTextTokenAttachment`. Both use the
`WFInput` key. The distinction is enforced by separate helpers:
`_wrap_variable_input` (for `If`) and `coerce_value` (for `RepeatEach`).
Using the wrong wrapper produces a condition that silently never evaluates
on device.

### `IntentAppDefinition` omission

Several corpus samples (`dictionary.xml` — `AdjustTone`, `Use Model`,
`SendMessage`) contain an `IntentAppDefinition` key at authoring time.
The library intentionally omits this in every action's `_params()`. It is
written by Shortcuts.app at shortcut-authoring time and is not part of the
library's authoring surface.

### `AddNewReminder.alert_enabled` string encoding

The alert-enabled toggle is not a boolean; it is one of the strings
`"Alert"` or `"No Alert"`. `True`/`False` would produce a broken reminder.
The `WFAlertEnabled` key may also be absent entirely (default). Confirmed:
`set_weekend_chores.xml:3` ("Alert"), `batch_add_reminders.xml:12` ("No
Alert"), `batch_add_reminders.xml:2` (key absent). V1.5 branch
`v15/model-addnewreminder`.

### `DownloadURL.ShowHeaders` bare boolean

When HTTP headers are configured, the library emits `ShowHeaders: True`
alongside `WFHTTPHeaders`. This is a bare plist boolean (no envelope) and
controls the header-editor visibility in Shortcuts.app. It has no runtime
effect but is present in every real shortcut with headers; omitting it
causes the editor to render collapsed even when headers are set. Confirmed:
`get_contents_of_url.xml:0`, `private/voice_note_to_github.xml:22`.

---

## 7. The lib's discipline — corpus over Jellycore

When in doubt, the corpus wins. `data/jellycore_facts.json` has known stale
entries. Two confirmed examples:

- `is.workflow.actions.text.combine` — Jellycore lists `combine` as a
  parameter key. No corpus sample uses it. The corpus uses `WFTextSeparator`
  as the separator key and `text` as the input key. Trust the decoded
  samples.
- `is.workflow.actions.count` — Jellycore lists `type` as the count-type
  key. The real Apple plist key is `WFCountType`. Confirmed in
  `combine_screenshots_and_share.xml`.

Always grep the decoded samples in `samples/decoded/` before trusting a
Jellycore-sourced key name. The oracle at `data/observed_envelope_types.json`
records slot names and envelope types as observed in real `.shortcut` files —
it is the ground truth for envelope type selection, and the `bare_string_slots`
section records which slots Apple emits as plain strings rather than envelopes.
