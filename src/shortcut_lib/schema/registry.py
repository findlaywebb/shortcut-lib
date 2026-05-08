"""Action registry — discoverability for the LLM-authoring user.

Each leaf-action class registers itself via ``@register``. Callers list
available actions and inspect their parameter signatures.

Control-flow constructs (``If``, ``RepeatEach``, etc.) and value types
(``Text``, ``NamedVar``, …) aren't auto-registered — they're not leaf
actions — but are available via :func:`list_control_flow` and
:func:`list_values` for runtime discovery.
"""

from __future__ import annotations

import inspect
import typing
from dataclasses import MISSING, fields
from typing import Any

from shortcut_lib.schema.base import Action

_REGISTRY: dict[str, type[Action]] = {}


def register[T: Action](cls: type[T]) -> type[T]:
    """Class decorator — register an action class by its identifier.

    Parametrised over the concrete subclass so type checkers preserve
    the dataclass-generated ``__init__`` on call sites (e.g.
    ``GetText(text="…")``) instead of widening to ``type[Action]``.
    """
    if not cls.identifier:
        raise ValueError(
            f"{cls.__name__} cannot be registered without a class-level `identifier`"
        )
    if cls.identifier in _REGISTRY and _REGISTRY[cls.identifier] is not cls:
        raise ValueError(
            f"{cls.identifier} already registered to {_REGISTRY[cls.identifier].__name__}"
        )
    _REGISTRY[cls.identifier] = cls
    return cls


def list_actions() -> list[dict[str, str]]:
    """Return a sorted list of registered actions as ``[{name, identifier, doc}]``."""
    out: list[dict[str, str]] = []
    for ident, cls in sorted(_REGISTRY.items()):
        out.append(
            {
                "name": cls.__name__,
                "identifier": ident,
                "doc": (cls.__doc__ or "").strip().splitlines()[0]
                if cls.__doc__
                else "",
            }
        )
    return out


def describe_action(name_or_identifier: str) -> dict[str, Any]:
    """Return a structured description of one registered action.

    Looks up by ``WFWorkflowActionIdentifier`` first, then by class name.
    Resolves parameter types via :func:`typing.get_type_hints` so forward
    references and ``from __future__ import annotations`` work as expected.

    Raises :class:`KeyError` if not found.
    """
    cls = _REGISTRY.get(name_or_identifier)
    if cls is None:
        for candidate in _REGISTRY.values():
            if candidate.__name__ == name_or_identifier:
                cls = candidate
                break
    if cls is None:
        raise KeyError(f"no registered action: {name_or_identifier!r}")

    try:
        hints = typing.get_type_hints(cls, include_extras=False)
    except (NameError, AttributeError, TypeError):
        hints = {}

    params: list[dict[str, Any]] = []
    for f in fields(cls):
        if f.name in {"uuid", "custom_output_name"}:
            continue
        resolved = hints.get(f.name, f.type)
        # NB: dataclass fields use ``dataclasses.MISSING`` as the
        # "no default" sentinel, NOT ``inspect.Parameter.empty``. The
        # earlier comparison was always True, so every parameter looked
        # optional to the LLM author — including required slots like
        # DownloadURL.url.
        has_default = f.default is not MISSING or f.default_factory is not MISSING
        params.append(
            {
                "name": f.name,
                "type": _format_type(resolved),
                "has_default": has_default,
            }
        )
    return {
        "name": cls.__name__,
        "identifier": cls.identifier,
        "doc": inspect.getdoc(cls) or "",
        "default_output_name": cls.default_output_name,
        "parameters": params,
    }


def _format_type(t: Any) -> str:
    """Render a type annotation as a short, readable string."""
    if isinstance(t, str):
        return t
    if t is type(None):
        return "None"
    name = getattr(t, "__name__", None)
    if name:
        # Handle generic aliases like list[str] / dict[str, Any]
        args = typing.get_args(t)
        if args:
            inner = ", ".join(_format_type(a) for a in args)
            return f"{name}[{inner}]"
        return name
    # Handle Union / Optional / X | Y
    args = typing.get_args(t)
    if args:
        return " | ".join(_format_type(a) for a in args)
    return repr(t)


def list_values() -> list[dict[str, str]]:
    """Return the value classes available for embedding in action params.

    These aren't actions — they're the data primitives Claude reaches for
    when filling action parameters: variable references, magic variables,
    templated strings, typed value containers.
    """
    from shortcut_lib.schema import values as v

    classes: list[type[Any]] = [
        v.Output,
        v.NamedVar,
        v.MagicVar,
        v.Text,
        v.Quantity,
        v.TimeOffset,
    ]
    rows: list[dict[str, str]] = [
        {"name": cls.__name__, "doc": _first_doc_line(cls)} for cls in classes
    ]
    rows.append(
        {
            "name": "CurrentDate / Clipboard / Ask / ShortcutInput / RepeatItem / RepeatIndex",
            "doc": "Module-level magic-variable singletons; pass directly anywhere a value is accepted.",
        }
    )
    return rows


def list_control_flow() -> list[dict[str, str]]:
    """Return control-flow constructs (If, RepeatEach, RepeatCount, ChooseFromMenu)."""
    from shortcut_lib.schema import compose, control

    classes: list[type[Any]] = [
        control.If,
        control.RepeatCount,
        control.RepeatEach,
        control.ChooseFromMenu,
        compose.RunWorkflow,
    ]
    return [{"name": cls.__name__, "doc": _first_doc_line(cls)} for cls in classes]


def _first_doc_line(cls: type) -> str:
    doc = inspect.getdoc(cls) or ""
    return doc.splitlines()[0] if doc else ""


def lookup(identifier: str) -> type[Action] | None:
    """Return the registered Action class for an identifier, or None."""
    return _REGISTRY.get(identifier)
