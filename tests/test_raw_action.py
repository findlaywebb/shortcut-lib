"""Tests for RawAction — pass-through action for unmodelled identifiers.

Covers the UUID-asymmetry guard added in V1: ``.output()`` points at
``self.uuid``, but historically ``raw_params`` was emitted verbatim,
so a freshly-authored RawAction whose ``raw_params`` had no UUID
emitted an action that downstream references couldn't resolve. The
guard writes ``self.uuid`` into the emitted ``WFWorkflowActionParameters``.
"""

from __future__ import annotations

import pytest

from shortcut_lib.schema.base import RawAction, SchemaError


def test_raw_action_emits_self_uuid_when_raw_params_omits_it() -> None:
    """A fresh RawAction with empty raw_params still emits its dataclass UUID.

    Without this, ``raw.output()`` would carry a UUID the emitted action
    doesn't have, producing a dangling reference at iOS runtime.
    """
    raw = RawAction(raw_identifier="is.workflow.actions.example", raw_params={})
    emitted = raw.to_action_dict()
    assert emitted["WFWorkflowActionParameters"]["UUID"] == raw.uuid
    assert raw.output().uuid == raw.uuid


def test_raw_action_self_uuid_overrides_raw_params_uuid() -> None:
    """When raw_params has a different UUID, the dataclass UUID wins.

    self.uuid is the canonical handle for output() resolution; the
    emitted dict matches it so downstream references resolve cleanly.
    """
    raw = RawAction(
        uuid="DATA-CLASS-UUID",
        raw_identifier="is.workflow.actions.example",
        raw_params={"UUID": "OLD-PARAMS-UUID", "Foo": "bar"},
    )
    emitted_params = raw.to_action_dict()["WFWorkflowActionParameters"]
    assert emitted_params["UUID"] == "DATA-CLASS-UUID"
    assert emitted_params["Foo"] == "bar"


def test_raw_action_empty_uuid_preserves_wire_quirk() -> None:
    """A lifted RawAction whose source had no UUID round-trips with no UUID.

    Some sample actions (e.g. comment / dnd.set in start_pomodoro.xml)
    have no UUID in their params. ``Shortcut.from_workflow`` sets
    ``self.uuid=""`` for those. The emit must omit UUID — otherwise the
    lift round-trip gains an empty-string UUID that wasn't in the source.
    """
    raw = RawAction(
        uuid="",
        raw_identifier="is.workflow.actions.comment",
        raw_params={"WFCommentActionText": "no UUID in source"},
    )
    emitted_params = raw.to_action_dict()["WFWorkflowActionParameters"]
    assert "UUID" not in emitted_params


def test_raw_action_requires_identifier() -> None:
    """A RawAction without raw_identifier raises SchemaError on emit."""
    raw = RawAction(raw_identifier="", raw_params={"UUID": "x"})
    with pytest.raises(SchemaError, match="raw_identifier"):
        raw.to_action_dict()
