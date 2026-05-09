"""Consolidated structural validation for Apple Shortcuts workflow dicts.

``validate_workflow(workflow)`` runs every built-in validator and returns a
flat list of :class:`ValidationFinding` objects.  Consumers (MCP server,
audit CLI) call this instead of re-implementing individual checks.  The
workflow dict matches what ``Shortcut.to_workflow()`` emits and
``decode_file(...).workflow`` returns.

Each validator is a module-private function ``_validate_<name>(actions,
workflow, oracle) -> list[ValidationFinding]``; new validators register
with one line in ``validate_workflow``.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from shortcut_lib.schema.values import MAGIC_VAR_TYPE_NAMES

logger = logging.getLogger(__name__)

_ORACLE_PATH = (
    Path(__file__).parent.parent.parent / "data" / "observed_envelope_types.json"
)

# Magic-variable Type strings that are always in scope without a preceding
# SetVariable / AppendVariable.  Derived from ``values.py`` singletons so
# additions to the MagicVar catalogue propagate here automatically.
_MAGIC_VAR_TYPES: frozenset[str] = MAGIC_VAR_TYPE_NAMES

# SetVariable / AppendVariable identifiers — actions that bring a name into
# scope for later NamedVar references.
_SET_VAR_IDENTIFIERS: frozenset[str] = frozenset(
    {
        "is.workflow.actions.setvariable",
        "is.workflow.actions.appendvariable",
    }
)


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ValidationFinding:
    """A single finding from the structural validation pass.

    Args:
        severity: "error" means the workflow will likely misbehave or fail
            to import; "warning" means something unusual but possibly
            intentional; "info" means noteworthy but benign.
        code: Short stable identifier, e.g. ``"envelope-mismatch"``.
        message: Human / LLM-readable description of the finding.
        action_index: 0-based index in ``WFWorkflowActions``, if applicable.
        action_identifier: The WFWorkflowActionIdentifier of the flagged
            action, if applicable.
        parameter_key: The parameter slot that triggered the finding.
    """

    severity: Literal["error", "warning", "info"]
    code: str
    message: str
    action_index: int | None = None
    action_identifier: str | None = None
    parameter_key: str | None = None


# ---------------------------------------------------------------------------
# Oracle loader (cached at module level after first load)
# ---------------------------------------------------------------------------

_oracle_cache: dict[str, Any] | None = None


def _load_oracle() -> dict[str, Any]:
    """Load observed_envelope_types.json, caching after the first call."""
    global _oracle_cache
    if _oracle_cache is not None:
        return _oracle_cache
    if not _ORACLE_PATH.exists():
        logger.warning(
            "Envelope oracle not found at %s; envelope validators will be skipped. "
            "Run `uv run python scripts/scan_envelope_types.py` to generate it.",
            _ORACLE_PATH,
        )
        _oracle_cache = {}
        return _oracle_cache
    _oracle_cache = json.loads(_ORACLE_PATH.read_text())
    return _oracle_cache


# ---------------------------------------------------------------------------
# Tree-walker helpers
# ---------------------------------------------------------------------------


def _walk_values(value: Any) -> list[Any]:
    """Recursively collect all dict and list values in a parameter tree.

    Returns a flat list of every node (including intermediate containers) in
    depth-first order.  Used by validators that need to inspect every token.
    """
    results: list[Any] = []
    if isinstance(value, dict):
        results.append(value)
        for v in value.values():
            results.extend(_walk_values(v))
    elif isinstance(value, list):
        for item in value:
            results.extend(_walk_values(item))
    return results


def _walk_params(params: dict[str, Any]) -> list[Any]:
    """Walk all values in a params dict, excluding bookkeeping keys."""
    nodes: list[Any] = []
    for key, val in params.items():
        if key in ("UUID", "CustomOutputName"):
            continue
        nodes.extend(_walk_values(val))
    return nodes


# ---------------------------------------------------------------------------
# Validator 1: envelope-mismatch / unknown-envelope
# ---------------------------------------------------------------------------


def _validate_envelope(
    actions: list[dict[str, Any]],
    workflow: dict[str, Any],
    oracle: dict[str, Any],
) -> list[ValidationFinding]:
    """Flag envelope types that mismatch or are absent from the oracle.

    For each dict-shaped parameter slot that carries a ``WFSerializationType``
    key:

    - If the oracle has observations for (action, slot) but the observed type
      is not among them → ``envelope-mismatch`` (error).
    - If the oracle has *no* observations anywhere for this type value →
      ``unknown-envelope`` (info).  This is rare (custom/new action types)
      and is purely informational.
    - If the oracle has observations for a *different* slot on the same action
      but not this slot → a sparse-coverage gap; we emit nothing (same
      behaviour as the oracle test).
    """
    oracle_slots: dict[str, Any] = oracle.get("slots", {})
    findings: list[ValidationFinding] = []

    for idx, action in enumerate(actions):
        action_id: str = action.get("WFWorkflowActionIdentifier", "")
        params: dict[str, Any] = action.get("WFWorkflowActionParameters") or {}

        for slot_key, slot_val in params.items():
            if slot_key in ("UUID", "CustomOutputName"):
                continue
            if not isinstance(slot_val, dict):
                continue
            wf_type = slot_val.get("WFSerializationType")
            if wf_type is None:
                continue

            action_oracle = oracle_slots.get(action_id, {})
            slot_oracle = action_oracle.get(slot_key)

            if slot_oracle is not None:
                # Oracle has observations for this (action, slot) pair.
                observed_types = set(slot_oracle.get("envelopes", {}).keys())
                if wf_type not in observed_types:
                    findings.append(
                        ValidationFinding(
                            severity="error",
                            code="envelope-mismatch",
                            message=(
                                f"Parameter slot {slot_key!r} on action "
                                f"{action_id!r} carries WFSerializationType "
                                f"{wf_type!r} but the oracle has only ever seen: "
                                f"{sorted(observed_types)!r}.  This likely reflects "
                                f"an incorrect envelope type that will cause "
                                f"the parameter to read as empty at runtime."
                            ),
                            action_index=idx,
                            action_identifier=action_id,
                            parameter_key=slot_key,
                        )
                    )
            else:
                # No oracle observation for this (action, slot) pair.
                # Check if the WFSerializationType value itself is unknown
                # across the entire oracle (truly novel type).
                all_observed_types: set[str] = set()
                for a_slots in oracle_slots.values():
                    for s_data in a_slots.values():
                        all_observed_types.update(s_data.get("envelopes", {}).keys())
                if all_observed_types and wf_type not in all_observed_types:
                    findings.append(
                        ValidationFinding(
                            severity="info",
                            code="unknown-envelope",
                            message=(
                                f"Parameter slot {slot_key!r} on action "
                                f"{action_id!r} carries WFSerializationType "
                                f"{wf_type!r} which has never been observed in "
                                f"the sample corpus.  This may be a new Apple "
                                f"type or a novel third-party action."
                            ),
                            action_index=idx,
                            action_identifier=action_id,
                            parameter_key=slot_key,
                        )
                    )

    return findings


# ---------------------------------------------------------------------------
# Validator 2: variable-not-set
# ---------------------------------------------------------------------------


def _validate_variable_not_set(
    actions: list[dict[str, Any]],
    workflow: dict[str, Any],
    oracle: dict[str, Any],
) -> list[ValidationFinding]:
    """Flag NamedVar references whose name has not been set by a prior action.

    Walks the action list linearly, accumulating the set of names bound by
    SetVariable / AppendVariable as it goes.  Each action's parameter tree is
    checked against names bound *strictly before* that action — meaning a
    reference at action N to a name first set at action N+K is flagged as a
    use-before-set error.

    iOS resolves named-variable references in sequential execution order; a
    variable that is set later in the flat list is empty at the point of use,
    producing silent data-loss at runtime.

    Magic variables (CurrentDate, Clipboard, Ask, ShortcutInput, RepeatItem,
    RepeatIndex) are always in scope and are never flagged.
    """
    bound_names: set[str] = set()
    findings: list[ValidationFinding] = []
    seen_refs: set[tuple[int, str]] = set()  # (action_index, var_name) dedup

    for idx, action in enumerate(actions):
        action_id = action.get("WFWorkflowActionIdentifier", "")
        params = action.get("WFWorkflowActionParameters") or {}

        # Check references BEFORE updating bound_names for this action so
        # that a SetVariable at index N does not satisfy its own references.
        for node in _walk_params(params):
            if not isinstance(node, dict):
                continue
            if node.get("Type") != "Variable":
                continue
            var_name = node.get("VariableName")
            if not isinstance(var_name, str) or not var_name:
                continue
            if var_name in bound_names or var_name in _MAGIC_VAR_TYPES:
                continue
            dedup_key = (idx, var_name)
            if dedup_key in seen_refs:
                continue
            seen_refs.add(dedup_key)
            findings.append(
                ValidationFinding(
                    severity="error",
                    code="variable-not-set",
                    message=(
                        f"Action at index {idx} ({action_id!r}) references "
                        f"variable {var_name!r} but no SetVariable or "
                        f"AppendVariable action earlier in the workflow assigns "
                        f"that name.  The variable will be empty at runtime."
                    ),
                    action_index=idx,
                    action_identifier=action_id,
                )
            )

        # Now register any name this action binds for subsequent actions.
        if action_id in _SET_VAR_IDENTIFIERS:
            var_name = params.get("WFVariableName")
            if isinstance(var_name, str) and var_name:
                bound_names.add(var_name)

    return findings


# ---------------------------------------------------------------------------
# Validator 3: output-uuid-orphan
# ---------------------------------------------------------------------------


def _validate_output_uuid_orphan(
    actions: list[dict[str, Any]],
    workflow: dict[str, Any],
    oracle: dict[str, Any],
) -> list[ValidationFinding]:
    """Flag ActionOutput references whose UUID doesn't match a prior action.

    Walks every token in every action's parameters looking for::

        {"Type": "ActionOutput", "OutputUUID": <uuid>, ...}

    The UUID is checked against the set of UUIDs from actions *earlier in the
    flat list* (forward references are invalid — iOS resolves output references
    strictly in execution order).  Self-referential UUIDs (same action) are
    also flagged.

    Actions whose parameters dict has no UUID key are skipped for the "seen
    so far" set (they are ``RawAction``s lifted from samples that carried no
    UUID in the plist).
    """
    seen_uuids: set[str] = set()
    findings: list[ValidationFinding] = []
    seen_refs: set[tuple[int, str]] = set()  # (action_index, uuid) dedup

    for idx, action in enumerate(actions):
        action_id = action.get("WFWorkflowActionIdentifier", "")
        params = action.get("WFWorkflowActionParameters") or {}

        for node in _walk_params(params):
            if not isinstance(node, dict):
                continue
            if node.get("Type") != "ActionOutput":
                continue
            ref_uuid = node.get("OutputUUID")
            if not isinstance(ref_uuid, str) or not ref_uuid:
                continue
            if ref_uuid in seen_uuids:
                continue  # valid back-reference
            dedup_key = (idx, ref_uuid)
            if dedup_key in seen_refs:
                continue
            seen_refs.add(dedup_key)
            findings.append(
                ValidationFinding(
                    severity="error",
                    code="output-uuid-orphan",
                    message=(
                        f"Action at index {idx} ({action_id!r}) references "
                        f"OutputUUID {ref_uuid!r} but no earlier action in "
                        f"this workflow has that UUID.  The reference will be "
                        f"unresolvable at runtime."
                    ),
                    action_index=idx,
                    action_identifier=action_id,
                )
            )

        # Register this action's UUID AFTER checking its references so
        # self-referential UUIDs are also flagged.
        own_uuid = params.get("UUID")
        if isinstance(own_uuid, str) and own_uuid:
            seen_uuids.add(own_uuid)

    return findings


# ---------------------------------------------------------------------------
# Validator 4: import-question-action-index-out-of-range
# ---------------------------------------------------------------------------


def _validate_import_question_index(
    actions: list[dict[str, Any]],
    workflow: dict[str, Any],
    oracle: dict[str, Any],
) -> list[ValidationFinding]:
    """Flag WFWorkflowImportQuestions entries with out-of-range ActionIndex.

    Each entry in ``WFWorkflowImportQuestions`` must carry an ``ActionIndex``
    that is a valid 0-based index into ``WFWorkflowActions``.  An index
    equal to ``len(actions)`` or greater (or negative) is out of range and
    the setup prompt will silently fail to populate the targeted action on
    import.
    """
    questions = workflow.get("WFWorkflowImportQuestions") or []
    n_actions = len(actions)
    findings: list[ValidationFinding] = []

    for q_idx, question in enumerate(questions):
        action_index = question.get("ActionIndex")
        if action_index is None:
            findings.append(
                ValidationFinding(
                    severity="error",
                    code="import-question-action-index-out-of-range",
                    message=(
                        f"WFWorkflowImportQuestions[{q_idx}] is missing "
                        f"ActionIndex.  The setup prompt will not target any "
                        f"action on import."
                    ),
                )
            )
        elif not isinstance(action_index, int) or not (0 <= action_index < n_actions):
            findings.append(
                ValidationFinding(
                    severity="error",
                    code="import-question-action-index-out-of-range",
                    message=(
                        f"WFWorkflowImportQuestions[{q_idx}] has ActionIndex "
                        f"{action_index!r} which is outside the valid range "
                        f"[0, {n_actions}).  The setup prompt will silently "
                        f"fail to populate its target action on import."
                    ),
                )
            )

    return findings


# ---------------------------------------------------------------------------
# Validator registry and entry point
# ---------------------------------------------------------------------------

# Validators run in this order.  Each takes (actions, workflow, oracle) and
# returns list[ValidationFinding].
_VALIDATORS = [
    _validate_envelope,
    _validate_variable_not_set,
    _validate_output_uuid_orphan,
    _validate_import_question_index,
]


def validate_workflow(workflow: dict[str, Any]) -> list[ValidationFinding]:
    """Run every available structural validator over the workflow dict.

    The workflow dict is the same shape as what ``Shortcut.to_workflow()``
    emits and ``decode_file(...).workflow`` returns.  Validators:

    - ``envelope-mismatch``: each parameter slot's WFSerializationType must
      appear in the observed-envelopes oracle for that (action, slot).
    - ``unknown-envelope``: parameter slots with WFSerializationType values
      the oracle has never seen anywhere — flagged as info (informational).
    - ``variable-not-set``: any NamedVar / variable reference whose name has
      no SetVariable upstream raises an error.
    - ``output-uuid-orphan``: any ActionOutput reference whose OutputUUID
      doesn't match an action's UUID earlier in the flow.
    - ``import-question-action-index-out-of-range``: ActionIndex in
      WFWorkflowImportQuestions outside ``[0, len(actions))``.

    Args:
        workflow: A decoded ``WFWorkflow*`` dict — typically from
            ``Shortcut.to_workflow()`` or ``decode_file(...).workflow``.

    Returns:
        A list of :class:`ValidationFinding` objects, sorted by
        ``(action_index, code)`` for stable output.  An empty list means no
        issues were found at the structural layer.
    """
    actions: list[dict[str, Any]] = workflow.get("WFWorkflowActions") or []
    oracle = _load_oracle()

    all_findings: list[ValidationFinding] = []
    for validator in _VALIDATORS:
        try:
            all_findings.extend(validator(actions, workflow, oracle))
        except Exception:
            logger.exception("Validator %s raised unexpectedly", validator.__name__)

    # Stable sort: action_index (None sorts last via sentinel), then code.
    all_findings.sort(
        key=lambda f: (f.action_index if f.action_index is not None else 2**31, f.code)
    )
    return all_findings
