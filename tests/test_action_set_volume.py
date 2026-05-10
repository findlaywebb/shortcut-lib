"""Tests for SetVolume (is.workflow.actions.setvolume) action schema."""

from __future__ import annotations

import pytest

import shortcut_lib.schema.actions.set_volume  # noqa: F401 — trigger registration
from shortcut_lib.schema.actions.set_volume import SetVolume
from shortcut_lib.schema.base import SchemaError
from shortcut_lib.schema.registry import lookup
from shortcut_lib.schema.values import NamedVar

# ---------------------------------------------------------------------------
# Identifier / registry
# ---------------------------------------------------------------------------


def test_set_volume_identifier() -> None:
    """to_action_dict carries the Apple setvolume identifier."""
    action = SetVolume()
    d = action.to_action_dict()
    assert d["WFWorkflowActionIdentifier"] == "is.workflow.actions.setvolume"


def test_set_volume_registered() -> None:
    """SetVolume is discoverable in the registry by its identifier."""
    cls = lookup("is.workflow.actions.setvolume")
    assert cls is SetVolume


# ---------------------------------------------------------------------------
# Empty params — valid corpus shape (dictionary.xml, both appearances)
# ---------------------------------------------------------------------------


def test_set_volume_empty_params_valid() -> None:
    """No-arg constructor emits only UUID — matches dictionary.xml wire shape."""
    action = SetVolume()
    params = action.to_action_dict()["WFWorkflowActionParameters"]
    assert set(params.keys()) == {"UUID"}


def test_set_volume_none_omits_wfvolume_key() -> None:
    """volume=None (default) omits the WFVolume key."""
    params = SetVolume().to_action_dict()["WFWorkflowActionParameters"]
    assert "WFVolume" not in params


# ---------------------------------------------------------------------------
# Float volume values
# ---------------------------------------------------------------------------


def test_set_volume_float_zero() -> None:
    """volume=0.0 emits WFVolume: 0.0."""
    params = SetVolume(volume=0.0).to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFVolume"] == 0.0


def test_set_volume_float_half() -> None:
    """volume=0.5 emits WFVolume: 0.5."""
    params = SetVolume(volume=0.5).to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFVolume"] == 0.5


def test_set_volume_float_max() -> None:
    """volume=1.0 emits WFVolume: 1.0."""
    params = SetVolume(volume=1.0).to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFVolume"] == 1.0


def test_set_volume_float_out_of_range_high() -> None:
    """volume > 1.0 raises SchemaError."""
    with pytest.raises(SchemaError, match=r"\[0\.0, 1\.0\]"):
        SetVolume(volume=1.1)._params()


def test_set_volume_float_out_of_range_low() -> None:
    """volume < 0.0 raises SchemaError."""
    with pytest.raises(SchemaError, match=r"\[0\.0, 1\.0\]"):
        SetVolume(volume=-0.1)._params()


# ---------------------------------------------------------------------------
# Integer volume values (coerced to float)
# ---------------------------------------------------------------------------


def test_set_volume_int_zero_coerced_to_float() -> None:
    """volume=0 (int) is coerced to 0.0 (float) and emitted as WFVolume."""
    params = SetVolume(volume=0).to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFVolume"] == 0.0
    assert isinstance(params["WFVolume"], float)


def test_set_volume_int_one_coerced_to_float() -> None:
    """volume=1 (int) is coerced to 1.0 (float) and emitted as WFVolume."""
    params = SetVolume(volume=1).to_action_dict()["WFWorkflowActionParameters"]
    assert params["WFVolume"] == 1.0
    assert isinstance(params["WFVolume"], float)


def test_set_volume_int_out_of_range() -> None:
    """volume=2 (int) raises SchemaError."""
    with pytest.raises(SchemaError, match=r"\[0\.0, 1\.0\]"):
        SetVolume(volume=2)._params()


# ---------------------------------------------------------------------------
# Variable-reference volume
# ---------------------------------------------------------------------------


def test_set_volume_named_var_emitted_as_attachment() -> None:
    """volume= with a NamedVar emits WFVolume as WFTextTokenAttachment."""
    var = NamedVar("Volume Level")
    params = SetVolume(volume=var).to_action_dict()["WFWorkflowActionParameters"]
    assert "WFVolume" in params
    token = params["WFVolume"]
    assert token["WFSerializationType"] == "WFTextTokenAttachment"
    assert token["Value"]["Type"] == "Variable"
    assert token["Value"]["VariableName"] == "Volume Level"


# ---------------------------------------------------------------------------
# Wire-format equivalence vs corpus
# ---------------------------------------------------------------------------


def test_set_volume_wire_equivalence_empty_corpus_shape() -> None:
    """Reproduces the empty wire shape from dictionary.xml (both occurrences).

    Both corpus appearances carry <dict/> for WFWorkflowActionParameters,
    confirming that WFVolume is optional and the action is valid with no params.
    """
    action = SetVolume()
    d = action.to_action_dict()
    assert d["WFWorkflowActionIdentifier"] == "is.workflow.actions.setvolume"
    params = d["WFWorkflowActionParameters"]
    assert "WFVolume" not in params
    # UUID is always injected by base class.
    assert "UUID" in params
