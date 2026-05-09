# Architecture Review — Round 1: Type System

**Reviewer**: Type-System Hawk
**Lens**: Make invalid programs unrepresentable. Every runtime `SchemaError` is a
type-system failure that should have been caught at type-check time.

---

## 1. Current-State Critique

### 1.1 `ParamValue` is the original sin

```python
# base.py:35
type ParamValue = (
    str | int | float | bool | None | "Action" | "Value" | dict[str, Any] | list[Any]
)
```

This union is simultaneously too wide and too narrow. Too wide because `dict[str, Any]`
and `list[Any]` erase all structure — a caller can pass any dict and pyright nods along.
Too narrow because it implies all slots accept all members of the union, which is false:
`WFURL` refuses a bare `WFTextTokenAttachment`; `WFDate` refuses the same; JSON body
slots want `dict` but text slots refuse `dict`. The type alias tells an LLM author "pass
anything" and then `coerce_text_field` discovers at emit time that the caller did the
wrong thing.

Pyright's current diagnostic output on `src/` reveals only **three real errors** outside
of missing stubs — and crucially, none of them are "wrong type passed to an action slot".
That silence is the bug. The type system is not catching anything interesting.

**Every `SchemaError` in `_params` methods is a type-system failure:**

| Location | Runtime check | What the type says | What it should say |
|----------|--------------|-------------------|-------------------|
| `DownloadURL._params` L148 | `url is None` raises | `ParamValue` (includes None) | required — no default |
| `DownloadURL._params` L152 | `body is not None and body_type is None` | independent fields | dependent — body requires body_type |
| `DownloadURL._params` L192 | `not isinstance(body, dict)` | `ParamValue` | `dict[str, Any]` when body_type is "JSON" |
| `AskForInput.__post_init__` L62 | `input_type not in _VALID_TYPES` | `str` | `Literal["Text","URL","Number","Date","Time","Date and Time"]` |
| `AskForInput.__post_init__` L69 | `allows_decimal not None and input_type != "Number"` | two unrelated fields | `allows_decimal` only exists when `input_type="Number"` |
| `FormatDate.__post_init__` L48 | `date_style not in _VALID_DATE_STYLES` | `str` | `Literal["None","Short","Medium","Long","Custom","Relative","RFC 2822","ISO 8601"]` |
| `FormatDate.__post_init__` L58 | `date_style == "Custom" and not custom_format` | `str \| None` | `custom_format: str` required when `date_style="Custom"` |
| `TextSplit.__post_init__` L36 | `separator not in _VALID_SEPARATORS` | `str` | `Literal["New Lines","Spaces","Every Character","Custom"]` |
| `TextSplit._params` L44 | `separator == "Custom" and not custom_separator` | `str \| None` | required when separator="Custom" |
| `UseModel.__post_init__` L61 | `model not in _VALID_MODELS` | `WFLLMModel` (already a Literal — good) | already correct |
| `AdjustTone.__post_init__` L62 | `tone not in _VALID_TONES` | `str` | `Literal["friendly","professional","concise","casual"]` |
| `SummarizeText._params` | `summary_type` is unchecked `str \| None` | any string | should be `Literal["createKeyPoints"] \| None` |
| `RepeatEach.to_actions` | `items is None` raises | `Any` (operand field) | required, no default |
| `RunWorkflow._params` L71 | `target is None` raises | `Any` | required typed union |
| `If.to_actions` L116 | unknown op string raises | `str \| WFCondition` | `WFCondition \| Literal["==","<",">","<=",">=",...]` |

That is fifteen runtime exceptions that should be caught earlier. Ten of them reduce to
"we have a `frozenset` validator but not a `Literal`"; four reduce to dependent
constructor arguments; one is a missing required field masked by `default=None`.

### 1.2 The `frozenset` validator antipattern

The codebase has a recurring pattern:

```python
# format_date.py
_VALID_DATE_STYLES = frozenset({"None", "Short", "Medium", "Long", ...})

@dataclass
class FormatDate(Action):
    date_style: str = "Short"     # ← str, not Literal

    def __post_init__(self) -> None:
        if self.date_style not in _VALID_DATE_STYLES:
            raise SchemaError(...)
```

There are **eight** occurrences of this pattern (date styles, time styles, separators,
tones, input types, body types, model names — `UseModel` has already been upgraded).
Each instance: (a) accepts invalid input at construction without IDE feedback; (b) raises
at emit time (`_params`) or init time, but after the object is fully constructed; (c)
tells pyright nothing. An LLM calling `FormatDate(date_style="custm")` gets a `SchemaError`
only when it calls `_params`, which may be many lines later. This is a type-system failure
dressed up as an error message.

`UseModel` already did this correctly: `WFLLMModel = Literal[...]` and the field is typed
`model: WFLLMModel`. The `__post_init__` validator there is redundant but harmless. The
other seven cases should follow the same migration.

### 1.3 `dict[str, Any]` erases wire-format structure

`coerce_text_field` and `coerce_value` return `Any`. The inner dicts — `WFTextTokenString`,
`WFTextTokenAttachment`, `WFDictionaryFieldValue` — are all `dict[str, Any]`. There is no
TypedDict for any of them. When `_encode_wf_dict` in `download_url.py` builds:

```python
items.append({
    "WFItemType": _WF_ITEM_TYPE_STRING,
    "WFKey": _make_wf_text_token_string(k),
    "WFValue": _make_wf_text_token_string(coerced_v),
})
```

pyright cannot check that `WFKey` is present, that `WFItemType` is an int, or that the
structure is a valid `WFDictionaryFieldValueItem`. A typo like `"WFItemtype"` would emit
silently, and the shortcut would fail on device. This is the same class of bug as the
`WFTextTokenString` envelope bug that was just swept (FU-7), except it's undetected
because there are no TypedDicts.

### 1.4 `NamedVar` is a stringly-typed footgun

```python
NamedVar("Polished")   # references variable named "Polished"
NamedVar("Polisehd")   # typo — zero static feedback
```

`NamedVar` takes a bare `str` with no connection to the `SetVariable` that created the
binding. The reference could be to a variable that was never set, or set under a
different name. In `vault_note_to_git.py`, there are seven `NamedVar` references across
three helper functions. If any `SetVariable(name=...)` string drifts from its
corresponding `NamedVar(...)` string, the shortcut silently produces empty values at
runtime. The type system has nothing to say about this.

### 1.5 `RunWorkflow.target: Any` — worst single field

```python
# compose.py:63
target: Any = None
```

This field accepts literally anything. The type should be
`Shortcut | tuple[str, str] | _SelfRef | _BoundSelf`. Because it is `Any`, pyright
propagates `Any` into `_resolve_target`, which in turn calls `.workflow_identifier` and
`.name` on `Any` without complaint. A caller passing `target="my-shortcut"` (a common
LLM mistake) would get a runtime `SchemaError` only at emit time.

### 1.6 `from __future__ import annotations` defers resolution, hiding gaps

Every file has `from __future__ import annotations`. This means all annotations are
strings at runtime, deferred to `get_type_hints()` calls. `describe_action` calls
`typing.get_type_hints(cls)` and falls back to `{}` on failure. If a forward reference
is unresolvable (which can happen with the `Action` / `Value` forward refs in
`ParamValue`), the registry silently reports the raw string annotation. The LLM then
sees `"Action"` (a string) rather than the resolved type. The `describe_action` fallback
swallows this without surfacing it — the narrowed `except (NameError, AttributeError,
TypeError)` in the SF-batch5 task is an improvement but still loses type fidelity.

### 1.7 Pyright findings summary

Running `pyright src/` with the project's own Python environment reveals three real errors:
- `compose.py:95,97` — `_resolve_target` return type is `tuple[str, str, bool]` but the
  `_BoundSelf` and `Shortcut` branches return `tuple[str | None, ...]`. This is a latent
  bug: `workflow_identifier` is typed `str | None` on `Shortcut`, and the return type
  annotation claims `str`. Pyright correctly catches this; it is not currently fixed.
- `actions/__init__.py:20` — `_mod` is possibly unbound in the pkgutil loop. Low severity
  but genuine.

Everything else is ignored because `ParamValue` and `Any` allow pyright to shrug at
every action construction and every `_params` call. The type system's silence is
proportional to how wide the unions are.

---

## 2. Ideal-State Thesis

### 2.1 Per-slot narrow types instead of `ParamValue`

Each Apple wire-format slot has a real type. Encode it. The current `ParamValue` alias
is a "no opinion" shrug; replace it with slot-specific type aliases:

```python
# base.py — wire-format type vocabulary

# A value that produces a string or variable reference at wire-format time.
type TextParam = str | Text | Output | NamedVar | MagicVar

# A value that produces a date reference at wire-format time.
type DateParam = Output | NamedVar | MagicVar

# A URL slot — must go through coerce_text_field (not bare WFTextTokenAttachment).
type URLParam = str | Text | Output | NamedVar | MagicVar

# An arbitrary variable/action output reference (not a dict body).
type VarParam = Action | Output | NamedVar | MagicVar | Text
```

Action slots then use these directly:

```python
@dataclass
class FormatDate(Action):
    input: DateParam = ...          # was ParamValue
    date_style: DateStyle = "Short" # was str

@dataclass
class DownloadURL(Action):
    url: URLParam = ...             # was ParamValue; None disallowed by no default
    headers: dict[str, TextParam] | None = None
```

This is not a dream — `UseModel` already does exactly this for `model` with `WFLLMModel`.
The pattern is proven; it just needs to be applied uniformly.

### 2.2 `Literal[...]` for all closed-set string fields

The `frozenset` validator pattern should not exist. Replace every instance:

```python
# Before:
_VALID_DATE_STYLES = frozenset({"None", "Short", "Medium", ...})
date_style: str = "Short"

# After:
type DateStyle = Literal["None", "Short", "Medium", "Long", "Custom", "Relative", "RFC 2822", "ISO 8601"]
date_style: DateStyle = "Short"
```

Pyright will catch `FormatDate(date_style="custm")` at type-check time with a red
underline, not at emit time with a `SchemaError`. The `__post_init__` validator becomes
redundant and can be removed (or kept as a belt-and-suspenders defence against
`Any`-typed callers). Eight fields to migrate; can be done in one commit.

### 2.3 Dependent constructor overloads for `AskForInput`

The `allows_decimal`/`allows_negative` fields only exist when `input_type="Number"`.
This is a classic dependent type situation. Python's `@overload` pattern from the stdlib's
own `open()` stubs handles exactly this:

```python
from typing import Literal, overload

@overload
def __init__(
    self,
    prompt: TextParam = "",
    input_type: Literal["Number"] = ...,
    default_answer: str | None = None,
    allows_decimal: bool | None = None,
    allows_negative: bool | None = None,
) -> None: ...

@overload
def __init__(
    self,
    prompt: TextParam = "",
    input_type: Literal["Text", "URL", "Date", "Time", "Date and Time"] = "Text",
    default_answer: str | None = None,
) -> None: ...
```

With this, `AskForInput(input_type="Text", allows_decimal=True)` is a pyright error
at construction, not a `SchemaError` at emit. The runtime check in `__post_init__` can
stay as a defence layer but becomes the last line of defence, not the only one.

The same pattern applies to `FormatDate`: `custom_format` only makes sense when
`date_style="Custom"`. And `TextSplit.custom_separator` only exists when
`separator="Custom"`. The `@overload` approach handles all three.

### 2.4 TypedDict for wire-format envelopes

The internal wire-format dicts should be TypedDicts. This would catch the exact class of
bug that FU-7 fixed manually:

```python
from typing import TypedDict, Required

class WFTextTokenAttachment(TypedDict):
    Value: dict[str, Any]
    WFSerializationType: Literal["WFTextTokenAttachment"]

class WFTextTokenStringValue(TypedDict):
    string: str
    attachmentsByRange: dict[str, dict[str, Any]]

class WFTextTokenString(TypedDict):
    Value: WFTextTokenStringValue
    WFSerializationType: Literal["WFTextTokenString"]

class WFDictionaryFieldValueItem(TypedDict):
    WFItemType: int
    WFKey: WFTextTokenString
    WFValue: WFTextTokenString
```

`coerce_text_field` and `coerce_value` could then be typed to return
`WFTextTokenString | WFTextTokenAttachment | str | int | float | bool | None` instead of
`Any`. A typo like `"WFItemtype"` in `_encode_wf_dict` would be a pyright error. This is
medium-sized work (the helpers need narrow return types, which ripples into callers), but
it directly addresses the class of bugs that caused FU-7.

PEP 728 (TypedDict closed) is accepted but not yet widely supported in pyright as of
early 2026. The `total=False` / `Required[...]` pattern is available today and is the
pragmatic path.

### 2.5 Typed variable bindings — `Var[T]` or a `VarRegistry`

`NamedVar("Polished")` is an unverifiable string. The ideal state has the library track
variable bindings:

```python
# Option A: typed at construction time
polished_var: Var[str] = s.set_variable("Polished", polished_action)
encoded = s.add(Base64Encode(input=polished_var))  # type-checked: Var[str] is valid TextParam

# Option B: registry checked at emit time
s.add(SetVariable(name="Polished", input=polished))
# ... later ...
s.add(Base64Encode(input=NamedVar("Polished")))  # emit-time: "Polished" confirmed set
```

Option A requires a `Var[T]` descriptor class and changes the authoring API (the LLM
would call `s.set_variable(...)` instead of `s.add(SetVariable(...))`). It gives full
static verification. Option B is a runtime check at `Shortcut.to_workflow()` time —
cheaper to implement, catches the typo before iOS sees it, but not a type-check win.

For the primary use case (LLM author), Option B is probably the right tradeoff: it keeps
the authoring API stable and catches the most dangerous failures (unset variable
references) at build time, not iOS runtime.

### 2.6 `Annotated[X, SlotMetadata(...)]` for registry introspection

The registry's `describe_action` could surface slot-level metadata if fields used
`Annotated`:

```python
from typing import Annotated

@dataclass
class DownloadURL(Action):
    url: Annotated[URLParam, SlotMeta(
        wire_key="WFURL",
        coerce=coerce_text_field,
        required=True,
        doc="Target URL. Accepts string, Text template, or variable reference.",
    )] = None  # noqa: type: ignore (required at emit)
```

`describe_action` extracts `SlotMeta` from `Annotated` metadata and returns it in the
structured description. The LLM author sees `required=True`, `wire_key="WFURL"`, and the
coercion path. This is directly useful for the "errors are training signal" design
principle. Pyright respects `Annotated` — the base type `URLParam` is still what gets
checked; the metadata is transparent to the type checker.

---

## 3. Top 3 Concrete Proposals

### Proposal 1: Migrate all `frozenset` validators to `Literal` — SMALL (1–2 days)

**Problem**: Eight action fields accept invalid strings at construction; errors surface
at `__post_init__` or `_params` time rather than at type-check time.

**Files affected**:
- `actions/ask.py` — `input_type: str` → `AskInputType = Literal[...]`
- `actions/format_date.py` — `date_style: str`, `time_style: str | None` → Literals
- `actions/text_split.py` — `separator: str` → `Literal[...]`
- `actions/writing_tools.py` — `AdjustTone.tone: str` → `Literal[...]`; `SummarizeText.summary_type` → `Literal["createKeyPoints"] | None`

**Migration path**:
1. Define the `Literal` type alias at module top (mirrors what `UseModel` already does
   with `WFLLMModel`).
2. Change the field annotation.
3. Remove or keep the `__post_init__` guard (keep it as a defence against `Any`-typed
   callers, but it's no longer load-bearing).
4. Run `prek run --all-files` — ruff and ty should both pass with zero changes to logic.

**Why prioritise**: This is the single highest-ratio type-safety improvement. Eight
fixes, zero behavioural change, maximum LLM-author benefit (IDE red underlines at call
sites). It's also a pilot for the broader migration and validates the `Literal` pattern
before tackling the harder dependent-type cases.

**Pilot**: Start with `FormatDate` (already has two style fields and a `Custom` dependent
relationship). Confirm pyright catches `FormatDate(date_style="bad")` before sweeping.

---

### Proposal 2: TypedDict the wire-format envelope layer — MEDIUM (3–5 days)

**Problem**: `coerce_value` and `coerce_text_field` return `Any`. Internal assembly
functions (`_encode_wf_dict`, `_make_wf_text_token_string`) build dicts as
`dict[str, Any]`. A typo in a key name emits silently; a structurally wrong dict causes
an iOS-runtime failure.

**Files affected**:
- `base.py` — add TypedDict definitions for `WFTextTokenAttachment`, `WFTextTokenString`,
  `WFDictionaryFieldValue`, `WFDictionaryFieldValueItem`; narrow `coerce_value` and
  `coerce_text_field` return types
- `values.py` — `Output.to_param()` and `NamedVar.to_param()` return types narrow to
  `WFTextTokenAttachment`
- `download_url.py` — `_encode_wf_dict` and `_make_wf_text_token_string` return
  `WFDictionaryFieldValue` and `WFTextTokenString` respectively

**Migration path**:
1. Define the TypedDicts in `base.py` (total=False with `Required` for mandatory keys,
   or simply total=True since all our envelopes have all keys populated).
2. Narrow `coerce_value` return type. This will surface caller sites where the return
   type is being used as `dict[str, Any]` in ways that are now more specific — expect
   some `isinstance` narrowing needed.
3. Fix any genuine type errors pyright finds. Each one is a potential iOS-runtime bug.
4. Check: `_resolve_target` in `compose.py` already has a pyright error
   (`str | None` vs `str`) — fixing the TypedDict layer is a good time to fix that too.

**Why prioritise**: TypedDict envelopes directly address the FU-7 class of bugs at the
type layer. The FU-7 fix was a runtime band-aid; TypedDicts are the structural prevention.
The `WFTextTokenString` / `WFTextTokenAttachment` distinction is the single most
consequential correctness issue in the codebase — a wrong envelope causes silent iOS
failures, not a Python exception. TypedDicts would have caught the FU-7 bugs before
they were deployed.

**Size caveat**: The return-type narrowing of `coerce_value` will cascade into every
action's `_params` method that uses the result. Budget a half-day of pyright error
triage after the TypedDicts land.

---

### Proposal 3: Dependent overloads for `AskForInput` and `FormatDate` — MEDIUM (2–3 days)

**Problem**: `AskForInput.allows_decimal` and `FormatDate.custom_format` are only valid
in specific modes. This is currently enforced by `__post_init__` runtime checks. An LLM
(or human) passing `allows_decimal=True` to a `Text`-type ask gets a `SchemaError` at
construction time — which is better than iOS runtime, but worse than type-check time.

**Files affected**:
- `actions/ask.py` — add `@overload` variants for Number vs. non-Number input_type
- `actions/format_date.py` — add `@overload` variant for `date_style="Custom"` requiring
  `custom_format: str`
- `actions/text_split.py` — add `@overload` variant for `separator="Custom"` requiring
  `custom_separator: str`

**Migration path**:
1. Add `@overload` signatures above the concrete `__init__`. Because these are
   dataclasses, `@overload` can't be placed on `__init__` directly — use a `__new__`
   overload pattern, or switch to a factory function (`AskForInput.number(...)`,
   `AskForInput.text(...)`) that is more explicit and LLM-friendly.
2. The factory function approach is actually *better* for an LLM author than overloads:
   `AskForInput.number(prompt="How many?", allows_decimal=True)` is unambiguous;
   `AskForInput(input_type="Number", allows_decimal=True)` requires remembering the
   constraint.
3. Keep the original constructor for back-compat; mark as `@deprecated` in the docstring.
4. `describe_action` should surface the factory methods alongside parameters.

**Why prioritise**: `AskForInput` is one of the highest-frequency actions (Tier 1
coverage). The `allows_decimal` / `input_type` coupling is the most-cited example of a
"runtime validation that should be static" throughout the review. It is the canonical
pilot for the dependent-type pattern. If factory methods prove ergonomic, the pattern
generalises to `FormatDate`, `TextSplit`, `DownloadURL` (body/body_type coupling), and
`RunWorkflow` (the `_SelfRef` / `_BoundSelf` target resolution).

**Note on `dataclass_transform` (PEP 681)**: This PEP allows custom decorators to tell
type checkers how to synthesise `__init__` signatures, which would make `@register`
teach pyright to narrow the init on known subclasses. However, this is advanced and
potentially fragile. The overload / factory approach is more legible for an LLM author
and doesn't require type-checker-specific magic.

---

## Summary

The codebase has done the hard work of building a real round-trip encoder with empirical
sample grounding. The type system is currently decorative — pyright finds three real
errors in `src/`, and none of them are in action parameter slots, which is where the
real risk lives. The three proposals above address the gap in order of effort-to-impact:

1. **Literal migration** — eight fields, one commit, maximum static coverage for zero
   behavioural change. Do this first.
2. **TypedDict envelopes** — addresses the class of bug that just burned you (FU-7);
   turns runtime-silent structural errors into pyright errors.
3. **Dependent overloads / factory methods** — addresses the `AskForInput` case and
   establishes the pattern for all dependent-parameter relationships.

The `NamedVar` stringly-typed variable reference problem is real but lower priority — an
emit-time binding check (Proposal B from §2.5) would catch 90% of the risk without
changing the authoring API, and can be added after the type-annotation work is stable.

The goal: `uv run pyright src/` should find meaningful errors in action call sites, not
silence. Right now it shrugs at everything because `ParamValue = ... | Any | ...`.
