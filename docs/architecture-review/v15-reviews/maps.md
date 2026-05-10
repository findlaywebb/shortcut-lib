# Review: v15/model-maps

**Branch:** `v15/model-maps` (head `df7d9d7`)
**Actions:** `SearchMaps` (`is.workflow.actions.searchmaps`) + `GetDirections` (`is.workflow.actions.getdirections`)
**Date:** 2026-05-10

---

## 1. Verdict

**Approve.** Both implementations are correct, corpus-grounded, and complete.
Wire keys verified against XML. Jellycore-absent claims confirmed. The
map-family inconsistency table is included in both docstrings, which is
exactly the right place for it. No blocking issues.

---

## 2. Test results + prek

```
30 passed in 0.13s      (15 tests × 2 actions)
```

prek: all 8 hooks passed (whitespace, yaml, ruff lint, ruff format, uv-lock, ty).

Clean green across the board.

---

## 3. What landed

**`SearchMaps`** (`src/shortcut_lib/schema/actions/search_maps.py`, ~96 lines)

- Single field: `query: ParamValue = None`.
- Emits `WFInput` via `coerce_value`.
- Docstring includes full map-family key table, source-verification block,
  and explicit "not `WFSearchTerm`" callout.

**`GetDirections`** (`src/shortcut_lib/schema/actions/get_directions.py`, ~91 lines)

- Single field: `destination: ParamValue = None`.
- Emits `WFDestination` via `coerce_value`.
- Docstring includes same map-family key table, source-verification block,
  and explicit "not `WFGetDistanceDestination`" callout plus note about
  `WFTransportType` being plausible-but-unconfirmed.

15 tests each: construction, key presence, envelope type, `None` omission,
registry lookup, and two corpus round-trip assertions (both corpus indices).

---

## 4. Wire-key verification

### 4a. `SearchMaps.WFInput` — CONFIRMED

XML (dictionary.xml), first appearance (indices 104-105 block):

```xml
<key>WFWorkflowActionIdentifier</key>
<string>is.workflow.actions.searchmaps</string>
<key>WFWorkflowActionParameters</key>
<dict>
    <key>WFInput</key>
    <dict>
        <key>Value</key>
        <dict>
            <key>OutputName</key><string>Locations</string>
            <key>OutputUUID</key><string>4EA23489-...</string>
            <key>Type</key><string>ActionOutput</string>
        </dict>
        <key>WFSerializationType</key>
        <string>WFTextTokenAttachment</string>
    </dict>
</dict>
```

Second appearance (indices 321-322 block) is structurally identical, same key
`WFInput`, same `WFTextTokenAttachment` envelope. No `WFSearchTerm` anywhere.
The claim holds.

### 4b. `GetDirections.WFDestination` — CONFIRMED

XML (dictionary.xml), first appearance (indices 104 block):

```xml
<key>WFWorkflowActionIdentifier</key>
<string>is.workflow.actions.getdirections</string>
<key>WFWorkflowActionParameters</key>
<dict>
    <key>WFDestination</key>
    <dict>
        <key>Value</key>
        <dict>
            <key>OutputName</key><string>Locations</string>
            <key>OutputUUID</key><string>4EA23489-...</string>
            <key>Type</key><string>ActionOutput</string>
        </dict>
        <key>WFSerializationType</key>
        <string>WFTextTokenAttachment</string>
    </dict>
</dict>
```

Second appearance (index 321 block) identical structure. Key is `WFDestination`,
not `WFGetDistanceDestination`. Matches `gettraveltime`'s key; differs from
`getdistance`. All three claims correct.

### 4c. Map-family wire-key inconsistency table (canonical)

| Action | Destination key | Corpus evidence | Branch |
|---|---|---|---|
| `searchmaps` | `WFInput` | x2 | this branch |
| `getdirections` | `WFDestination` | x2 | this branch |
| `gettraveltime` | `WFDestination` | x3 | `v15/model-gettraveltime` |
| `getdistance` | `WFGetDistanceDestination` | x2 | `v15/model-getdistance` |

Apple uses three different key names for conceptually the same "destination
input" across four sibling actions. This is the strongest example to date of
why the project's position — "never guess key names; corpus only" — is
justified. Wrong-key guesses would produce syntactically valid but silently
broken plist structures with no runtime error in Shortcuts.app.

---

## 5. Source-attribution audit (jellycore-absent claims)

Both actions claim jellycore carries no data for their identifiers.

```
jq '.actions[] | select(.identifier == "is.workflow.actions.searchmaps")' jellycore_facts.json
# → (no output)

jq '.actions[] | select(.identifier == "is.workflow.actions.getdirections")' jellycore_facts.json
# → (no output)
```

Both return empty. Jellycore-absent claims are accurate. The docstrings note
this clearly and attribute all key-name evidence to the corpus alone. This is
the correct epistemic posture — no borrowed authority from a source that
doesn't cover these actions.

---

## 6. Cross-references in docstrings

Both docstrings include:

- A full four-row map-family key comparison table.
- Explicit sibling callouts: `searchmaps` references `getdirections` and
  `GetDistance`; `getdirections` references `gettraveltime` and `getdistance`.
- The "not `WFSearchTerm`" / "not `WFGetDistanceDestination`" negative callouts
  that warn against the most likely wrong-key mistakes.

Cross-reference coverage is thorough. A reader arriving at either class via IDE
lookup gets the full family context without hunting other files.

---

## 7. Doc quality

### `SearchMaps` — 9/10

Strengths: the "Parameter key — WFInput" section is decisive and well-placed.
The table is readable. The negative callout ("not `WFSearchTerm`") is exactly
where it needs to be. Source-verification block follows established project
conventions. `Args` section is accurate and covers the `None`-omission
behaviour.

Minor: the `WFTextTokenAttachment` vs `WFTextTokenString` distinction is
explained well inline but the in-code comment restates it redundantly. Not a
problem, but the comment is a duplicate of the docstring.

### `GetDirections` — 9/10

Strengths: same pattern as `SearchMaps`, executed consistently. The
`WFTransportType` note under "Fields not in the corpus" is the right epistemic
move — acknowledges the plausible omission without inventing unverified keys.
Sibling comparison to `gettraveltime` is direct and unambiguous.

Minor: same slight in-code comment redundancy as `SearchMaps`. No functional
issue.

Both classes score above the doc-quality bar set by the existing v15 series.

---

## 8. Issues

No blocking issues. One observation:

**Observation (non-blocking):** The `WFTransportType` note in `GetDirections`
says the key "is plausible but unconfirmed" for `getdirections` because
`gettraveltime` supports it. This is accurate. However, if a future branch adds
`WFTransportType` to `gettraveltime`, the reviewer should return here and verify
whether `getdirections` shares it. A `# TODO:` comment in the source would make
this easier to find — but given the project's current stage and the preference
for clean diffs, omitting it is defensible. Not filing as an issue.

---

## 9. Merge recommendation + wire-format-quirks note

**Merge.** All claims verified. Tests green. Prek clean. Doc quality high.

### Wire-format-quirks doc note

The four-action key inconsistency table (section 4c) should be promoted to
`docs/wire-format-quirks.md` (the `v15/wire-format-quirks-doc` branch). This is
the clearest concrete example in the codebase of Apple's naming inconsistency
causing a non-obvious, silently-wrong outcome — it belongs in the reference doc
alongside the `WFTextTokenString` vs `WFTextTokenAttachment` distinction.

Suggested entry heading: **"Map-family destination keys are not consistent"**,
table from section 4c, followed by: *"Use corpus evidence to establish each
action's key independently. Never infer a key from a sibling action."*
