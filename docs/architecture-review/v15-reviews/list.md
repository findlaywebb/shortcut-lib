# Review: v15/model-list — BuildList (`is.workflow.actions.list`)

**Branch:** `v15/model-list` (head `ab64eb0`)
**Reviewer:** Claude (automated, on behalf of Findlay)
**Date:** 2026-05-09

---

## 1. Verdict

Merge with one naming note to resolve (see §5). Everything else is solid. Wire format is confirmed, tests are exhaustive, docs meet the v1.0.0 bar, and the items-as-strings restriction is well-motivated and clearly signposted.

---

## 2. Test Result

All 13 tests pass. No linting, formatting, or type-check failures.

```
13 passed in 0.10s
prek: all hooks passed
```

---

## 3. What Landed

Two new files, 307 lines total:

- `src/shortcut_lib/schema/actions/list.py` — 125 lines. `BuildList` dataclass registered under `is.workflow.actions.list`. Single `items: list[str]` field, default empty. `_params()` returns `{}` for empty list, otherwise `{"WFItems": list(self.items)}`. Type guard raises `SchemaError` with an Append Variable hint for non-string items.
- `tests/test_action_list.py` — 182 lines. 13 tests covering: empty-list omission (default and explicit), single-item, multi-item order, full wire-format equivalence against `set_weekend_chores.xml`, SchemaError on Action/NamedVar/int, identifier, output name, registry, and output-reference (default and custom name).

---

## 4. Doc Quality Assessment — First Action Under v1.0.0 Criterion

**Rating: 4 / 5**

The module docstring is the star here — it carries the full prose load. It covers:

- **Apple display name and identifier** — both clearly stated in the first four lines.
- **One-line purpose** — "creates an ordered list of text values"; the `[]` constructor analogy is effective.
- **Wire format with inline XML samples** — this is genuinely excellent. The `set_weekend_chores.xml` snippet shows the `<array>` of `<string>` structure; the `dictionary.xml` snippet shows UUID-only when empty. Both are correctly labelled with their source file.
- **Quirks documented explicitly** — the `Quirks` section names both the empty-omission behaviour and the plain-strings-only constraint, and explains the "why" behind each.
- **Usage example** — present, imports shown, downstream intent (ChooseFromList, RepeatEach) stated.

The class docstring is leaner but appropriate — it restates the key restriction and delegates detail to the module level.

What costs the fifth point:

- The `Args:` block inside the class docstring uses Google style correctly but `items` skips the type; Google style includes the type in the arg line (`items (list[str]): ...`). It's a minor miss but relevant for a branch self-assessing against v1.0.0 documentation standards.
- The module-level `Parameters` section uses a NumPy-style layout (dashed underline, type on a separate line) while the class uses Google. The two conventions should agree. One or the other — pick Google throughout.

Overall: the substance is very good and clearly first-rate for this codebase. The two style inconsistencies are easy to fix post-merge if desired, and they don't impair understanding.

---

## 5. `BuildList` vs `List` — Naming Question

**Position: `BuildList` is justified here. Do not rename.**

The naming logic is different in kind from the `DateAction` case. `list` is a Python builtin. Shadowing it with a class named `List` would suppress type-checker warnings project-wide anywhere `list` is used in that scope, and would be invisible to the casual reader. By contrast, `date` is not a builtin; the concern in the `v15/model-event-helpers` rejection was about the `Action` suffix pattern being inconsistent, not about language keywords.

Looking at the existing codebase, naming precedent follows Apple's display name wherever it's safe: `Comment`, `Dictionary`, `ExitShortcut`, `FormatDate`, `GetText`, etc. The one exception that already exists is `writing_tools.py`'s `FormatList` class — which wraps a *different* action and uses a qualifier for the same reason `BuildList` does: `List` alone would be too generic or conflicting.

`BuildList` reads naturally. It makes the construction intent explicit (you are building a list, not consuming or filtering one), which is genuinely useful when `ChooseFromList` and `GetItemFromList` live in the same module namespace. No rename risk introduced.

---

## 6. Items-Must-Be-Strings Restriction — Sound or Arbitrary?

**Sound. The restriction faithfully reflects the wire format.**

The XML in `set_weekend_chores.xml` confirms it: `WFItems` is a plain `<array>` of `<string>` elements, with no type-code wrapper, no `WFTextTokenString` envelope, and no `WFSerializationType` key. It is structurally impossible to encode a variable reference or action output into this array at the plist level without changing the wire format Apple expects.

The SchemaError message is the right call over a silent coercion (e.g. `str(item)`) — users passing an Action object are almost certainly making a conceptual mistake, and the error redirects them to the correct pattern (Append Variable) rather than silently emitting wrong output. The error text names the bad type and points to the alternative.

One observation: the restriction is caught at `to_action_dict()` time, not at field assignment. That's consistent with the rest of the codebase (where `@dataclass` fields accept the annotation type at construction and validation runs lazily), so no issue — but it means `BuildList(items=[some_action])` won't fail until serialisation. The `ty:ignore` comments in the tests call this out correctly.

---

## 7. Issues

None blocking. Minor items for awareness:

- **Doc style inconsistency**: module-level `Parameters` block uses NumPy style; class-level `Args:` uses Google. Align to Google throughout. (Non-blocking; could be a follow-up.)
- **`items` arg missing type in class docstring**: `items (list[str]):` per Google convention. Trivial fix.
- **Lazy validation**: type guard fires at serialisation, not at construction. Consistent with codebase pattern, but worth documenting if the pattern is ever revisited.

---

## 8. Merge Recommendation

**Merge.** The implementation is correct, well-tested, and well-documented. The `BuildList` name is the right call. The items-as-strings restriction is accurate and appropriately enforced. Doc quality is the highest in the actions package — a strong template for subsequent actions under the v1.0.0 criterion. The two style-consistency nits can be addressed in a follow-up or inline before merge, but they do not block.
