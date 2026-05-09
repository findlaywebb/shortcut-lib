<!--
Generated against:
  main @ 422c520405c55fb4aedee1af58f2fc71c14ccf3f
  data/observed_envelope_types.json @ 2026-05-09T08:09:34.980297+00:00

To regenerate: re-run the inventory walk in the schema-gaps brief
(see docs/architecture-review/v15-deep-review/B-schema-infrastructure.md).
After significant V1.5 merges, the modelled-vs-unmodelled counts in
Section 5 may drift; refresh by running list_actions() on the new
state and updating the table.
-->

# Schema Gaps Inventory

_Generated 2026-05-09 against 21 decoded corpus samples (20 public +
1 gitignored private). Use this document to select the next modelling batch._

---

## 1. Snapshot

The decoded corpus covers 687 total action invocations across 21 sample
shortcuts (20 public + 1 gitignored private), producing 393 distinct
`WFWorkflowActionIdentifier` values.
Of these, 29 are currently registered in the schema library: 24 leaf
actions (fully typed, `@register`-decorated) and 5 control-flow constructs
(`If`, `RepeatEach`, `RepeatCount`, `ChooseFromMenu`, `RunWorkflow`).
That leaves **364 unmodelled identifiers** -- 93% of the distinct surface.
Coverage of corpus invocations by count is higher: the 29 modelled
identifiers account for roughly 38% of total action appearances, because
the most-repeated control-flow and variable-management actions are already
modelled. The 364 unmodelled identifiers split into 6 with 4+ appearances
(Tier 1), 84 with 2-3 appearances (Tier 2), and 274 singletons (Tier 3).

---

## 2. Tier-1 Unmodelled -- High Frequency (4+ Corpus Appearances)

- **`is.workflow.actions.file.rename`** -- "Rename File"
  - Corpus count: 7
  - Samples: `rename_files.xml:6`, `rename_files.xml:10`,
    `dictionary.xml:189`, `dictionary.xml:292`, and 3 more
  - Observed param keys: `WFFile`, `WFNewFilename` (2 keys, plus `UUID`)
  - Jellycore params: `WFFile`, `WFNewFilename` -- confirmed match
  - Apparent complexity: **low** (2 distinct WF params)
  - Closed-set string fields: none observed
  - Dict-typed params: none
  - Recommendation: **model next batch**. Minimal surface, Jellycore
    confirms the key names. Wire-R1 already notes that `WFFile` arrives as
    `WFTextTokenAttachment` and `WFNewFilename` as `WFTextTokenString` --
    both envelope types are already handled in the lib. Lowest-friction
    action in the entire unmodelled set.

- **`is.workflow.actions.addnewreminder`** -- "Add New Reminder"
  - Corpus count: 5
  - Samples: `add_expiry_reminder.xml:3`, `batch_add_reminders.xml:2`,
    `batch_add_reminders.xml:12`, `dictionary.xml:418`
  - Observed param keys: `WFCalendarItemTitle`, `WFCalendarItemNotes`,
    `WFAlertCondition`, `WFAlertEnabled`, `WFAlertCustomTime`,
    `WFAlertLocationRadius`, `WFCalendarItemCalendar`, `WFParentTask`,
    `WFURL` (9 wire keys observed in corpus; `WFFlag` is not present in the
    21-sample corpus — 4 of the 9 are dict-envelope slots, 5 are bare
    scalars/strings)
  - Jellycore params: not in catalogue
  - Apparent complexity: **medium** (9 distinct observed keys; mix of plain
    strings, `WFQuantityFieldValue` for `WFAlertLocationRadius`, bare
    booleans for `WFAlertEnabled`)
  - Closed-set string fields: `WFAlertCondition` (time/location), likely
    Literal candidates
  - Dict-typed params: none observed directly, but `WFAlertLocationRadius`
    uses `{Magnitude, Unit}` shape
  - Recommendation: **model next batch**. High user utility (reminder
    creation is a core automation pattern). All params are Optional bar the
    title; the quantity shape is already modelled via `Quantity` value type.

- **`is.workflow.actions.text.combine`** -- "Combine Text"
  - Corpus count: 5
  - Samples: `daily_standup.xml:5`, `daily_standup.xml:12`,
    `daily_standup.xml:19`, `dictionary.xml:40`, and 1 more
  - Observed param keys: `text`, `WFTextSeparator` (2 wire keys observed in
    corpus; `Show-text` is a boolean scalar — not a dict-envelope slot and
    not seen in the 21-sample corpus)
  - Jellycore params: `text`, `combine`, `WFTextCustomSeparator`
  - Apparent complexity: **low** (2 observed keys; `WFTextSeparator` is a
    closed set: "New Lines", "Spaces", "Custom", etc.)
  - Closed-set string fields: `WFTextSeparator` -- strong Literal candidate
  - Dict-typed params: none
  - Recommendation: **model next batch**. Low complexity; `WFTextSeparator`
    is a Literal enum, `WFTextCustomSeparator` is an optional text token.
    Shares structural pattern with `TextSplit` (already modelled).

- **`is.workflow.actions.sendmessage`** -- "Send Message" (iMessage)
  - Corpus count: 5
  - Samples: `markup_and_send.xml:1`, `dictionary.xml:173`,
    `dictionary.xml:328`, `dictionary.xml:331`, and 1 more
  - Observed param keys: `WFSendMessageContent`, `WFSendMessageActionRecipients`
    (2 wire keys observed in corpus; `IntentAppDefinition` is not seen in
    `sendmessage` samples — it appears in `timer.start` and was a cross-action
    confusion in an earlier draft)
  - Jellycore params: not in catalogue
  - Apparent complexity: **medium** (2 observed keys; `WFSendMessageActionRecipients`
    is a contact-reference type -- similar to `com.apple.mobilephone.call`)
  - Closed-set string fields: none
  - Dict-typed params: `IntentAppDefinition` (app routing object -- V2
    territory for full typing, but can be accepted as `dict[str, Any]` for V1)
  - Recommendation: **model with dict passthrough for recipients**. Contact
    references are a new content class; accept as `list[dict[str, Any]]` for
    V1 and tag for V2 typing.

- **`is.workflow.actions.previewdocument`** -- "Quick Look"
  - Corpus count: 4
  - Samples: `combine_screenshots_and_share.xml:5`, `daily_standup.xml:36`,
    `dictionary.xml:56`, `turn_text_into_audio.xml:1`
  - Observed param keys: `WFInput` (1 key)
  - Jellycore params: `WFInput`
  - Apparent complexity: **low** (1 key; plain input passthrough)
  - Closed-set string fields: none
  - Dict-typed params: none
  - Recommendation: **model next batch**. Trivially low surface; useful for
    debugging and preview shortcuts.

- **`is.workflow.actions.filter.calendarevents`** -- "Filter Calendar Events"
  - Corpus count: 4
  - Samples: `daily_standup.xml:22`, `daily_standup.xml:23`,
    `running_late.xml:0`, `dictionary.xml:248`
  - Observed param keys: `WFContentItemFilter`, `WFContentItemInputParameter`
    (2 keys)
  - Jellycore params: none listed
  - Apparent complexity: **high** (`WFContentItemFilter` is a structured
    filter predicate dict -- same pattern as `filter.files`, `filter.photos`)
  - Closed-set string fields: none at top level
  - Dict-typed params: `WFContentItemFilter` is a nested predicate
    structure (filter operator, field name, value, comparison). This is the
    V2 filter-predicate shape.
  - Recommendation: **defer full typing to V2**. Accept as
    `dict[str, Any]` passthrough for now; the filter-predicate type is a
    reusable infrastructure piece that should be modelled once across all
    `filter.*` actions simultaneously.

---

## 3. Tier-2 Unmodelled -- Medium Frequency (2-3 Corpus Appearances)

Entries below show: identifier, friendly name, count, observed param keys,
and a brief note. Jellycore-unknown identifiers are marked `(jc:-)`.

- `is.workflow.actions.getlastscreenshot` -- "Get Last Screenshots" -- 3
  -- params: `WFGetLatestPhotoCount` -- low complexity, clean counter
- `is.workflow.actions.share` -- "Share" -- 3 -- params: `WFInput` --
  trivially low; single-param passthrough
- `is.workflow.actions.getitemfromlist` -- "Get Item From List" -- 3 --
  params: `WFInput`, `WFItemIndex`, `WFItemSpecifier` -- low; closed-set
  `WFItemSpecifier` (First/Last/Random/Custom index)
- `is.workflow.actions.round` -- "Round Number" -- 3 --
  params: `WFInput`, `WFRoundMode` -- low; `WFRoundMode` is a Literal
- `is.workflow.actions.alert` -- "Show Alert" -- 2 --
  params: `WFAlertActionMessage`, `WFAlertActionTitle` (2 observed wire keys;
  `WFAlertActionCancelButtonShown` is not present in the corpus) -- low;
  familiar text pattern
- `is.workflow.actions.showresult` -- "Show Result" -- 2 --
  params: `Text` -- trivially low; single text slot
- `is.workflow.actions.list` -- "List" -- 2 --
  params: `WFItems` -- low; creates a list value
- `is.workflow.actions.choosefromlist` -- "Choose From List" -- 2 --
  params: `WFChooseFromListActionPrompt`, `WFChooseFromListActionSelectMultiple`,
  `WFInput` -- low; 3 params, boolean flag
- `is.workflow.actions.date` -- "Date" -- 2 -- params: none (UUID only) --
  trivially low; returns current date
- `is.workflow.actions.count` -- "Count" -- 2 --
  params: `Input`, `WFCountType` -- low; `WFCountType` is a Literal
  (Items/Characters/Words/Sentences/Lines)
- `is.workflow.actions.number` -- "Number" -- 2 -- params: none -- trivial;
  wraps a number literal
- `is.workflow.actions.number.random` -- "Random Number" -- 2 --
  params: none observed (defaults) -- low
- `is.workflow.actions.math` -- "Math" -- 2 --
  params: `WFInput` -- low; arithmetic on input
- `is.workflow.actions.format.number` -- "Format Number" -- 2 --
  params: `WFNumber` -- low
- `is.workflow.actions.calculateexpression` -- "Calculate Expression" -- 2
  -- params: `Input` -- low
- `is.workflow.actions.statistics` -- "Calculate Statistic" -- 2 --
  params: `Input` -- low
- `is.workflow.actions.adjustdate` -- "Adjust Date" -- 2 --
  params: `WFAdjustOperation`, `WFDuration`, `WFDate`, `WFAdjustOffsetPicker`
  -- medium (4 params; `WFDuration` uses `TimeOffset` shape)
- `is.workflow.actions.detect.number` -- "Get Numbers From Input" -- 2 --
  params: `WFInput` -- low
- `is.workflow.actions.makespokenaudiofromtext` -- "Make Spoken Audio From
  Text" -- 2 -- params: `WFInput`, `WFSpeakTextVoice` -- low-medium;
  `WFSpeakTextVoice` may be a string picker
- `is.workflow.actions.output` -- "Output" -- 2 --
  params: `WFOutput`, `WFResponse`, `WFNoOutputSurfaceBehavior` -- medium;
  used for returning values from shortcuts, `WFResponse` may be a
  structured type
- `is.workflow.actions.dnd.set` -- "Set Focus / Do Not Disturb" -- 2 --
  params: `AssertionType`, `Enabled`, `Event`, `FocusModes`, `Time` --
  medium (5 keys; `FocusModes` is a list); surface integration (Focus API)
- `is.workflow.actions.timer.start` -- "Start Timer" -- 2 --
  params: `WFDuration`, `IntentAppDefinition` -- low-medium; uses
  `TimeOffset`; `IntentAppDefinition` is app-routing dict passthrough
- `is.workflow.actions.image.combine` -- "Combine Images" -- 2 --
  params: `WFInput`, `WFImageCombineMode`, `WFImageCombineSpacing` --
  low-medium; two Literal candidates
- `is.workflow.actions.getlastphoto` -- "Get Last Photo" -- 2 --
  params: none (UUID/CustomOutputName) -- trivial
- `is.workflow.actions.selectphoto` -- "Select Photo" -- 2 --
  params: none -- trivial
- `is.workflow.actions.savetocameraroll` -- "Save to Camera Roll" -- 2 --
  params: `WFInput` -- low
- `is.workflow.actions.filter.photos` -- "Filter Photos" -- 2 --
  params: `WFContentItemInputParameter` -- medium (filter predicate; V2)
- `is.workflow.actions.filter.windows` -- "Find Windows" -- 2 --
  params: `WFContentItemLimitEnabled`, `WFContentItemLimitNumber` -- low;
  no filter predicate
- `is.workflow.actions.resizewindow` -- "Resize Window" -- 2 --
  params: `WFConfiguration`, `WFWindow` -- medium; window reference is
  a new content class (`WFWindow`)
- `is.workflow.actions.avairyeditphoto` -- "Markup" -- 2 --
  params: `WFDocument` -- low; single doc input
- `is.workflow.actions.sendemail` -- "Send Email" -- 2 (jc:-) --
  params: `WFSendEmailActionInputAttachments`,
  `WFSendEmailActionShowComposeSheet`, `WFSendEmailActionSubject` --
  medium; recipients not in observed keys (uses `ShowComposeSheet` mode)
- `is.workflow.actions.readinglist` -- "Add to Reading List" -- 2 --
  params: `WFURL` -- low; single URL
- `is.workflow.actions.openurl` -- "Open URL" -- 2 --
  params: `WFInput` -- low
- `is.workflow.actions.showwebpage` -- "Show Webpage" -- 2 --
  params: `WFURL` -- low
- `is.workflow.actions.getmyworkflows` -- "Get Shortcuts" -- 2 --
  params: none -- trivial
- `is.workflow.actions.gettraveltime` -- "Get Travel Time" (jc:-) -- 3 --
  params: `WFDestination` -- low-medium; location reference
- `is.workflow.actions.getwebpagecontents` -- "Get Web Page Contents" -- 2
  -- params: `WFInput` -- low
- `is.workflow.actions.runjavascriptonwebpage` -- "Run JS on Webpage" -- 2
  -- params: `WFInput` -- low
- `is.workflow.actions.filter.files` -- "Filter Files" -- 2 --
  params: `WFContentItemInputParameter`, `WFContentItemSortOrder`,
  `WFContentItemSortProperty` -- medium (sort Literals; filter in V2)
- `is.workflow.actions.getupcomingevents` -- "Get Upcoming Events" (jc:-) -- 2
  -- params: `WFDateSpecifier`, `WFGetUpcomingItemCalendar`,
  `WFGetUpcomingItemCount` -- medium; 3 params including date specifier
- `is.workflow.actions.file` -- "File" -- 2 -- params: none -- trivial
- `is.workflow.actions.file.select` -- "Select File" -- 2 -- params: none -- trivial
- `is.workflow.actions.file.move` -- "Move File" -- 2 --
  params: `WFFile` -- low
- `is.workflow.actions.documentpicker.save` -- "Save File" -- 2 --
  params: `WFInput` -- low
- `is.workflow.actions.file.delete` -- "Delete File" -- 2 --
  params: `WFInput` -- low
- `is.workflow.actions.file.createfolder` -- "Create Folder" -- 2 --
  params: none -- trivial
- `is.workflow.actions.file.getfoldercontents` -- "Get Contents of Folder"
  -- 2 -- params: `WFFolder` -- low
- `is.workflow.actions.documentpicker.open` -- "Get File" -- 2 --
  params: `WFFile` -- low
- `is.workflow.actions.searchweb` -- "Search Web" -- 2 --
  params: `WFInputText` -- low
- `is.workflow.actions.setvolume` -- "Set Volume" -- 2 --
  params: none observed -- trivial
- `is.workflow.actions.filter.articles` -- "Filter Articles" -- 2 --
  params: `WFContentItemInputParameter` -- medium (filter predicate; V2)
- `is.workflow.actions.getarticle` -- "Get Article" -- 2 --
  params: `WFWebPage` -- low

  _The remaining ~40 Tier-2 entries (music/podcast/maps/contacts/calendar
  actions) are catalogued in `data/observed_envelope_types.json` and
  follow the same low-to-medium pattern. Most have 1-3 params; several
  involve `WFContentItemFilter` (defer to V2)._

---

## 4. Tier-3 Unmodelled -- Singletons (1 Corpus Appearance)

274 identifiers appear exactly once. Listing all is not useful; key clusters:

| Cluster | Count | Representative identifiers |
|---------|-------|---------------------------|
| System / device settings | 12 | `wifi.set`, `bluetooth.set`, `setbrightness`, `appearance`, `lockscreen` |
| Image / video manipulation | 17 | `image.crop`, `image.resize`, `image.flip`, `makegif`, `trimvideo` |
| Calendar (single) | 8 | `addnewevent`, `removeevents`, `properties.calendarevents`, `addnewcalendar` |
| Contacts | 10 | `addnewcontact`, `filter.contacts`, `properties.contacts`, `selectcontacts` |
| Notes.app | 16 | `appendnote`, `filter.notes`, `shownote`, plus 13 `com.apple.Notes.*` intents |
| iWork suite | 9 | `com.apple.iWork.{Keynote,Numbers,Pages}.*` |
| Microsoft 365 | 8 | `com.microsoft.{Excel,Word,Powerpoint,teams2,Outlook}.*` |
| Clock / alarms | 8 | `com.apple.clock.*`, `com.apple.mobiletimer-framework.*` |
| Music / podcasts | 6 | `pausemusic`, `seek`, `skipback`, `playpodcast`, `encodemedia` |
| Scripting | 4 | `runapplescript`, `runjavascriptforautomation`, `runshellscript`, `runsshscript` |
| Third-party read-later | 3 | `pocket.add`, `instapaper.add`, `pinboard.add` |
| Misc uncategorised | 131 | Everything else -- mostly `com.apple.*` app intents |

Full per-identifier data is in the analysis output; sample file for each is
`dictionary.xml` (the corpus catch-all) unless noted.

---

## 5. Currently Modelled (Cross-Reference)

### Leaf actions (24)

- `com.apple.ShortcutsActions.TranscribeAudioAction` -- TranscribeAudio
- `com.apple.WritingTools.WritingToolsAppIntentsExtension.AdjustToneIntent` -- AdjustTone
- `com.apple.WritingTools.WritingToolsAppIntentsExtension.FormatListIntent` -- FormatList
- `com.apple.WritingTools.WritingToolsAppIntentsExtension.RewriteTextIntent` -- RewriteText
- `com.apple.WritingTools.WritingToolsAppIntentsExtension.SummarizeTextIntent` -- SummarizeText
- `is.workflow.actions.appendvariable` -- AppendVariable
- `is.workflow.actions.ask` -- AskForInput
- `is.workflow.actions.askllm` -- UseModel
- `is.workflow.actions.base64encode` -- Base64Encode
- `is.workflow.actions.comment` -- Comment
- `is.workflow.actions.dictatetext` -- DictateText
- `is.workflow.actions.dictionary` -- Dictionary
- `is.workflow.actions.downloadurl` -- DownloadURL
- `is.workflow.actions.exit` -- ExitShortcut
- `is.workflow.actions.format.date` -- FormatDate
- `is.workflow.actions.getclipboard` -- GetClipboard
- `is.workflow.actions.gettext` -- GetText
- `is.workflow.actions.getvariable` -- GetVariable
- `is.workflow.actions.notification` -- ShowNotification
- `is.workflow.actions.recordaudio` -- RecordAudio
- `is.workflow.actions.setclipboard` -- SetClipboard
- `is.workflow.actions.setvariable` -- SetVariable
- `is.workflow.actions.text.replace` -- TextReplace
- `is.workflow.actions.text.split` -- TextSplit

### Control-flow constructs (5)

- `is.workflow.actions.choosefrommenu` -- ChooseFromMenu
- `is.workflow.actions.conditional` -- If
- `is.workflow.actions.repeat.count` -- RepeatCount
- `is.workflow.actions.repeat.each` -- RepeatEach
- `is.workflow.actions.runworkflow` -- RunWorkflow

---

## 6. Recommended Next Batches

Batch order reflects: combined user utility, parameter simplicity, and
structural similarity to already-modelled actions.

### Batch A (Priority 1) -- Trivial text + file outputs

_Pattern: 1-3 params, no new envelope types, all existing value types apply._

- `is.workflow.actions.file.rename` (2 params, `Text` envelope; R1-grounded)
- `is.workflow.actions.previewdocument` (1 param)
- `is.workflow.actions.text.combine` (3 params; mirrors `TextSplit`)
- `is.workflow.actions.showresult` (1 param, `Text` slot)

Rationale: All four can be authored, tested, and wire-validated in a single
sub-agent pass. `file.rename` and `text.combine` are high-frequency and
have real-sample wire evidence. `previewdocument` and `showresult` are
near-zero cost. Together they bring 6 more corpus appearances into typed
coverage.

### Batch B (Priority 2) -- List and selection actions

_Pattern: 2-4 params, Literal closed-set fields, no new content classes._

- `is.workflow.actions.list` (creates list value; `WFItems`)
- `is.workflow.actions.choosefromlist` (3 params; boolean flag + Literal)
- `is.workflow.actions.getitemfromlist` (3 params; `WFItemSpecifier` Literal)
- `is.workflow.actions.count` (2 params; `WFCountType` Literal)

Rationale: These four form a cohesive input/output pipeline that LLM
authors use together. `WFCountType` and `WFItemSpecifier` are obvious
Literal enums. No new infrastructure needed.

### Batch C (Priority 3) -- Numeric and date utilities

_Pattern: 2-4 params, some Literal fields, one existing TimeOffset shape._

- `is.workflow.actions.number` (trivial literal wrapper)
- `is.workflow.actions.math` (1 param)
- `is.workflow.actions.round` (2 params; `WFRoundMode` Literal)
- `is.workflow.actions.adjustdate` (4 params; `WFDuration` uses `TimeOffset`)
- `is.workflow.actions.date` (zero params; returns current date)

Rationale: Core numeric/date primitives that unlock more complex automation
patterns. `adjustdate` is the heaviest of the five (`TimeOffset` shape) but
the type is already in the library.

### Batch D (Priority 4) -- Reminder creation

_Medium complexity; high user utility; requires Quantity shape for location
alert radius._

- `is.workflow.actions.addnewreminder` (9 observed params; all Optional
  except title)

Rationale: Standalone batch because it has the richest parameter set in
Tier-1 and warrants careful wire-format validation against
`add_expiry_reminder.xml` and `batch_add_reminders.xml`. The `Quantity`
value type is already modelled.

### Batch E (Priority 5) -- Alert and send actions (with dict passthrough)

_Medium complexity; contact/app-routing references handled as `dict[str, Any]`
for V1._

- `is.workflow.actions.alert` (2 observed params; straightforward)
- `is.workflow.actions.sendmessage` (2 observed params; `WFSendMessageActionRecipients`
  as `list[dict[str, Any]]` passthrough)

Rationale: `alert` is simple. `sendmessage` requires a contact-reference
type that is not yet in the library; accept as opaque dict for V1, mark V2
in a `# TODO` comment.

### Batch F (Priority 6) -- File system actions (bulk)

_Low complexity; 1-2 params each; forms a natural grouping._

- `is.workflow.actions.file.move`, `.file.delete`, `.file.select`,
  `.file`, `.file.createfolder`, `.file.getfoldercontents`,
  `.documentpicker.save`, `.documentpicker.open`

Rationale: Eight actions but all trivially thin. Can be done in a single
pass once the file-reference envelope type is confirmed from `rename_files.xml`.

### Batch G (Priority 7) -- Web and URL actions

_Low complexity; 1-2 params each._

- `is.workflow.actions.openurl`, `.showwebpage`, `.readinglist`,
  `.searchweb`, `.getwebpagecontents`, `.getarticle`

### Deferred to V2 -- Filter predicate actions

_All `filter.*` actions (`filter.calendarevents`, `filter.files`,
`filter.photos`, `filter.reminders`, `filter.articles`, `filter.windows`,
`filter.contacts`, `filter.music`) share the `WFContentItemFilter`
predicate dict. Model the predicate infrastructure once, then add all
filter actions in a single V2 batch._

---

## 7. Out-of-Scope Flags

- **`filter.*` predicate typing** -- `WFContentItemFilter` is a structured
  nested dict (field, operator, value). Eight Tier-2/3 actions share it.
  Modelling piecemeal would produce eight redundant passthrough fields.
  Track as a V2 infrastructure item; a single `FilterPredicate` type will
  unlock all eight actions simultaneously.

- **Contact and window references** -- `WFSendMessageActionRecipients`,
  `WFWindow`, `WFCallContact` are first-class content-class types with no
  existing parallel in the library. Accepted as `dict[str, Any]` for V1;
  need dedicated types in V2.

- **Third-party app intents** (`com.microsoft.*`, `com.apple.iBooksX.*`,
  `com.apple.freeform.*`) -- Apple exposes these via App Intents; their
  parameter shapes are not documented in Jellycore and vary by installed
  app version. Out of scope for corpus-driven modelling; accept as
  `RawAction` passthrough indefinitely.
