# Architecture Review Round 1 — LLM-Author UX

**Reviewer perspective:** LLM-Author UX Designer
**Date:** 2026-05-09
**Scope:** Discoverability surface, error-message quality, silent-failure taxonomy,
skill file shape, worked examples.

---

## 1. Current-state critique

### 1.1 Day-in-the-life walkthrough

The LLM-author's entry point is one of three skills (`make-shortcut`, `edit-shortcut`,
`decode-shortcut`). The make-shortcut skill instructs the LLM to first run
`uv run python scripts/print_actions.py`, which emits a well-structured Markdown
table — name, identifier, one-line doc, and parameter signature. That is the
primary discoverability surface, and it's already better than most domain-specific
authoring APIs.

The `describe_action` path (used internally by `print_actions.py`) is also good:
it resolves type hints through `typing.get_type_hints`, formats the `ParamValue`
union usefully, and surfaces `has_default`. What the output does **not** tell the
LLM:

- Which parameters are semantically required vs. truly optional. `url: ParamValue`
  in `DownloadURL` has `has_default=True` because it defaults to `None`, but
  calling `DownloadURL(url=None)` raises `SchemaError` at emit time. The flag says
  "optional" but the runtime says "required."
- What valid string enum values are. `AskForInput.input_type: str` — the LLM has
  to know that `"URL"`, `"Number"` etc. are the only valid values, but `str` is all
  `print_actions.py` shows. Compare `UseModel.model`, which surfaces
  `Literal[Apple Intelligence, Private Cloud Compute, ...]` — that is the right
  shape and is zero-shot correct.
- What the `Text` constructor looks like. The values section shows only the
  one-line docstring. The substitution signature — `Text("...{x}...", x=something)`
  — is the most frequently-needed pattern in real shortcuts, and the LLM cannot
  derive it from the one-liner.
- Which parameters are in `coerce_text_field` territory vs. `coerce_value`
  territory. This is the distinction that caused the WFTextTokenString envelope bug
  and is entirely invisible to the authoring LLM.

### 1.2 Error-message audit

**Good messages — teach the right answer on the first try:**

`AskForInput.__post_init__` (type validation):
```
AskForInput.input_type='URL2' is not a valid Apple input type. Use one of
['Date', 'Date and Time', 'Number', 'Text', 'Time', 'URL'].
```
Grade: A. Exact class name, exact field name, wrong value quoted, full valid set.

`FormatDate.__post_init__` (Custom without format):
```
custom_format must be set when date_style is "Custom".
Example: custom_format="yyyy-MM-dd"
```
Grade: A. States the precondition, provides a copy-paste example.

`If` bad operator:
```
unknown condition op 'eq' — pass a WFCondition enum member or one of
['<', '<=', '==', '>', '>=', 'begins-with', 'contains', 'does-not-exist',
'ends-with', 'exists', 'is-not-true', 'is-true']
```
Grade: A. Tells the LLM both the enum path and the string-alias path.

`Dictionary._encode_value` non-primitive in array:
```
Dictionary list entry contains a non-primitive value of type 'NamedVar'.
Arrays in Dictionary entries must contain only str, int, float, or bool.
To embed a variable reference, use a templated string (Text) instead.
```
Grade: A-. Clear, actionable. The "use Text instead" hint is valuable training
signal — it directs the LLM toward the correct abstraction.

**Mediocre messages — incomplete or missing the fix:**

`DownloadURL._params` (missing url):
```
DownloadURL requires a url — pass a string, Text template, or an Action
whose output is a URL.
```
Grade: B. Correct, but doesn't say "url=..." so the LLM still has to look up the
parameter name from the describe_action output. A small cost; not blocking.

`SetVariable._params` (empty name):
```
SetVariable requires `name`
```
Grade: C. No hint about why a name is required, no example. Should be:
```
SetVariable requires a non-empty name (WFVariableName). Example:
SetVariable(name="Token", input=token_action)
```

`RepeatEach.to_actions` (missing items):
```
RepeatEach requires `items` (a list-typed Output or value)
```
Grade: C+. Acceptable but skips the obvious: what does a list-typed Output look
like? The LLM already knows about `Output` from `describe_action`, but "list-typed"
is a semantic qualifier with no mechanical definition. Should say: "pass the output
of an action that returns a list, e.g. `items=text_split_action.output()`".

`RawAction.to_action_dict` (missing raw_identifier):
```
RawAction needs raw_identifier
```
Grade: D. Minimal. Who calls `RawAction` directly? The LLM-author does, when
modelling an unregistered action. This message provides no example and no hint
that `raw_params` must mirror the decoded wire dict.

`coerce_token` wrong type:
```
cannot coerce int to a token — pass an Action, Output, NamedVar, MagicVar, or
other Value
```
Grade: B+. Reasonable but the LLM often hits this when they pass a plain
`NamedVar("Foo")` in a `Text` substitution dict and accidentally wrap it one level
too deep. A concrete example of the correct shape would save a turn.

`Value.to_token` fallback:
```
{ClassName} does not have a token form usable inside Text
```
Grade: C. The LLM doesn't know what "inside Text" means mechanically at this
point. Should say: "Use this value directly as an action parameter, not as a
substitution in Text('...{x}...', x=...). Only Output, NamedVar, and MagicVar can
appear as substitutions."

### 1.3 Silent-failure taxonomy

The most dangerous class is failures that produce a valid bplist, emit no Python
error, import into Shortcuts.app without complaint, but silently do the wrong
thing on iOS. These are the hardest to debug — the LLM sees success at every prior
step.

| Failure mode | Detection point | Signal quality |
|---|---|---|
| Variable ref as bare `WFTextTokenAttachment` in a `WFTextTokenString` slot | iOS runtime | Silent: field appears blank or "No URL Specified" |
| `SetVariable(name="")` | Emit (after FU-7) | None today; will raise after SF-batch4 |
| `GetText(text=None)` | Emit | None — emits `None` as wire value |
| `RunWorkflow` UUID mismatch after re-run | iOS runtime | Silently no-ops |
| `Shortcut.workflow_identifier` changes each run | iOS runtime | Silent composition break |
| `WFWorkflowImportQuestions` destroyed on lift | Lift round-trip | Silent data loss |
| Body dict value containing an `Action` in `Dictionary._encode_entry` | Emit | Raised correctly after current patch |
| `DownloadURL(url=None)` | `_params()` call | Raised — but only at emit time, not construction |

The coerce-path silent failure (bare `WFTextTokenAttachment` vs. `WFTextTokenString`)
was the most dangerous class identified in practice. It was discovered only via
on-device testing. The `coerce_text_field` helper now covers known slots, but the
LLM has no way to know which slots need it — the API surface is `ParamValue`
everywhere.

### 1.4 Discoverability gaps in the registry output

Running `print_actions.py` produces good tabular output, but several gaps make
zero-shot authoring harder than necessary:

**Gap 1 — `Text` constructor signature is absent.** The values section says:
```
### Text
_Templated string with embedded variable substitutions._
```
The actual constructor — `Text(template: str, substitutions: dict[str, Any])` — is
never shown. The skill SKILL.md shows one example in the boilerplate, but the LLM
has to hold that in context for the full session. Every framework that ships
embedded examples (PydanticAI's `require_parameter_descriptions=True`, Anthropic's
`input_examples` field on tool definitions) shows this is load-bearing. The `Text`
pattern is complex enough that an inline worked example would eliminate the most
common authoring mistake.

**Gap 2 — enum constraints missing for `str`-typed parameters.** Parameters shown
as `str` with an implicit closed set (`AskForInput.input_type`,
`RecordAudio.start`, `TextSplit.separator`, `Base64Encode.mode`) give the LLM no
constraint at all. The `UseModel.model` field correctly shows
`Literal[Apple Intelligence, ...]` — that pattern should be applied uniformly.
After SF-batch4's `TextSplit` closed-set addition, the `str` annotation should
become a `Literal`.

**Gap 3 — `has_default` conflates dataclass contract with semantic requiredness.**
This is FU-1, already known. The practical impact: `DownloadURL.url` shows
`has_default=True`, which the LLM interprets as "I can omit this." It cannot.
The LLM writes `DownloadURL(method="GET")`, gets a `SchemaError` at emit time, and
has to re-read the source to understand why. One extra turn.

**Gap 4 — No "intent → action" lookup.** The LLM knows it wants to "split a text
by comma" and must find `TextSplit` by browsing all 24 actions. There is no
`find_action_by_intent("split text")` equivalent. PydanticAI and smol-agents both
support semantic tool search. The Anthropic docs now recommend `tool_search_tool`
for large tool sets. At 24 actions this is manageable; at 50+ it becomes a
real cost.

**Gap 5 — Skills describe composition with stale RunWorkflow docs.** The
`make-shortcut` SKILL.md's composition section still shows the multi-shortcut
`RunWorkflow` pattern (helper + orchestrator), but the 2026-05-09 decisions log
explicitly deprecated this in favour of Python helper functions within a single
`Shortcut`. An LLM following SKILL.md will produce a pattern that requires manual
re-wiring after iOS import. This is a direct contradiction between the skill and
the decisions log.

**Gap 6 — No worked example for control-flow authoring.** The examples directory
has `vault_note_to_git.py` (a real, non-trivial shortcut) and `note_to_github.py`
(a trimmed variant). Neither uses `If`, `RepeatEach`, or `ChooseFromMenu`. An LLM
authoring a shortcut that needs conditional branching has no worked reference — it
must construct the `If(operand=..., op="==", then=[...], otherwise=[...])` pattern
cold. `If` is the most failure-prone construct (GroupingIdentifier pairing,
`_wrap_variable_input` envelope) and has no canonical example.

---

## 2. Ideal-state thesis

### What the LLM needs at each decision point

**Decision 1: What actions exist?** The LLM runs `print_actions.py` or calls
`list_actions()`. The output should be sufficient to select the right action
without reading source files. That means: name, one-line intent, the full
parameter list with semantic constraints (Literal enums, not bare `str`), a
required/optional marker that reflects runtime behaviour (not dataclass defaults),
and a mini-example for every non-trivial action.

Ideal `describe_action` output for `AskForInput`:

```
AskForInput  →  "Provided Input"
is.workflow.actions.ask

Prompt the user to type or speak a value. Keyboard type and picker
are controlled by input_type.

Parameters:
  prompt         ParamValue   optional    The text shown above the input field.
  input_type     required     One of: "Text" | "URL" | "Number" | "Date" |
                              "Time" | "Date and Time". Default: "Text"
  default_answer str | None   optional    Pre-filled answer. String only.
  allows_decimal bool | None  optional    Number only. Omit for other types.
  allows_negative bool | None optional    Number only. Omit for other types.

Example:
  AskForInput(prompt="Enter your name", input_type="Text")
  AskForInput(prompt="How many?", input_type="Number", allows_decimal=False)
```

**Decision 2: How do I wire outputs together?** The LLM needs a single clear
mental model: `s.add(action)` returns the `Action` instance; passing the instance
directly as a parameter coerces via `coerce_value`; for `Text` templates, pass the
instance in `substitutions={"key": action}`. This model is documented in the
skill but not surfaced by the registry. The `describe_action` output should include
a "chaining pattern" note for actions that are typically used as inputs to later
actions (i.e., those with a non-empty `default_output_name`).

**Decision 3: Did I get the envelope right?** Today this is invisible. The ideal
state is that the LLM never needs to think about `coerce_text_field` vs.
`coerce_value`. The API should enforce the correct coercion internally. Where that
isn't possible (e.g., the `Text` `substitutions` dict), the error message at
coercion time should state the expected shape, not just the wrong type.

**Decision 4: Did the shortcut emit correctly?** The current workflow is: run the
script, check that `save_signed` succeeded, then run `shortcut-decode --format
buzz`. This is good. The gap is that `buzz` output doesn't surface which parameters
are live variable references vs. baked strings — both look like `${Name}` in the
output but the encoding is different.

**Decision 5: What went wrong on iOS?** Today: nothing. This requires a feedback
path (decode the re-exported shortcut from the device) that doesn't exist yet. Out
of scope for this review.

### What an LLM-first `describe_action` looks like

The current `describe_action` returns:

```python
{
    "name": "AskForInput",
    "identifier": "is.workflow.actions.ask",
    "doc": "Prompt the user to enter a value.\n\n...",
    "default_output_name": "Provided Input",
    "parameters": [
        {"name": "prompt", "type": "ParamValue", "has_default": True},
        {"name": "input_type", "type": "str", "has_default": True},
        ...
    ]
}
```

The ideal adds:

```python
{
    ...
    "parameters": [
        {
            "name": "input_type",
            "type": "str",
            "has_default": True,
            "semantic_required": False,
            "valid_values": ["Text", "URL", "Number", "Date", "Time", "Date and Time"],
            "default": "Text",
        },
        ...
    ],
    "examples": [
        "AskForInput(prompt='Enter name')",
        "AskForInput(prompt='How many?', input_type='Number', allows_decimal=False)",
    ],
    "output_chaining": "Pass the returned Action to SetVariable(input=...) or "
                       "as a Text substitution value.",
}
```

### What a good SchemaError teaches

Anthropic's own guidance: "Replace cryptic error codes with actionable guidance.
Instead of a traceback, direct agents toward correct usage."
[writing-tools-for-agents](https://www.anthropic.com/engineering/writing-tools-for-agents)

The instructor library demonstrates automatic retry loops where the Pydantic
validation error is embedded back into the prompt: the LLM sees not just what was
wrong but what shape the model expected, and corrects on the next generation.
shortcut-lib doesn't have a retry loop, but it can adopt the same pattern for its
error messages: every `SchemaError` should read as if it were the embedded error
in an instructor retry — complete enough that the LLM can fix the call on first
re-read.

Template for a good SchemaError:
```
{ClassName}.{field} = {bad_value!r}
{What the constraint is}
{What the correct value should be}
Example: {ClassName}({field}={correct_example!r})
```

---

## 3. Top 3 concrete proposals

### Proposal 1 — Semantic-required markers + closed enum types in `describe_action`

**Size:** Small. 2–3 days. Parallelisable with other work.

**Problem it solves:** Gaps 2 and 3 above. The LLM sees `url: ParamValue,
has_default=True` and omits it. It sees `input_type: str` and guesses `"text"`.
Both waste turns.

**Concrete changes:**

1. Add `_REQUIRED_PARAMS: ClassVar[frozenset[str]]` to every action class that
   has semantically-required fields whose dataclass default is `None` or empty.
   The set names the fields that `_params` will raise on if absent.

   ```python
   # In DownloadURL:
   _REQUIRED_PARAMS: ClassVar[frozenset[str]] = frozenset({"url"})
   ```

2. Update `describe_action` to emit `"semantic_required": True` for any parameter
   in `_REQUIRED_PARAMS` (regardless of `has_default`).

3. Promote all implicit closed-string sets to `Literal` type annotations:
   - `AskForInput.input_type` → `Literal["Text", "URL", "Number", "Date", "Time", "Date and Time"]`
   - `TextSplit.separator` → `Literal["New Lines", "Spaces", "Every Character", "Custom"]` (SF-batch4)
   - `Base64Encode.mode` → `Literal["Encode", "Decode"]` (check against sample)
   - `RecordAudio.start` → verify valid values from decoded sample, then `Literal`
   - `FormatDate.date_style` / `time_style` → already have `_VALID_*` sets; promote to `Literal`

4. `print_actions.py` prints `required` or `optional` next to each parameter, and
   lists the `Literal` values in the signature column.

**Impact:** The parameters table goes from `input_type: str` to
`input_type: Literal["Text", "URL", "Number", ...]  required` — the LLM can
now fill the slot correctly on first attempt without a validation round-trip.

**Rewrite these 5 `SchemaError`s to the standard pattern:**

- `SetVariable._params` (`name` empty): include field name, constraint, example.
- `RepeatEach.to_actions` (`items` missing): add example of list-typed output.
- `RawAction.to_action_dict` (`raw_identifier` missing): add example of construction.
- `Value.to_token` fallback: explain "inside Text" concretely, say which Value
  subclasses support it.
- `UseModel._params` (`prompt` is None): add example with `Text(...)` and plain string.

---

### Proposal 2 — Add a worked `If`/`RepeatEach` control-flow example + fix the stale RunWorkflow docs in SKILL.md

**Size:** Small-medium. 1 day.

**Problem it solves:** Gap 5 (stale composition docs), Gap 6 (no control-flow
example). The make-shortcut skill is the LLM's primary guide. It currently
contradicts the decisions log on composition.

**Part A — Fix the stale skill.**

In `skills/make-shortcut/SKILL.md`, replace the composition section's
multi-shortcut `RunWorkflow` sketch with the current Python-function-per-step
pattern. The corrected section should say:

> **Composition pattern (current).** Since iOS assigns fresh UUIDs at import,
> pre-linked `RunWorkflow` calls don't survive import. Compose via Python
> functions that each call `s.add(...)` on the same `Shortcut` instance. See
> `examples/vault_note_to_git.py` (`_add_config`, `_add_polish`, `_add_push`).
> Reserve `RunWorkflow` for genuinely separate-trigger helpers (auth setup,
> iCloud-shared utilities) that the user will wire manually after import.

Delete the 15-line `polish + main` sketch that shows the old pattern; it is now
misleading.

**Part B — Add `examples/control_flow_demo.py`.**

A ~60-line example that demonstrates `If`, `RepeatEach`, and `ChooseFromMenu` in
a single runnable shortcut. Suggested scenario: ask the user for a number, if > 0
repeat `RepeatCount` times showing a notification, else show a "zero" message.
This is intentionally minimal so it stays readable and copyable. The file becomes
the canonical reference the LLM reaches for when authoring any branching shortcut.

Add a reference to this example in `print_actions.py`'s control-flow section:

```
### If
_Conditional branching._
Example: examples/control_flow_demo.py
```

**Part C — Add a `Text` worked example to the values section of `print_actions.py`.**

The one-liner `_Templated string with embedded variable substitutions._` is not
enough. Append the constructor signature and a two-line usage example:

```
### Text(template, substitutions={...})
_Templated string with embedded variable substitutions._
Usage:
  Text("Hello {name}", substitutions={"name": NamedVar("FirstName")})
  Text("Score: {n}", substitutions={"n": score_action})
```

---

### Proposal 3 — Add `registry.find_action_by_intent(query: str) -> list[dict]`

**Size:** Medium. 2–3 days. Zero runtime dependencies if using simple keyword
matching; one extra dependency (rapidfuzz or similar) if fuzzy.

**Problem it solves:** Gap 4 — the LLM knows what it wants to do conceptually
but must scan all 24 actions to find the right class. At the current 24-action
size this is a minor friction. With 50+ actions — the natural growth path as
Tier 3 actions are added — it becomes a real multi-turn tax.

**Concrete design:**

```python
def find_action_by_intent(query: str, *, top_k: int = 3) -> list[dict[str, Any]]:
    """Return the top-k registered actions matching a natural-language intent.

    Matches against action name, identifier, and first doc line using
    case-insensitive substring matching, ranked by match count.

    Args:
        query: Natural language description of desired behaviour.
            E.g. "split text", "http request", "show user a message".
        top_k: Maximum number of results. Defaults to 3.

    Returns:
        List of ``describe_action`` dicts, best match first.

    Example:
        >>> find_action_by_intent("send http request")
        [{"name": "DownloadURL", ...}, {"name": "GetText", ...}, ...]
    """
```

Implementation: tokenise the query on whitespace, score each registered action
by how many tokens appear in its name + identifier + first doc line (case-fold),
return top-k. No ML required. Total implementation ~30 lines.

Add an alias vocabulary dict: `{"get url": "DownloadURL", "http": "DownloadURL",
"clipboard": "GetClipboard", "notify": "ShowNotification", "ask": "AskForInput",
"split": "TextSplit", ...}`. This costs ~20 lines and fixes the cases where the
LLM's natural query term (`"http get"`, `"send a notification"`) has zero overlap
with the class name.

Expose in `print_actions.py` with a `--search` flag:

```
uv run python scripts/print_actions.py --search "send http request"
```

This is the LLM's equivalent of `man -k` — fuzzy search of the action surface
before committing to a specific class. It reduces the "scan all 24" cost to
zero for the common case.

The Anthropic docs now recommend `tool_search_tool` for large tool registries.
This proposal is the in-process equivalent: a cheap search step before the
heavier `describe_action` call.

---

## Summary table

| Proposal | Gap addressed | Turns saved | Size | Priority |
|---|---|---|---|---|
| 1 — Semantic-required + Literal enums | `has_default` lie, implicit enums, 5 weak errors | 1–2 per session | Small | High |
| 2 — Control-flow example + fix stale SKILL.md | No branching reference, stale composition docs | 2–3 per branching session | Small-med | High |
| 3 — `find_action_by_intent` | No intent→action lookup | 0–2 per session (deferred) | Medium | Medium |

Proposals 1 and 2 address the highest-frequency failure modes: wrong enum value,
wrong required/optional judgment, and stale composition guidance. Both are
mechanical changes that require no new dependencies and no architectural decisions.
Proposal 3 is a quality-of-life investment for when the action count grows past
~40.
