"""Shared wire-format test helpers for normalisation and sample loading.

Extracted from ``tests/test_wire_format_equivalence.py`` so that every
per-action test file can import rather than copy these ~30 lines.

Public surface
--------------
load_sample(path)
    Load a decoded plist XML file and return its top-level dict.

find_action(workflow, identifier)
    Return the first action matching ``identifier`` or raise ``KeyError``.

strip_output_uuids(obj)
    Recursively strip ``OutputUUID`` from all nested dicts in-place.

normalise_action(action_dict)
    Deep-copy an action dict and strip non-deterministic fields so two
    action dicts are structurally comparable.

normalise_sequence(actions)
    Normalise a sequence of action dicts for control-flow comparison,
    additionally stripping ``GroupingIdentifier``.

find_action_sequence(workflow, head_identifier, mode0_index)
    Return the full multi-action block for a control-flow construct,
    from the mode-0 head to the matching mode-2 close (inclusive).

Keys stripped
-------------
- ``UUID`` — each schema-built instance gets a fresh UUID4.
- ``CustomOutputName`` — optional user label; irrelevant to structural format.
- ``OutputUUID`` — references other actions' UUIDs; stripped recursively.
- ``GroupingIdentifier`` — only in ``normalise_sequence``; the schema
  generates a fresh UUID4 for the grouping.
"""

from __future__ import annotations

import copy
import plistlib
from pathlib import Path
from typing import Any


def load_sample(path: Path) -> dict[str, Any]:
    """Load a decoded plist XML file and return its top-level dict.

    Args:
        path: Absolute path to a decoded ``.xml`` plist file.

    Returns:
        The top-level plist dictionary.
    """
    return plistlib.loads(path.read_bytes())


def find_action(
    workflow: dict[str, Any],
    identifier: str,
) -> dict[str, Any]:
    """Return the first action matching ``identifier`` or raise.

    Args:
        workflow: Top-level workflow dict (as returned by ``load_sample``).
        identifier: The ``WFWorkflowActionIdentifier`` string to search for.

    Returns:
        The first matching action dict.

    Raises:
        KeyError: If no action with ``identifier`` is found.
    """
    for action in workflow["WFWorkflowActions"]:
        if action["WFWorkflowActionIdentifier"] == identifier:
            return action
    raise KeyError(f"No action with identifier {identifier!r} in sample")


def strip_output_uuids(obj: Any) -> None:
    """Recursively strip ``OutputUUID`` from all dicts in-place.

    Args:
        obj: Any Python object; only dicts and lists are traversed.
    """
    if isinstance(obj, dict):
        obj.pop("OutputUUID", None)
        for v in obj.values():
            strip_output_uuids(v)
    elif isinstance(obj, list):
        for v in obj:
            strip_output_uuids(v)


def normalise_action(action_dict: dict[str, Any]) -> dict[str, Any]:
    """Strip non-deterministic fields so two action dicts are comparable.

    Removes from ``WFWorkflowActionParameters``:

    - ``UUID`` — each schema-built instance gets a fresh UUID4.
    - ``CustomOutputName`` — optional user label irrelevant to wire format.
    - ``OutputUUID`` (recursively) — references other actions' UUIDs which
      differ between schema-built and corpus sample copies.

    Args:
        action_dict: A single action dict as loaded from a decoded sample
            or returned by ``Action.to_action_dict()``.

    Returns:
        A deep-copied, normalised action dict.
    """
    out = copy.deepcopy(action_dict)
    params = out.get("WFWorkflowActionParameters", {})
    params.pop("UUID", None)
    params.pop("CustomOutputName", None)
    strip_output_uuids(params)
    return out


def normalise_sequence(
    actions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Normalise a sequence of action dicts for control-flow comparison.

    Strips ``UUID``, ``GroupingIdentifier``, and ``CustomOutputName`` from
    every action in the sequence, and strips ``OutputUUID`` from all nested
    attachments.  ``GroupingIdentifier`` is stripped because the schema
    generates a fresh UUID4 for the grouping, which differs from the sample's
    literal value.

    Args:
        actions: List of action dicts (e.g. the full sequence of a
            ``RepeatEach`` or ``If`` block).

    Returns:
        A new list of deep-copied, normalised action dicts.
    """
    out: list[dict[str, Any]] = []
    for action in actions:
        normalised = copy.deepcopy(action)
        params = normalised.get("WFWorkflowActionParameters", {})
        params.pop("UUID", None)
        params.pop("GroupingIdentifier", None)
        params.pop("CustomOutputName", None)
        strip_output_uuids(params)
        out.append(normalised)
    return out


def find_action_sequence(
    workflow: dict[str, Any],
    head_identifier: str,
    mode0_index: int,
) -> list[dict[str, Any]]:
    """Return the full multi-action sequence for a control-flow construct.

    Starts at ``mode0_index`` (the head with ``WFControlFlowMode=0``) and
    walks forward until the matching close (``WFControlFlowMode=2``) with
    the same ``GroupingIdentifier``.  The close action is included.

    Args:
        workflow: Top-level workflow dict (as returned by ``load_sample``).
        head_identifier: The ``WFWorkflowActionIdentifier`` of the
            control-flow head action (e.g.
            ``"is.workflow.actions.conditional"``).
        mode0_index: Index into ``workflow["WFWorkflowActions"]`` of the
            mode-0 head action.

    Returns:
        A list of action dicts from the head through the mode-2 close
        (inclusive).

    Raises:
        AssertionError: If the action at ``mode0_index`` does not match
            ``head_identifier``.
    """
    actions = workflow["WFWorkflowActions"]
    head = actions[mode0_index]
    assert head["WFWorkflowActionIdentifier"] == head_identifier
    gid = head["WFWorkflowActionParameters"]["GroupingIdentifier"]
    seq: list[dict[str, Any]] = [head]
    for j in range(mode0_index + 1, len(actions)):
        a = actions[j]
        seq.append(a)
        params = a.get("WFWorkflowActionParameters", {})
        if (
            a["WFWorkflowActionIdentifier"] == head_identifier
            and params.get("GroupingIdentifier") == gid
            and params.get("WFControlFlowMode") == 2
        ):
            break
    return seq
