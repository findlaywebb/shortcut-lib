# shortcut-lib

Decode (and eventually author) Apple Shortcuts files programmatically.

There is no first-party API for creating shortcuts from text. This library
goes the only available route: parse the `.shortcut` binary format directly,
build a typed schema for actions one shortcut at a time, and emit valid
files signed via the `shortcuts` CLI shipped with macOS.

## Status

- **Decode**: working. AEA1 → Apple Archive → bplist pipeline using the
  embedded signing public key, no external state needed.
- **Schema**: empty. Bootstrapped on demand from decoded samples.
- **Encode + DSL**: not started.

## Install

```sh
uv venv && uv pip install -e '.[dev]'
```

Requires macOS (uses the system `aea` and `aa` binaries).

## CLI

```sh
shortcut-decode path/to/foo.shortcut                   # XML plist to stdout
shortcut-decode path/to/foo.shortcut --format summary  # action breakdown
shortcut-decode path/to/foo.shortcut --format json -o foo.json
```

## Library

```python
from shortcut_lib import decode_file

decoded = decode_file("Start Pomodoro.shortcut")
print(decoded.signing_subject)      # leaf cert CN
for action in decoded.workflow["WFWorkflowActions"]:
    print(action["WFWorkflowActionIdentifier"])
```

## See also

- `docs/format.md` — what we know about the file format
- `docs/sources.md` — attributions to prior reverse-engineering work
