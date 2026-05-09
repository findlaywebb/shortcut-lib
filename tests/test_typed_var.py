"""Tests for the typed variable handle returned by ``Shortcut.set``.

The point of the typed handle is that the variable's name lives on a
Python identifier — a typo at the use site becomes a NameError caught by
the type checker, not a silent empty value at iOS runtime. These tests
pin the wire-format behaviour and the round-trip through the schema.
"""

from __future__ import annotations

from shortcut_lib.builder import Shortcut
from shortcut_lib.schema import NamedVar, Text
from shortcut_lib.schema.actions.get_text import GetText
from shortcut_lib.schema.actions.show_notification import ShowNotification


def test_set_returns_named_var_handle() -> None:
    """``Shortcut.set`` adds a SetVariable action and returns a NamedVar."""
    s = Shortcut(name="t", surfaces=[])
    src = s.add(GetText(text="hello"))
    ref = s.set("Greeting", src)

    assert isinstance(ref, NamedVar)
    assert ref.name == "Greeting"
    # The SetVariable was actually added.
    assert len(s.actions) == 2
    assert s.actions[1].identifier == "is.workflow.actions.setvariable"


def test_set_handle_round_trips_to_named_var_wire_format() -> None:
    """Using the handle in a downstream action emits NamedVar's wire shape."""
    s = Shortcut(name="t", surfaces=[])
    src = s.add(GetText(text="hello"))
    greeting = s.set("Greeting", src)

    notif = s.add(ShowNotification(body=Text("Hi {g}", substitutions={"g": greeting})))
    body = notif.to_action_dict()["WFWorkflowActionParameters"][
        "WFNotificationActionBody"
    ]
    assert body["WFSerializationType"] == "WFTextTokenString"
    # "Hi " is 3 UTF-16 units; the {g} placeholder lands at offset 3.
    attachments = body["Value"]["attachmentsByRange"]
    assert list(attachments) == ["{3, 1}"]
    assert attachments["{3, 1}"] == {"VariableName": "Greeting", "Type": "Variable"}


def test_handle_equivalent_to_named_var_direct_construction() -> None:
    """``s.set("X", v)`` and ``s.add(SetVariable…); NamedVar("X")`` agree."""
    a = Shortcut(name="a", surfaces=[])
    src_a = a.add(GetText(text="x"))
    handle = a.set("Same", src_a)

    b = Shortcut(name="b", surfaces=[])
    src_b = b.add(GetText(text="x"))
    from shortcut_lib.schema.actions.set_variable import SetVariable

    b.add(SetVariable(name="Same", input=src_b))
    direct = NamedVar("Same")

    assert handle.to_param() == direct.to_param()
    assert handle.to_token() == direct.to_token()


def test_named_var_generic_default_is_any() -> None:
    """``NamedVar("X")`` constructs without a type argument (T defaults to Any)."""
    # No syntax error / runtime error from omitting the type parameter.
    v = NamedVar("X")
    assert v.name == "X"


def test_named_var_generic_subscript_runs() -> None:
    """``NamedVar[str]("X")`` is callable; the type parameter is informational."""
    # PEP 695 / PEP 696: subscripting a generic class returns a type alias
    # but instantiation through ``NamedVar(...)`` is the supported runtime path.
    # Here we just check that referencing ``NamedVar[str]`` doesn't raise.
    alias = NamedVar[str]
    assert alias is not None
    # The instance constructed via the underlying class is unchanged in shape.
    v: NamedVar[str] = NamedVar("X")
    assert v.name == "X"
