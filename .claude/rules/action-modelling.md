# Rules for modelling a new Apple Shortcuts action

Loaded by sub-agents dispatched to add action schemas. Keep referenced; don't duplicate the full text in every prompt.

## The discipline

Every parameter key, every Literal value, every `default_output_name` in your docstring is a *claim*. Each claim must be labelled with its rung on the source-confidence ladder:

```
corpus  >  jellycore (parameter_keys)  >  Shortcuts.app UI  >  inference
```

If you cannot point at a sample line or a jellycore parameter_key entry, the claim is inference — say so explicitly.

## Workflow per action

1. **Corpus sweep.** `grep -l "is.workflow.actions.X" samples/decoded/*.xml`. Read every appearance. Note all wire keys, envelope shapes, value types.
2. **Jellycore lookup** — **always with the array-select form**:
   ```sh
   jq '.actions[] | select(.identifier == "is.workflow.actions.X")' data/jellycore_facts.json
   ```
   `jq '.["is.workflow.actions.X"]'` silently returns null because the file is `{actions: [...288]}`.
3. **Envelope oracle:** `data/observed_envelope_types.json` for the identifier.
4. **Pattern reference:** find the closest already-modelled sibling and read it before designing yours.

## Wire-key inference rules

- **Trust corpus over jellycore** for wire-key spelling. Jellycore's lowercase keys (e.g. `voice`, `language`, `operation`, `type`, `noResultBehavior`) are AppIntent-layer abstractions; the wire format usually uses `WF`-prefixed equivalents (e.g. `WFSpeakTextVoice`).
- **Corpus-silent + jellycore-lowercase**: emit the inferred `WF`-prefixed form when a corpus-confirmed sibling key follows the same pattern. Document the inference.
- **Don't assume cross-sibling consistency.** Apple ships `gettraveltime: WFDestination`, `getdistance: WFGetDistanceDestination`, `searchmaps: WFInput`, `getdirections: WFDestination`. Always corpus-confirm per action.

## Envelope rules

- Use `coerce_text_field(value)` when the slot is a `WFTextTokenString` (text with `attachmentsByRange` — i.e. inline-string-with-variable-interpolation).
- Use `coerce_value(value)` when the slot is a bare `WFTextTokenAttachment` (single variable ref) or a plain literal.
- The same value can take *different envelopes* depending on the slot. Slot semantics determine the envelope, not value type.

## Required-field guards

- A field is "required" only if **every corpus appearance populates it** AND a missing value would produce a runtime-inert action. Document the inference. If corpus shows even one bare appearance, allow `None` (matches Apple's default-omit behaviour).

## Class naming

- Bare nouns where they don't collide: `Math`, `Statistics`, `GetDistance`.
- Avoid Python builtin shadows: `BuildList` (not `List`), `RandomNumber` (not `number.random`).
- Avoid project-internal collisions: `StopAndOutput` (not `Output` — `schema.values.Output` exists).

## Docstring template

```
"""<Apple display name> — <one-line summary>.

Apple identifier: ``is.workflow.actions.X``.

**Wire format**

<concise prose; reference `samples/decoded/<file>.xml:<line>` for each
parameter that's corpus-confirmed; reference jellycore for parameter
existence claims; mark UI-only / inferred items explicitly>

**Quirks**

- <closed-set Literal options, default-omission rules,
  wire-key-vs-Python-name mismatches>

Args:
    <field>: <purpose, type, default behaviour, sample citation or
              "inferred" disclaimer>

Returns:
    <only present if default_output_name is set>

Raises:
    SchemaError: <when>

Example::

    <one minimal authoring example for non-trivial actions>
"""
```

## Branch + commit

- Branch `v15/model-<thing>` off `main`.
- One commit per agent task: `schema: model X — <Apple display name> action (v1.0 build-out)`.
- Don't forget to commit. The framework does not auto-commit. The agent's report should include the commit hash.

## Tests

- `tests/test_action_<thing>.py`.
- Cover: identifier, default output, registry lookup, every Literal value (parametrize), default-omission, every corpus appearance via wire-format equivalence, cross-field validation if `__post_init__` enforces any.
- Pin UUIDs from corpus when asserting wire-format equivalence so the tests document which sample they're checking.

## Reporting

When you finish, the report back must include:
- Branch name and commit hash
- Per-action: parameter list with provenance (corpus / jellycore / inferred) per field
- Test count delta
- Explicit confirmation: "*verified jellycore via array-select form*" if applicable
- Any quirks discovered worth promoting to `docs/wire-format-quirks.md`

## Anti-patterns to avoid

- "Jellycore says no entry" — verify with the array-select form first.
- Inventing style enums (currency / percent) from the UI when corpus + jellycore don't list them.
- Adding speculative fields with confident docstrings.
- Reaching for `RawAction` instead of typed modelling for an Apple-known identifier.
- Editing files in `~/personal/shortcut-lib/src/` directly when you should be editing in your worktree's `src/`.
