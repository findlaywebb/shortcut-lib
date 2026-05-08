"""Registry visibility for control-flow and values (P4)."""

from __future__ import annotations

from shortcut_lib.schema import (
    describe_action,
    list_control_flow,
    list_values,
)


def test_list_values_includes_core_types() -> None:
    names = {row["name"] for row in list_values()}
    assert "Output" in names
    assert "NamedVar" in names
    assert "Text" in names
    assert "Quantity" in names


def test_list_control_flow_includes_all() -> None:
    names = {row["name"] for row in list_control_flow()}
    assert names >= {"If", "RepeatCount", "RepeatEach", "ChooseFromMenu", "RunWorkflow"}


def test_describe_action_shows_real_types() -> None:
    """get_type_hints resolves str annotations to concrete types."""
    desc = describe_action("DownloadURL")
    by_name = {p["name"]: p for p in desc["parameters"]}
    assert by_name["method"]["type"] == "str"
    # headers should be a generic alias, not bare "Any"
    assert "dict" in by_name["headers"]["type"]
    assert "None" in by_name["headers"]["type"]


def test_describe_action_unknown_raises() -> None:
    import pytest

    with pytest.raises(KeyError):
        describe_action("NoSuchActionEverInExistence")
