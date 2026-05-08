# Prior reverse-engineering work

Three public projects were evaluated as wrapper candidates; this lib was
written when none of them fit. Plus smaller community write-ups that
informed the file-format work. Apple has never published a shortcut
format spec.

The schema source code is hand-written. References to upstream projects
in the source are labelled hints, validated against decoded samples.

## [Open-Jellycore](https://github.com/OpenJelly/Open-Jellycore) — OpenJelly, GPL-3.0

The Jellycuts compiler. The most comprehensive public action catalogue:
288 first-party actions with typed parameter schemas, 77 typed enums,
plus a Compiler.swift that emits 5 control-flow primitives
(`is.workflow.actions.conditional`, `choosefrommenu`, `repeat.each`,
`repeat.count`, `comment`) as language constructs rather than lookup-table
entries. Includes `lowestCompatibleHost` per action — neither shortcuts-js
nor sebj's reference has equivalent OS-min metadata.

Not viable as a wrapper: Swift compiler-frontend shape doesn't port to
Python ergonomics, and the iOS-26-era actions (`UseModel`, Writing
Tools) post-date its last update. Used as the bootstrapping fact source
for `docs/coverage_dictionary.md` and as one of several hint sources
during schema authoring.

`scripts/extract_jellycore.py` projects an Open-Jellycore checkout to
`data/jellycore_facts.json`: identifier, Apple display name, parameter
key names, OS-min, plus Apple-namespace structural identifiers from
Compiler.swift. The dataset is a development-time artefact;
`pyproject.toml` excludes `data/` from the wheel. See `NOTICE` for
attribution.

Dictionary.shortcut coverage check: covers ~62% of identifiers (231 via
lookup table + 7 via language constructs); the rest are post-2023
first-party additions and third-party app-intent identifiers.

External catalogue field names don't always match Apple's WF* keys 1:1
(e.g. an `AskForInputParameter` field labelled `type` is `WFInputType`
on the wire). Treat extracted parameter names as hints; validate against
decoded shortcuts.

## [shortcuts-js](https://github.com/joshfarrant/shortcuts-js) — Josh Farrant, MIT

TypeScript library, ~129 hand-written action modules, ~2018 era (iOS 12).
Most useful single source for action parameter shapes. Schema has drifted
since (e.g. `WFCondition` shifted from string `"Equals"` to integer `0`),
so treat as a hint rather than truth — verify against a current decoded
sample before trusting.

Wrapper-candidate verdict: TypeScript-first, schema is iOS-12-era and
drifted from current Shortcuts; the per-action factory pattern doesn't
map cleanly to Python dataclasses. Patterns borrowed conceptually rather
than mechanically:

- Per-action module with a small typed factory function returning the
  WFWorkflow action dict (mirrored as Python dataclasses).
- A "use this action's output as a variable downstream" pattern (the
  Python lib auto-mints a UUID per `Action` and exposes `.output()`).
- Variable type taxonomy: `Ask`, `Clipboard`, `CurrentDate`, `ExtensionInput`,
  named `Variable` — same names used in this lib's `values.py`.

## [iOS-Shortcuts-Reference](https://github.com/sebj/iOS-Shortcuts-Reference) — sebj, archived 2022

Pre-iOS-15. The action coverage is thin (one example) but the
workflow-level reference data is the best single source for the
top-level metadata enums:

- `WFWorkflowImportQuestions` schema
- `WFWorkflowInputContentItemClasses` enum (17 values)
- `WFWorkflowTypes` enum
- Icon colour palette (15 named colours, RGBA-8 ints)
- URL schemes (`shortcuts://import-shortcut/?url=…`, etc.)

Wrapper-candidate verdict: not a library, just a reference data
repository — never a wrapper candidate, only an enum source. Useful
for top-level metadata enums when modelling those becomes priority.

## [shortcuts-toolkit](https://github.com/drewburchfield/shortcuts-toolkit) — Drew Burchfield, MIT

JS + web/CLI builder UI. Lighter on action coverage than shortcuts-js;
nothing structural we'd miss. Useful only as a sanity check for the
top-tier identifiers.

## [zachary7829's file format notes](https://zachary7829.github.io/blog/shortcuts/fileformat.html)

Best community write-up of the bplist + signing layers. Pre-iOS-15 only.
Useful for historical context (iCloud unsigned-export workaround, jailbroken
import re-enable) but the AEA pipeline we use here is more direct.

## [apple-shortcuts-jgstew](https://github.com/jgstew/apple-shortcuts-jgstew)

Just example shortcuts + a binary→XML plist conversion shell script.
Nothing structural to take.
