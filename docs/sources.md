# Prior reverse-engineering work

Attributions and notes on what we've drawn from each. None of these is
authoritative; Apple has never published a shortcut format spec.

## [Open-Jellycore](https://github.com/OpenJelly/Open-Jellycore) — OpenJelly, GPL-3.0

The Jellycuts compiler. Highest-fidelity public action database we've found:
**288 first-party actions** with hand-curated typed parameter schemas, **77
typed enums**, plus a Compiler.swift that emits 5 control-flow primitives
(`is.workflow.actions.conditional`, `choosefrommenu`, `repeat.each`,
`repeat.count`, `comment`) as language constructs rather than lookup-table
entries. Includes `lowestCompatibleHost` per action — neither shortcuts-js
nor sebj's reference has equivalent OS-min metadata.

**License-clean extraction**: GPL-3.0 source can't be vendored, but facts
about Apple's API (identifier strings, parameter key names, enum members,
OS-min) aren't copyrightable expression. `scripts/extract_jellycore.py`
reads the Swift sources, emits `data/jellycore_facts.json` with only the
factual fields, and deliberately omits Jellycore's description prose,
DSL function names, and presets (those *are* original expression).

Dictionary.shortcut coverage check: Jellycore covers ~62% of identifiers
(231 via lookup table + 7 via language constructs), missing ~50 first-party
identifiers that appear to be post-2023 additions or omissions
(`addnewreminder`, `appendvariable`, `getvariable`, `addnewevent`,
maps actions, etc.) and ~100 third-party app-intent identifiers. The
~150 gaps are the schema work we'd own.

**Caveat on parameter keys**: Jellycore's Swift fields don't always match
Apple's WF* keys 1:1 (e.g. `AskForInputParameter` declares `var type:
Jelly_WFInputType?` but Apple's plist uses `WFInputType`). Treat extracted
parameter names as hints; validate against decoded shortcuts before trusting.

## [shortcuts-js](https://github.com/joshfarrant/shortcuts-js) — Josh Farrant, MIT

TypeScript library, ~129 hand-written action modules, ~2018 era (iOS 12).
Most useful single source for action parameter shapes. Schema has drifted
since (e.g. `WFCondition` shifted from string `"Equals"` to integer `0`),
so treat as a hint rather than truth — verify against a current decoded
sample before trusting.

Patterns worth borrowing:
- Per-action TS module with a small typed factory function returning the
  WFWorkflow action dict.
- `withActionOutput` HOF that auto-mints an output UUID and lets the action
  be used as a variable reference downstream.
- Variable type taxonomy: `Ask`, `Clipboard`, `CurrentDate`, `ExtensionInput`,
  named `Variable`.

## [iOS-Shortcuts-Reference](https://github.com/sebj/iOS-Shortcuts-Reference) — sebj, archived 2022

Pre-iOS-15. The action coverage is thin (one example) but the
**workflow-level reference data is the best single source**:

- `WFWorkflowImportQuestions` schema
- `WFWorkflowInputContentItemClasses` enum (17 values)
- `WFWorkflowTypes` enum
- Icon colour palette (15 named colours, RGBA-8 ints)
- URL schemes (`shortcuts://import-shortcut/?url=…`, etc.)

Worth lifting these enums wholesale into our schema layer.

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
