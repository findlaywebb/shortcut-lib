"""Action registry — discoverability for the LLM-authoring user.

Each leaf-action class registers itself via ``@register``. Callers list
available actions and inspect their parameter signatures.
"""

from __future__ import annotations

import inspect
from dataclasses import fields
from typing import Any

from shortcut_lib.schema.base import Action

_REGISTRY: dict[str, type[Action]] = {}


def register(cls: type[Action]) -> type[Action]:
    """Class decorator — register an action class by its identifier."""
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

    params: list[dict[str, Any]] = []
    for f in fields(cls):
        if f.name in {"uuid", "custom_output_name"}:
            continue
        params.append(
            {
                "name": f.name,
                "type": _format_type(f.type),
                "has_default": f.default is not inspect.Parameter.empty
                or f.default_factory is not inspect.Parameter.empty,  # type: ignore[misc]
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
    if isinstance(t, str):
        return t
    return getattr(t, "__name__", repr(t))


def lookup(identifier: str) -> type[Action] | None:
    """Return the registered Action class for an identifier, or None."""
    return _REGISTRY.get(identifier)
