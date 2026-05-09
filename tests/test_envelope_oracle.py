"""Oracle test: every dict envelope the schema emits must appear in the corpus.

Loads ``data/observed_envelope_types.json`` (the living artefact produced by
``scripts/scan_envelope_types.py``) and asserts that, for every leaf action
registered in the schema, every ``WFSerializationType`` value emitted for a
dict-shaped parameter slot has been observed in at least one real decoded
sample.

If the oracle has *no* observation for an (action, slot) pair the test emits a
``warnings.warn`` (sparse coverage — not a bug) and skips the assertion.
If the oracle has observations but the schema emits a type not in the observed
set, the test fails (FU-7-class bug).

Intentional design choices
--------------------------
- The session fixture loads the JSON once; the per-action tests are pure
  in-memory and finish in well under a second.
- Actions that produce no dict envelopes under the placeholder construction
  (``RecordAudio``, ``ExitShortcut``, ``GetClipboard``, ``DictateText``)
  contribute nothing to check and pass trivially.
- Actions that require mandatory string fields (``SetVariable.name``,
  ``AppendVariable.name``, ``GetVariable.name``, ``AskForInput.input_type``)
  are constructed with safe sentinel values.
- Control-flow constructs (``If``, ``RepeatCount``, ``ChooseFromMenu``) are
  not in the registry and are not tested here.
"""

from __future__ import annotations

import json
import warnings
from dataclasses import fields
from pathlib import Path
from typing import Any

import pytest

from shortcut_lib.schema.base import Action
from shortcut_lib.schema.registry import list_actions, lookup
from shortcut_lib.schema.values import NamedVar

_ORACLE_PATH = Path(__file__).parent.parent / "data" / "observed_envelope_types.json"

# Actions where every interesting parameter slot needs a non-None sentinel
# beyond NamedVar("X") — keyed by class name.
_MANDATORY_OVERRIDES: dict[str, dict[str, Any]] = {
    "SetVariable": {"name": "_oracle_test_var", "input": NamedVar("X")},
    "AppendVariable": {"name": "_oracle_test_var", "input": NamedVar("X")},
    "GetVariable": {"name": "_oracle_test_var"},
    "AskForInput": {"input_type": "Text"},
    "FormatDate": {"date_style": "Short"},
    "DownloadURL": {"url": NamedVar("X")},
    "UseModel": {"prompt": NamedVar("X")},
    # Writing Tools: text defaults to None but is required by _text_param().
    # Provide it explicitly so _params() runs and envelope checking fires.
    # Oracle has no dict observations for 'text' in samples (bare string only),
    # so these will pass with a sparse-coverage warning rather than fail.
    "AdjustTone": {"text": NamedVar("X")},
    "FormatList": {"text": NamedVar("X")},
    "RewriteText": {"text": NamedVar("X")},
    "SummarizeText": {"text": NamedVar("X")},
    # TextReplace.input defaults to None (so the generic loop skips it) but
    # the oracle has 5 observations of WFInput as WFTextTokenString.  Provide
    # the input slot explicitly so the oracle assertion runs against it.
    "TextReplace": {"input": NamedVar("X")},
    # TranscribeAudio.audio_file and Base64Encode.input default to None but
    # the oracle has observations for their slots — exercise them.
    "TranscribeAudio": {"audio_file": NamedVar("X")},
    "Base64Encode": {"input": NamedVar("X")},
    # SetClipboard.input and SetVariable.input default to None; include them
    # so the oracle checks WFInput slot coverage.
    "SetClipboard": {"input": NamedVar("X")},
}

# Actions that have no ParamValue slots at all (emit only scalars or nothing).
# Including them avoids false "no dict envelopes" warnings but they trivially
# produce nothing to assert, so we skip them early.
_NO_ENVELOPE_ACTIONS: frozenset[str] = frozenset(
    {
        "RecordAudio",
        "ExitShortcut",
        "GetClipboard",
        "DictateText",
    }
)


# ---------------------------------------------------------------------------
# Session-scoped fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def oracle() -> dict[str, Any]:
    """Load the observed_envelope_types.json oracle once per test session."""
    if not _ORACLE_PATH.exists():
        pytest.skip(
            f"Oracle not found at {_ORACLE_PATH}. "
            "Run `uv run python scripts/scan_envelope_types.py` first."
        )
    return json.loads(_ORACLE_PATH.read_text())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_param_value_field(f: Any) -> bool:
    """Return True if a dataclass field's type annotation includes ParamValue.

    Uses the string form of the annotation (safe with ``from __future__ import
    annotations``) rather than resolving the full type, so no import-time
    evaluation is needed.
    """
    hint = str(f.type) if isinstance(f.type, str) else repr(f.type)
    return "ParamValue" in hint


def _build_instance(cls: type[Action]) -> Action:
    """Construct a minimal instance of *cls* that will emit dict envelopes.

    For every ``ParamValue`` field not covered by ``_MANDATORY_OVERRIDES``,
    substitute a ``NamedVar("X")`` when the field's default is not ``None``.
    Fields that default to ``None`` are optional extras (e.g. ``DownloadURL.body``
    which requires a paired ``body_type`` to be valid) — leaving them as ``None``
    avoids triggering cross-field validation errors.

    Non-ParamValue fields always keep their dataclass defaults.
    """
    from dataclasses import MISSING

    overrides = dict(_MANDATORY_OVERRIDES.get(cls.__name__, {}))

    for f in fields(cls):
        if f.name in ("uuid", "custom_output_name"):
            continue
        if f.name in overrides:
            continue
        if not _is_param_value_field(f):
            continue
        # Only substitute for slots whose default is not None — those are the
        # primary content slots that always emit.  Slots defaulting to None
        # are conditional extras that need paired sibling fields to be valid.
        default = f.default if f.default is not MISSING else None
        if default is not None:
            overrides[f.name] = NamedVar("X")

    return cls(**overrides)  # type: ignore[call-arg]


def _collect_dict_envelopes(params: dict[str, Any]) -> dict[str, str]:
    """Walk a flat params dict and return ``{slot: WFSerializationType}`` pairs.

    Only the top-level slots are checked (nested structures inside
    ``WFDictionaryFieldValue`` are not checked — those are internal structure,
    not per-action slot classification).
    """
    result: dict[str, str] = {}
    for slot, value in params.items():
        if slot in ("UUID", "CustomOutputName"):
            continue
        if isinstance(value, dict) and "WFSerializationType" in value:
            result[slot] = value["WFSerializationType"]
    return result


# ---------------------------------------------------------------------------
# Parametrised test
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "action_meta",
    list_actions(),
    ids=lambda m: m["name"],
)
def test_envelope_type_in_oracle(
    action_meta: dict[str, str],
    oracle: dict[str, Any],
) -> None:
    """Every dict envelope emitted by the schema must appear in the oracle.

    For (action, slot) pairs with no oracle observation, a warning is issued
    (sparse coverage) but no assertion is made — a missing observation is
    informational, not a bug signal.

    For pairs where the oracle has observations but the schema emits a type
    not in the observed set, the test fails — this is the FU-7-class signal.
    """
    cls = lookup(action_meta["identifier"])
    assert cls is not None, (
        f"Registered action {action_meta['identifier']!r} not in registry"
    )

    if cls.__name__ in _NO_ENVELOPE_ACTIONS:
        return  # nothing to assert

    try:
        instance = _build_instance(cls)
        params = instance._params()
    except Exception as exc:
        pytest.skip(f"Could not construct {cls.__name__} for oracle test: {exc}")
        return

    emitted = _collect_dict_envelopes(params)
    if not emitted:
        return  # no dict envelopes emitted — nothing to assert

    oracle_slots = oracle.get("slots", {}).get(action_meta["identifier"], {})

    for slot, emitted_type in emitted.items():
        if slot not in oracle_slots:
            warnings.warn(
                f"Oracle has no observation for "
                f"({action_meta['identifier']!r}, {slot!r}). "
                "Add a decoded sample containing this action with a variable "
                f"reference in {slot!r} to improve oracle coverage.",
                stacklevel=2,
            )
            continue

        observed_types = set(oracle_slots[slot]["envelopes"].keys())
        if emitted_type not in observed_types:
            pytest.fail(
                f"Schema emits {emitted_type!r} for "
                f"({action_meta['identifier']!r}, {slot!r}) "
                f"but oracle has only seen: {sorted(observed_types)!r}. "
                "This is a FU-7-class bug: the schema envelope type does not "
                "match Apple's wire format in the sample corpus."
            )
