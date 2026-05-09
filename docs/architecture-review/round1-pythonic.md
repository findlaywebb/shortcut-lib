# Architecture Review — Round 1: Pythonic API

**Lens**: Declarative, annotation-driven Python. Primary user is an LLM (Claude Code), not a human. Reference points: Pydantic v2, FastAPI, Strawberry, Litestar, Pydantic AI.

---

## 1. Current-State Critique

### What's load-bearing and smart

The registry/auto-discovery pattern (`@register` + `pkgutil`) is genuinely good. Dropping a new file in `actions/` to extend the schema — with no shared-file edits — is the correct structure for an LLM-authored library. The discoverability contract (`list_actions`, `describe_action`) is well-considered: it gives Claude a runtime-queryable surface rather than requiring it to read source files to know what exists. The decision to make errors training signal — explicit `SchemaError` messages that state what was wrong and what shape is expected — is architecturally sound and frequently missing in Python libraries.

`coerce_text_field` is a pragmatic but correct fix for a real Apple-side footgun. The fact that it lives in `base.py` and gets applied consistently across slots that empirically require it shows the team is sample-grounded rather than spec-guessing.

`Text("... {n}", substitutions={"n": NamedVar("Note")})` is readable. The template-substitution pattern is honest about what it does and doesn't obscure wire-format concerns from the caller.

`Shortcut.from_workflow` → `RawAction` passthrough is the right design for round-trip. Don't fight unknown identifiers; passthrough them.

### What's smart but fragile

`ParamValue` as a `type` alias (`str | int | float | bool | None | Action | Value | dict | list`) is now the right shape (SF-batch7 already landed it). The problem is that it's applied at the slot level as a type annotation, but the semantic contract for each slot is not encoded in the type. `DownloadURL.url: ParamValue` and `DownloadURL.body: ParamValue` carry identical static types but radically different runtime semantics. The type system is currently doing no work on that distinction. An LLM reading `describe_action("is.workflow.actions.downloadurl")` sees `url: ParamValue` and `body: ParamValue` — the difference between "text-token-string slot" and "generic-value slot" is invisible until `coerce_text_field` vs `coerce_value` is called at emit time.

`__post_init__` as the validation site is conventional but has a problem: the validation only fires at construction time, not at emit time. If a caller mutates a field after construction (entirely possible on a dataclass), the validation is silently bypassed. `FormatDate(date_style="Custom")` raises at construction — good. But `fd = FormatDate(date_style="Short"); fd.date_style = "Custom"` (forgetting `custom_format`) silently emits a broken shortcut. The fix is either frozen dataclasses (which prevents mutation entirely) or validation-on-emit. More on this below.

The `@register @dataclass` double-decorator stack is a compound smell. It requires both decorators in the right order; changing either silently breaks the other. A junior engineer or LLM writing a new action has to remember the correct stacking. `@dataclass_transform` (PEP 681) exists precisely to collapse this.

### What's vestigial

`default_output_name: ClassVar[str] = ""` falls back to the class name when empty. This means every action that doesn't set it produces output references named after the Python class, which may not match Shortcuts.app's display name. Half the actions set it correctly; half don't. This is a semantic gap the registry currently doesn't surface.

`Action.identifier: ClassVar[str] = ""` is checked at `to_action_dict` time with a `SchemaError`. The check fires at emit time, not at class-definition time. A registered action with a missing identifier is caught only when `to_actions()` is called — too late, and invisible to the type checker. The `@register` decorator already checks for empty identifiers, but the base class default keeps `ClassVar[str] = ""` as a valid base-class state, which is a lie.

`NamedVar("Token")` is a stringly-typed handle on a named variable. The name is a bare string; nothing connects the string at a `SetVariable(name="Token")` call site to the `NamedVar("Token")` at the read site. An LLM that misspells `NamedVar("Toekn")` produces a silent runtime failure with no error until iOS runs the shortcut. The library currently has zero static or build-time detection for this class of bug.

### What's wrong

The composition model after the iOS UUID-pivot is "Python helper functions that mutate a `Shortcut` instance." The canonical example (`_add_config`, `_add_polish`, `_add_push`) is procedural: each function calls `s.add(...)` as a side effect. There is no reusable, shareable, testable unit that says "this is the polish step" — there's a function that appends actions to whatever `Shortcut` you hand it. This works for the current single-shortcut case but has no scaling story: you can't compose `_add_polish` into two different shortcuts without the function leaving no trace of what it consumed or produced. The return type of `_add_polish` is `None`, so its outputs (the `SetVariable("Polished")` it creates) are communicated only through the stringly-typed `NamedVar("Polished")` at the call site. This is the named-variable coupling problem in its starkest form.

The `_extra: dict[str, Any]` escape hatch on `Shortcut` is pragmatically correct for round-trip but will accumulate. Every un-modelled top-level key lands in `_extra`; over time this becomes an undocumented bag. There's no type-safe path to author or inspect the contents.

---

## 2. Ideal-State Thesis

The ideal V2 call site reads like a typed recipe, not an imperative script. The authoring experience should satisfy three properties:
1. **Errors fire at build time** (when `to_workflow()` is called), not at iOS runtime.
2. **Named-variable coupling is structural**, not stringly-typed.
3. **A "block" is a first-class Python unit** with typed inputs, typed outputs, and no ambient-mutation side effects.

### The right primitive for "block"

The correct primitive is a **function that returns typed output variables**, called with a `Shortcut` builder. Not a plain function that mutates a `Shortcut` argument, and not a class hierarchy. The key insight from FastAPI's dependency injection is that the *call site* should declare what it needs and what it produces, and the framework resolves the wiring. The equivalent here is:

```python
# TODAY (procedural, stringly-typed coupling):
def _add_polish(s: Shortcut) -> None:
    note = s.add(GetClipboard())
    s.add(SetVariable(name="Note", input=note))
    polished = s.add(UseModel(prompt=..., model="Apple Intelligence"))
    s.add(SetVariable(name="Polished", input=polished))

# V2 target (typed outputs, no ambient mutation):
@block
def polish(s: ShortcutBuilder, *, note: Var[str]) -> Var[str]:
    cleaned = s.add(UseModel(
        prompt=Text("Polish this:\n\n{n}", n=note),
        model="Apple Intelligence",
    ))
    return s.named(cleaned, "Polished")
```

The `@block` decorator makes `polish` a reusable, independently-testable unit with a typed signature. `Var[str]` is a typed variable reference — `Var[T]` plays the role `VarRef[T]` would play in a more generic system. The function returns its outputs explicitly; callers don't reach into the Shortcut's state via `NamedVar("Polished")`.

Composition then reads as:

```python
def build() -> Shortcut:
    s = Shortcut(name="Vault Note To Git", surfaces=["share", "quick-action"])
    token, repo = config(s)
    polished = polish(s, note=clipboard(s))
    push(s, polished=polished, token=token, repo=repo)
    return s
```

This is compositional without being a class hierarchy, without context managers (which would obscure the data flow), and without a DAG engine. The `Var[str]` type is essentially what `NamedVar` already is, promoted to the type level.

### Slot-level typing with `Annotated`

The current `ParamValue` alias is a step forward but stops at "any of these types." The real semantic gap is that `WFURL` and `WFInput` have different wire-format requirements. V2 should express this at the field type:

```python
# TODAY:
url: ParamValue = None           # any of str|int|...|Action|Value|dict|list
body: ParamValue = None          # identical type, different semantic

# V2 target — slot metadata in the type, visible to describe_action and LLM:
from typing import Annotated
from shortcut_lib.schema.base import TextTokenSlot, ValueSlot

url: Annotated[ParamValue, TextTokenSlot] = None
body: Annotated[ParamValue, ValueSlot] = None
```

`TextTokenSlot` and `ValueSlot` are marker types (zero-runtime-cost `Annotated` metadata). `_params()` implementations call `coerce_text_field` vs `coerce_value` based on the slot marker, rather than each action hardcoding the choice. `describe_action` reads `Annotated` metadata via `typing.get_type_hints(include_extras=True)` and surfaces the slot class to the LLM. The LLM then knows that a `TextTokenSlot` parameter will always be wrapped as `WFTextTokenString`; it doesn't need to reason about `coerce_text_field` existence.

Beyond slot markers, enum-constrained slots should use `Literal` or `Enum` in `Annotated`:

```python
# TODAY:
model: WFLLMModel = "Apple Intelligence"  # WFLLMModel is a Literal alias, OK

# V2 — consistent pattern across all constrained slots:
date_style: Annotated[str, Literal["None","Short","Medium","Long","Custom","Relative","RFC 2822","ISO 8601"]] = "Short"
```

The validation that currently lives in `__post_init__` can then move to the emit path, where it fires for all code paths including post-construction mutation.

### `dataclass_transform` and the decorator stack

PEP 681's `@dataclass_transform` (available in `typing` since Python 3.12, in `typing_extensions` for older) lets a library define a single `@action` decorator that, to type checkers, behaves exactly like `@dataclass`. The `@register @dataclass` double-stack collapses:

```python
# TODAY:
@register
@dataclass
class GetText(Action):
    identifier: ClassVar[str] = "is.workflow.actions.gettext"
    ...

# V2 target:
@action("is.workflow.actions.gettext", output="Text")
class GetText(Action):
    text: TextParam = ""
```

`@action` is decorated with `@dataclass_transform(field_specifiers=(field,))`, so Pyright/mypy see it as a dataclass. It calls `dataclass(cls)` internally, registers the class, validates the identifier at class-definition time (not at emit time), and can enforce that `identifier` is always provided. The `ClassVar[str] = ""` lie is gone.

### Validation at emit time, not construction time

V2 actions should be frozen dataclasses (preventing post-construction mutation) OR emit-time validators. The "frozen" approach is simpler and aligns with the existing `@dataclass(frozen=True)` on `Output` and `NamedVar`. Frozen actions can't be mutated after construction, so `__post_init__` validation is sufficient. The builder pattern in `vault_note_to_git.py` never mutates an action after construction anyway; frozen is the right default.

Making all action classes frozen also enables the identity check in `Shortcut.add` to be expressed as a type-level invariant rather than a runtime check: the same frozen instance can never accumulate mutations from two different call sites.

---

## 3. Top 3 Concrete Proposals

### Proposal 1 — Typed named-variable coupling (`Var[T]` return from blocks)

**What**: Replace the stringly-typed `NamedVar("Polished")` coupling with a structured `Var[str]` that carries the variable name internally. Introduce a `Var[T]` generic as a thin wrapper around `NamedVar` that carries a phantom type parameter.

**Concrete pattern** (pilot on `vault_note_to_git.py` + `set_variable.py`):

```python
# src/shortcut_lib/schema/values.py — add:
from typing import Generic, TypeVar
_T = TypeVar("_T")

class Var(NamedVar, Generic[_T]):
    """A typed named variable reference.

    Var[str] means "a named variable that will contain text".
    Var[int] means "a named variable that will contain a number".
    The type parameter is phantom — it's for type checking only.
    Construct via Shortcut.set_var() not directly.
    """
    pass  # inherits NamedVar.to_param(), to_token(); T is phantom

# src/shortcut_lib/builder.py — add to Shortcut:
def set_var(self, name: str, source: Action, type_hint: type[_T] = str) -> Var[_T]:
    """Add a SetVariable action and return a typed Var reference."""
    self.add(SetVariable(name=name, input=source))
    return Var(name=name)  # type: ignore[return-value]
```

Then `_add_polish` becomes:

```python
def add_polish(s: Shortcut, note: Var[str]) -> Var[str]:
    result = s.add(UseModel(
        prompt=Text("Polish:\n\n{n}", substitutions={"n": note}),
        model="Apple Intelligence",
    ))
    return s.set_var("Polished", result, str)
```

The caller passes a `Var[str]`; the function returns a `Var[str]`. Typos on the variable name (`Var[str]("Toekn")` vs `Var[str]("Token")`) are still not caught by the type checker at this stage — that requires a more invasive descriptor approach. But the explicit threading of `Var` objects through function signatures eliminates the silent ambient-coupling via `NamedVar("...")` scattered across unconnected call sites.

**Cost**: Small. One new generic class in `values.py`, one helper method on `Shortcut`, refactor of three helper functions in `vault_note_to_git.py`, update of two tests. No breaking changes.

**What it unlocks**: Named variables become traceable Python objects. The `describe_action` output starts surfacing typed variable references. Blocks become unit-testable in isolation (construct a fake `Var[str]("test")`, call the block, check what actions were added).

**Priority**: High. This is the most immediate return on investment because it directly addresses the silent iOS runtime failure mode (misspelled variable names) and gives the composition story a typed spine.

---

### Proposal 2 — `Annotated[ParamValue, SlotKind(...)]` slot metadata + emit-time coercion dispatch

**What**: Introduce slot-kind markers as `Annotated` metadata so that (a) `describe_action` surfaces the coercion contract to LLM authors, and (b) `_params()` implementations can delegate coercion to a shared dispatch rather than hardcoding `coerce_text_field` vs `coerce_value`.

**Concrete pilot** on three actions — `GetText`, `UseModel`, `FormatDate` — as the pattern:

```python
# src/shortcut_lib/schema/base.py — add slot markers:
from dataclasses import dataclass as _dc
@_dc(frozen=True)
class TextTokenSlot:
    """This parameter slot expects WFTextTokenString envelope."""
    wf_key: str

@_dc(frozen=True)
class ValueSlot:
    """This parameter slot accepts WFTextTokenAttachment or scalar."""
    wf_key: str

# type alias with slot metadata:
TextParam = Annotated[ParamValue, TextTokenSlot]
ValueParam = Annotated[ParamValue, ValueSlot]

# Coercion dispatch — replaces per-action hardcoding:
def emit_params(action: Action) -> dict[str, Any]:
    """Emit params using slot metadata from Annotated type hints."""
    hints = get_type_hints(type(action), include_extras=True)
    out = {}
    for f in fields(action):
        if f.name in {"uuid", "custom_output_name"}:
            continue
        value = getattr(action, f.name)
        if value is None:
            continue
        annotated_meta = get_args(hints.get(f.name, None))
        slot = next((m for m in annotated_meta if isinstance(m, (TextTokenSlot, ValueSlot))), None)
        if slot is None:
            out[f.name] = coerce_value(value)
        elif isinstance(slot, TextTokenSlot):
            out[slot.wf_key] = coerce_text_field(value)
        else:
            out[slot.wf_key] = coerce_value(value)
    return out
```

In `GetText`:

```python
# TODAY:
text: ParamValue = field(default="")
def _params(self):
    return {"WFTextActionText": coerce_text_field(self.text)}

# V2:
text: Annotated[ParamValue, TextTokenSlot("WFTextActionText")] = ""
# _params() can be eliminated or reduced to special-case logic
```

**Cost**: Medium. The slot-marker dataclasses and dispatch function are ~40 lines. Migrating 24 leaf actions to annotated fields is mechanical but time-consuming. The pilot on 3 actions should run first to validate the pattern before committing. Actions with complex `_params()` logic (e.g. `DownloadURL` with dict encoding) keep their `_params()` override; the dispatch is an opt-in simplification, not a mandate.

**What it unlocks**: `describe_action` can surface "this is a text-token-string slot" vs "this is a generic value slot" — the LLM author stops needing to know about `coerce_text_field` vs `coerce_value`. The envelope-wrapping bug class (FU-7's root cause) becomes structurally impossible to introduce in new actions because the dispatch handles it.

**Priority**: Medium. High value, but depends on the team committing to the annotation pattern. Don't do this under time pressure — a partial migration where half the actions use `Annotated` and half don't is worse than the status quo.

---

### Proposal 3 — Collapse `@register @dataclass` into `@action` using `dataclass_transform`

**What**: Introduce a single `@action` decorator that (a) calls `dataclass(frozen=True)` on the class, (b) registers the class by its identifier, (c) validates the identifier at class-definition time, (d) is annotated with `@dataclass_transform` so Pyright/mypy preserve the synthesized `__init__` signature. This eliminates the double-decorator smell, enforces frozen-by-default (addressing post-construction mutation), and makes the class-definition mistake (missing identifier) a static error.

**Concrete shape**:

```python
# src/shortcut_lib/schema/base.py — new decorator:
from typing import dataclass_transform

@dataclass_transform(field_specifiers=(field,), frozen_default=True)
def action(
    identifier: str,
    *,
    output: str = "",
) -> Callable[[type[_ActionT]], type[_ActionT]]:
    """Register an Action class by its Apple identifier.

    Applies @dataclass(frozen=True) and registers via the global registry.
    Validates that identifier is non-empty at decoration time.

    Example:
        @action("is.workflow.actions.gettext", output="Text")
        class GetText(Action):
            text: TextParam = ""
    """
    if not identifier:
        raise ValueError("@action requires a non-empty Apple identifier")
    def decorator(cls: type[_ActionT]) -> type[_ActionT]:
        cls.identifier = identifier
        if output:
            cls.default_output_name = output
        cls = dataclass(frozen=True)(cls)
        _REGISTRY[identifier] = cls
        return cls
    return decorator
```

Then every action becomes:

```python
# TODAY (24 actions look like this):
@register
@dataclass
class GetText(Action):
    identifier: ClassVar[str] = "is.workflow.actions.gettext"
    default_output_name: ClassVar[str] = "Text"
    text: ParamValue = field(default="")

# V2:
@action("is.workflow.actions.gettext", output="Text")
class GetText(Action):
    text: TextParam = ""
```

**Important caveat on `frozen=True`**: Several existing actions use mutable fields (`body: dict[str, Any] | None = None` on `DownloadURL`; the `target` mutation via `_bind_self` in `builder.py` on `RunWorkflow`). The `_bind_self` pattern directly mutates `action.target` after construction; this would break under frozen. The fix for `RunWorkflow` is to make `target` a constructor argument that's resolved at construction time (which the existing `B7+E1` task already plans — `Self` sentinel resolves at `add()` time by constructing a new `_BoundSelf`-carrying instance rather than mutating). After `B7+E1` lands, `RunWorkflow` can be frozen. `DownloadURL.body: dict` is a caller-supplied value, never mutated post-construction; frozen is safe.

**Cost**: Medium. Writing the decorator and its `dataclass_transform` annotation is ~30 lines. The mechanical migration of 24 actions is straightforward. The real cost is resolving the `RunWorkflow`/`_bind_self` mutation issue — but that's blocked on `B7+E1` anyway. Run this after `B7+E1`.

**What it unlocks**: A new action is three lines to define correctly. The LLM writing a new action can't forget `@dataclass` or `@register` — one decorator does both. Missing identifier becomes a hard error at import time. `frozen=True` by default eliminates the post-construction mutation footgun. The type checker sees the synthesized `__init__` correctly (no `# type: ignore` needed for action constructors). The `ClassVar[str]` lie is gone.

**Priority**: Medium, gated on `B7+E1`. The improvement is significant but there's no bug being fixed — it's a code quality and authoring ergonomics win. Do it as the first "V2 era" change after the current open blockers are closed, so the pattern is established before new actions are written.

---

## Closing note on scope

None of the three proposals require a full V2 rewrite. They're layered improvements that can be adopted incrementally:

- Proposal 1 (typed Var coupling) is additive and backward-compatible.
- Proposal 2 (Annotated slot metadata) can be piloted on 3 actions before full rollout.
- Proposal 3 (dataclass_transform + frozen) is a mechanical refactor gated on B7+E1.

The one change I'd argue against rushing is `Annotated` slot metadata as a wholesale migration — the pattern is right but the payoff is only full when the majority of actions use it. Pilot carefully, then sweep. The one change I'd argue for doing immediately, before any other V2 work, is the typed `Var[T]` returns from block functions. The stringly-typed named-variable coupling is the most active footgun in the current codebase.
