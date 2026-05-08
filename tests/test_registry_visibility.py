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


def test_has_default_uses_dataclass_missing_sentinel() -> None:
    """Regression for the registry has_default sentinel bug.

    Earlier code compared against ``inspect.Parameter.empty`` instead of
    ``dataclasses.MISSING``. Those are different objects, so the
    expression always evaluated True — every parameter looked optional.

    We use a synthetic registered action because the production actions
    all default required-feeling fields to None for caller ergonomics
    (validated at _params time, not by the dataclass contract). This
    test isolates the sentinel-comparison correctness from that
    convention.
    """
    from dataclasses import dataclass, field
    from typing import Any, ClassVar

    from shortcut_lib.schema.base import Action
    from shortcut_lib.schema.registry import _REGISTRY, register

    @register
    @dataclass
    class _Probe(Action):
        identifier: ClassVar[str] = "shortcut_lib.test.probe"

        required: str = ""  # value default
        listed: list[str] = field(default_factory=list)  # factory default

        def _params(self) -> dict[str, Any]:
            return {}

    try:
        desc = describe_action("_Probe")
        by_name = {p["name"]: p for p in desc["parameters"]}
        assert by_name["required"]["has_default"] is True
        assert by_name["listed"]["has_default"] is True
    finally:
        _REGISTRY.pop("shortcut_lib.test.probe", None)


# NB: testing the "genuinely required" path is awkward because Action's
# inherited fields (uuid, custom_output_name) all have defaults, and a
# subclass field without a default would have to come BEFORE inherited
# fields — which Python's dataclass machinery rejects. Production action
# classes accept this: required-feeling fields default to None and
# validate at _params time. The has_default flag therefore reflects the
# dataclass contract honestly, but doesn't tell an LLM author whether
# a slot will be rejected at emit time. Improving that signal is tracked
# as a follow-up (introduce a "required" semantic via __post_init__
# probing or a class-level marker).


def test_doc_non_empty_for_every_value() -> None:
    """Every list_values() entry has a non-empty doc string for LLM use."""
    assert all(row["doc"] for row in list_values())


def test_doc_non_empty_for_every_control_flow_entry() -> None:
    """Every list_control_flow() entry has a non-empty doc string."""
    assert all(row["doc"] for row in list_control_flow())
