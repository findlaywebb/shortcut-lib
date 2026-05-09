# Review: `v15/model-photo-getters` — GetLastPhoto and GetLastScreenshot

**Branch:** `v15/model-photo-getters` (head: `50b26bc`)
**Files changed:** `src/shortcut_lib/schema/actions/get_last_photo.py` (+44),
`src/shortcut_lib/schema/actions/get_last_screenshot.py` (+41),
`tests/test_action_get_last_photo.py` (+66),
`tests/test_action_get_last_screenshot.py` (+70) — 221 lines total, all additive.
**Verdict:** APPROVE — correct, fully grounded, clean.

---

## What landed

Two typed action dataclasses added to the registry:

- `GetLastPhoto` (`is.workflow.actions.getlastphoto`) — fetches the most recent N photos
  from the device camera roll. Single public field: `count: int | None = None`. Writes
  `WFGetLatestPhotoCount` when `count` is not `None`; omits the key otherwise.
  `default_output_name` is `"Latest Photos"`.

- `GetLastScreenshot` (`is.workflow.actions.getlastscreenshot`) — same structure, same
  field, same key, different identifier and output name (`"Latest Screenshots"`).

Both use `@register` and are discoverable via `lookup()`. Neither branch adds any
dependencies or modifies shared infrastructure.

---

## Corpus verification

### Corpus count: confirmed 3 + 3 = 6

**GetLastPhoto — 3 appearances:**

| Sample | Appearance | WFGetLatestPhotoCount present? |
|---|---|---|
| `email_last_image.xml` | 1 | No (UUID + CustomOutputName only) |
| `dictionary.xml` | 1 | No (UUID only) |
| `dictionary.xml` | 2 | No (UUID only) |

**GetLastScreenshot — 3 appearances:**

| Sample | Appearance | WFGetLatestPhotoCount present? |
|---|---|---|
| `combine_screenshots_and_share.xml` | 1 | Yes — dynamic "Ask" token |
| `dictionary.xml` | 1 | No (UUID only) |
| `dictionary.xml` | 2 | No (UUID only) |

All 6 appearances independently verified from raw XML. Count is correct.

### Default-omission behaviour: confirmed

5 of 6 corpus appearances have no `WFGetLatestPhotoCount` key — only UUID (and in one
case `CustomOutputName`). The schemas correctly omit the key when `count is None`, which
faithfully reproduces the dominant wire form. The single non-default appearance
(`combine_screenshots_and_share.xml`) uses a dynamic "Ask" token rather than a plain
integer — this is not yet modelable as a simple `int` field, but it's the edge case, not
the default, and the docstring notes it.

The wire-format equivalence tests use real corpus UUIDs (the `email_last_image.xml` UUID
for photo, the `dictionary.xml` UUID for screenshot) and assert exact dict equality.
Both pass.

---

## Shared `WFGetLatestPhotoCount` key: confirmed and explained

This is the most notable wire-format quirk in the branch. `is.workflow.actions.getlastscreenshot`
uses the parameter key `WFGetLatestPhotoCount` — a key whose name contains "Photo" — not
`WFGetLatestScreenshotCount` or any screenshot-specific variant. This is not a modelling
choice; it is confirmed directly from corpus. The `combine_screenshots_and_share.xml`
sample shows `getlastscreenshot` emitting `WFGetLatestPhotoCount` in its params dict.

Both action docstrings call this out correctly: `GetLastPhoto` notes that the key was
confirmed via the sibling action in the screenshot sample, and `GetLastScreenshot`
confirms the key from the same source.

**Should this be tracked centrally?** Yes, once the wire-format-quirks doc exists (the
brief mentions it as a forthcoming branch). The entry should read: both
`getlastphoto` and `getlastscreenshot` share the single key `WFGetLatestPhotoCount` for
their count parameter — the screenshot action does not have its own key. Corpus evidence:
`combine_screenshots_and_share.xml`. Until that doc exists, the cross-references in
the action docstrings are sufficient.

---

## Test results

**New action tests: 14/14 passed.**

```
tests/test_action_get_last_photo.py     7/7  PASSED
tests/test_action_get_last_screenshot.py  7/7  PASSED
```

Coverage per action: identifier, default omits count, explicit count emitted, UUID
present, output name, registry lookup, wire-format equivalence. The suite is minimal but
complete for the surface area of these actions.

**`test_comment_wire_format` — pre-existing failure, branch is innocent.**

This test fails identically on both `main` and the worktree:

- `main`: `FAILED tests/test_wire_format_equivalence.py::test_comment_wire_format`
- Worktree: same failure, same assertion diff

The branch touches none of `Comment`, `coerce_text_field`, or the wire-format
equivalence test infrastructure. The diff is 100% additive. This failure pre-dates the
branch and is main's responsibility, not this one.

**Static analysis (branch files only):** ruff lint and ruff format both clean. `ty`
type check passes on both new action files. The one ruff finding across the repo
(`FURB110` in `builder.py`) is pre-existing and unrelated.

---

## Issues

None blocking. Two minor observations:

1. **`CustomOutputName` not modelled.** The `email_last_image.xml` appearance includes
   `CustomOutputName: "Last Photo"` alongside the UUID. This is a user-visible rename
   of the action's output and is not modelled (no `custom_output_name` field). This
   is consistent with the rest of the v15 series — no action in the branch models
   `CustomOutputName` — so it is not a gap unique to this PR. Worth one central issue
   rather than per-action noise.

2. **Dynamic token on `count` not covered.** The "Ask" token in
   `combine_screenshots_and_share.xml` is a `WFTextTokenAttachment` dynamic value, not
   a plain integer. The current `count: int | None` field can't represent it. This is
   a known limitation of the v15 schema surface (no `ParamValue` generalisation for
   count fields yet) and is not a regression — the field simply serialises integers
   correctly and leaves the dynamic case for a future pass.

Neither observation warrants blocking the merge.

---

## Merge recommendation

Merge. The implementation is correct, grounded in corpus, and fully tested. The shared
`WFGetLatestPhotoCount` quirk is properly documented in both action docstrings. The only
failing test is pre-existing on main. Static analysis is clean on all changed files.

When the wire-format-quirks doc branch arrives, add one entry: `getlastphoto` and
`getlastscreenshot` both use `WFGetLatestPhotoCount` — `combine_screenshots_and_share.xml`
is the primary evidence.
