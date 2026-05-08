# Apple Shortcuts file format — what we know

Notes accumulated while building the decoder. Anything stated here without
caveat has been verified against at least one decoded sample.

## Envelope

A `.shortcut` file is three layers nested:

```
AEA1 (Apple Encrypted Archive, profile 0 — sign-only)
  └─ AA (Apple Archive, single-file)
       └─ Shortcut.wflow (binary plist, the WFWorkflow* dict)
```

### AEA1 header

| Offset | Size | Meaning                                               |
|--------|------|-------------------------------------------------------|
| 0      | 4    | Magic `AEA1`                                          |
| 4      | 4    | Profile (`0` = sign-only, what Shortcuts uses)        |
| 8      | 4    | Auth-data size N (little-endian uint32)               |
| 12     | N    | Auth-data bplist (single key: `SigningCertificateChain`)|
| 12+N   | …    | Compressed signed AA payload                          |

The auth-data plist's `SigningCertificateChain` is `[leaf, intermediate, root]`,
each as DER bytes. The leaf is signed by `Apple System Integration CA 4`
issued under `Apple Certification Authority`, with a fresh per-shortcut
P-256 keypair (CN is a hex identifier). To decrypt, you need the leaf's
public key in X9.63 uncompressed form (65 bytes: `04 || X || Y`).

```sh
aea decrypt -i in.shortcut -o out.aa -sign-pub <hex:|base64:|raw key file>
aa  extract -i out.aa -d   out/
```

`out/Shortcut.wflow` is the binary plist — `plutil -convert xml1` to read.

### Why this works

Profile 0 is "sign only, no encryption". The AEA verifies the signature
against the public key you provide; since the leaf cert is bundled in the
archive itself, any signed shortcut is decodable without external state.
Apple's trust validation (CA chain checking) is a separate layer that runs
during *import* into the Shortcuts app, not during the AEA decrypt step.

## Plist structure (top level)

| Key                                 | Type        | Notes                                                       |
|-------------------------------------|-------------|-------------------------------------------------------------|
| `WFWorkflowActions`                 | array       | Ordered action list (see below)                             |
| `WFWorkflowMinimumClientVersion`    | int         | Gates compatibility                                         |
| `WFWorkflowMinimumClientVersionString` | string   | Same as above as string                                     |
| `WFWorkflowClientVersion`           | string      | e.g. `4033.0.4.3`                                           |
| `WFWorkflowIcon`                    | dict        | `{WFWorkflowIconGlyphNumber: int, WFWorkflowIconStartColor: int (RGBA-8)}` |
| `WFWorkflowTypes`                   | [string]    | Surfaces: `Watch`, `NCWidget`, `MenuBar`, `QuickActions`, `ActionExtension`, `Sleep`, `WatchKit` |
| `WFQuickActionSurfaces`             | [string]    | e.g. `Services` on macOS                                    |
| `WFWorkflowInputContentItemClasses` | [string]    | Accepted input types (see sebj reference)                   |
| `WFWorkflowOutputContentItemClasses`| [string]    | Output types                                                |
| `WFWorkflowImportQuestions`         | [dict]      | Prompts shown on import (see below)                         |
| `WFWorkflowHasOutputFallback`       | bool        |                                                             |
| `WFWorkflowHasShortcutInputVariables` | bool      |                                                             |

### WFWorkflowImportQuestions

Each question dict:

| Key            | Notes                                                    |
|----------------|----------------------------------------------------------|
| `ActionIndex`  | Index into `WFWorkflowActions` for the targeted action   |
| `Category`     | Usually `Parameter`                                      |
| `ParameterKey` | Key inside that action's `WFWorkflowActionParameters` to populate |
| `Text`         | The prompt shown to the user                             |
| `DefaultValue` | Pre-filled value (string/bool/dict)                      |

This is how gallery shortcuts ask "Which Focus mode?" on install.

### Icon colors (RGBA-8)

See [sebj's reference](https://github.com/sebj/iOS-Shortcuts-Reference) for
the named-colour palette. Stored as a single int, e.g. red = `4282601983`
= `0xFF4351FF`.

## Actions

Each `WFWorkflowActions[i]`:

```
{
  WFWorkflowActionIdentifier: "is.workflow.actions.<name>",
  WFWorkflowActionParameters: { … action-specific … }
}
```

Identifiers are reverse-DNS. First-party uses `is.workflow.actions.*`;
third-party app intents use `com.apple.<bundle>.<name>` or
`com.<vendor>.<bundle>.<name>`.

Most actions also have a `UUID` parameter when they produce an output
that downstream actions reference.

## Variable references

There are three serialisation flavours we've seen:

### 1. `WFTextTokenAttachment` — direct variable substitution

Used when a parameter accepts a single variable token:

```
{
  Value: {
    OutputName: "Rounded Number",
    OutputUUID: "5DFB8DC2-…",
    Type: "ActionOutput"
  },
  WFSerializationType: "WFTextTokenAttachment"
}
```

`Type` can also be:
- `Variable` — for named user variables (`{VariableName: "Token", Type: "Variable"}` in the inner dict — no `OutputUUID`).
- Magic types with no UUID: `CurrentDate`, `Clipboard`, `Ask`, `ExtensionInput`.

### 2. `WFTextTokenString` — string with embedded variables

For text fields that mix literals and variable substitutions:

```
{
  Value: {
    string: "Started a timer for ￼ minutes.",
    attachmentsByRange: {
      "{20, 1}": { OutputName, OutputUUID, Type: "ActionOutput" }
    }
  },
  WFSerializationType: "WFTextTokenString"
}
```

The `￼` (object replacement) character in `string` is the placeholder.
Keys in `attachmentsByRange` are NSRange syntax `"{offset, length}"` —
**UTF-16 code units**, not bytes or chars (matters for emoji/multi-byte text).

### 3. Wrapped `Variable` (for condition inputs)

Some parameters expect a Variable wrapper around the token:

```
{
  Type: "Variable",
  Variable: {
    Value: { OutputName, OutputUUID, Type: "ActionOutput" },
    WFSerializationType: "WFTextTokenAttachment"
  }
}
```

## Control flow

Branches are **flat-encoded** with paired open/close markers sharing a
`GroupingIdentifier` UUID. The body actions sit linearly between markers.

For `is.workflow.actions.conditional`:

| `WFControlFlowMode` | Meaning             |
|---------------------|---------------------|
| `0`                 | If — block start    |
| `1`                 | Else                |
| `2`                 | End if              |

Same flat+grouping pattern is used by `repeat`, `repeat.each`,
`choose-from-menu`, `dictionary`, etc.

`WFCondition` is encoded as an integer (e.g. `0` for "Equals") in current
iOS versions. Older shortcuts-js encoded it as the string `"Equals"`;
newer iOS rejects that — drift confirmed.

## Typed value containers

Several parameters use a `{Value, WFSerializationType}` envelope where the
serialization type names a value kind:

| `WFSerializationType`   | `Value` shape                                                |
|-------------------------|--------------------------------------------------------------|
| `WFTextTokenAttachment` | Single variable token (above)                                |
| `WFTextTokenString`     | Templated string (above)                                     |
| `WFQuantityFieldValue`  | `{Magnitude: number-or-token, Unit: "min"\|"hour"\|…}`       |
| `WFTimeOffsetValue`     | `{Operation: "Add"\|…, Unit: "Minute"\|…, Value: token}`     |

Worth modelling as a sealed `Value` union in the schema layer.

## Open questions

- Full enum for `WFCondition` integer values (we have `0`=Equals; need a
  mapped sample for `<`, `>`, `Contains`, `BeginsWith`, etc.).
- How `repeat` and `choose-from-menu` markers differ in their open/close
  parameter shapes.
- Encoding of `Dictionary` action items (key+value pairs as templated text?).
- Third-party action parameter conventions (e.g. `IntentAppDefinition` is
  used in `is.workflow.actions.timer.start` to scope to Clock — when else?).
- Magic variable identifiers beyond the obvious set (e.g. `RepeatItem`
  inside repeat blocks).
