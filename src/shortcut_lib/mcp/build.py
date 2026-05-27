"""Compile a :class:`ShortcutSpec` to a typed :class:`Shortcut` and sign it.

The compiler walks each ``ActionSpec``, resolves ``${ref}`` substitutions
into the right wire-format shape (single-attachment variable reference for
pure refs, templated :class:`Text` for interleaved strings), instantiates
the registered Action class, and adds it to the builder. The result is a
signed ``.shortcut`` file at the configured output directory.

All errors raised here are :class:`SpecCompileError` and carry a recovery
prompt (what went wrong, what to inspect next) — they're surfaced verbatim
to the calling agent.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import shortcut_lib.schema  # noqa: F401  — triggers action auto-registration
from shortcut_lib.builder import Shortcut
from shortcut_lib.encode import SignMode
from shortcut_lib.mcp.spec import ActionSpec, ShortcutSpec, find_refs, pure_ref
from shortcut_lib.schema.base import Action
from shortcut_lib.schema.registry import _REGISTRY, lookup
from shortcut_lib.schema.values import Text

_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9 _-]+")


class SpecCompileError(ValueError):
    """Raised when a ShortcutSpec can't be compiled.

    The message is written to be read by an agent and is safe to surface
    verbatim — it states what went wrong and what tool to call next.
    """


def _resolve_action_class(type_name: str) -> type[Action]:
    """Look up an Action class by identifier or class name.

    Tries the registry's identifier index first (O(1)); falls back to a
    linear scan of class names. Raises :class:`SpecCompileError` with a
    recovery prompt if no match exists.
    """
    cls = lookup(type_name)
    if cls is not None:
        return cls
    for candidate in _REGISTRY.values():
        if candidate.__name__ == type_name:
            return candidate
    raise SpecCompileError(
        f"Unknown action type {type_name!r}. "
        f"Call shortcut_list_actions(query={type_name[:16]!r}) to find "
        f"candidates, or shortcut_list_actions() for the full registry."
    )


def _substitute(value: Any, refs: dict[str, Action], path: str) -> Any:
    """Replace ``${ref}`` occurrences inside ``value`` with Action handles.

    Args:
        value: A raw parameter value (scalar, list, dict, or string).
        refs: Mapping of ``ref`` names to already-added Action instances.
        path: Dotted parameter path used in error messages.

    Returns:
        The substituted value. Pure ``${ref}`` strings become the Action
        handle (the schema layer coerces it to a variable reference on
        emit); interleaved strings become a :class:`Text` value.
    """
    if isinstance(value, str):
        pure = pure_ref(value)
        if pure is not None:
            if pure not in refs:
                raise SpecCompileError(
                    f"{path}: ${{{pure}}} references an unknown ref. "
                    f"Available refs at this point: {sorted(refs) or '(none)'}. "
                    f"Add an earlier action with ref={pure!r}."
                )
            return refs[pure]
        names = find_refs(value)
        if not names:
            return value
        substitutions: dict[str, Any] = {}
        for name in names:
            if name not in refs:
                raise SpecCompileError(
                    f"{path}: ${{{name}}} references an unknown ref. "
                    f"Available refs at this point: {sorted(refs) or '(none)'}."
                )
            substitutions[name] = refs[name]
        template = _replace_refs_with_braces(value)
        return Text(template=template, substitutions=substitutions)
    if isinstance(value, list):
        return [_substitute(v, refs, f"{path}[{i}]") for i, v in enumerate(value)]
    if isinstance(value, dict):
        return {k: _substitute(v, refs, f"{path}.{k}") for k, v in value.items()}
    return value


def _replace_refs_with_braces(template: str) -> str:
    """Rewrite ``${name}`` → ``{name}`` for :class:`Text` template syntax."""
    from shortcut_lib.mcp.spec import REF_PATTERN

    return REF_PATTERN.sub(lambda m: "{" + m.group(1) + "}", template)


def compile_spec(spec: ShortcutSpec) -> Shortcut:
    """Compile a validated :class:`ShortcutSpec` into a :class:`Shortcut`.

    Does not sign or write — call :func:`build_shortcut` for that, or
    invoke :meth:`Shortcut.save_signed` on the result.
    """
    shortcut = Shortcut(
        name=spec.name,
        surfaces=list(spec.surfaces),
        min_client=spec.min_client,
        accepted_input=list(spec.accepted_input),
        output_classes=list(spec.output_classes),
    )
    refs: dict[str, Action] = {}
    for idx, action_spec in enumerate(spec.actions):
        instance = _compile_action(action_spec, refs, idx)
        shortcut.add(instance)
        if action_spec.ref is not None:
            if action_spec.ref in refs:
                raise SpecCompileError(
                    f"actions[{idx}]: duplicate ref {action_spec.ref!r}. "
                    f"Each ref must be unique within a shortcut."
                )
            refs[action_spec.ref] = instance
    return shortcut


def _compile_action(
    action_spec: ActionSpec,
    refs: dict[str, Action],
    idx: int,
) -> Action:
    cls = _resolve_action_class(action_spec.type)
    resolved = _substitute(action_spec.params, refs, path=f"actions[{idx}].params")
    if not isinstance(resolved, dict):
        raise SpecCompileError(
            f"actions[{idx}].params must be an object, got {type(resolved).__name__}."
        )
    try:
        instance = cls(**resolved)
    except TypeError as exc:
        raise SpecCompileError(
            f"actions[{idx}] ({cls.__name__}): {exc}. "
            f"Call shortcut_get_action_schema({cls.__name__!r}) to see "
            f"accepted parameters."
        ) from exc
    if action_spec.custom_output_name is not None:
        instance.custom_output_name = action_spec.custom_output_name
    return instance


def _safe_filename(name: str) -> str:
    """Return a filesystem-safe filename derived from ``name``.

    Strips characters outside ``[A-Za-z0-9._ -]``; trims whitespace; falls
    back to ``"Untitled"`` if nothing survives. Matches Apple's filename
    conventions (spaces are fine, special chars are not).
    """
    cleaned = _SAFE_FILENAME_RE.sub("", name).strip()
    return cleaned or "Untitled"


def build_shortcut(
    spec: ShortcutSpec,
    output_dir: Path,
    *,
    sign_mode: SignMode = "anyone",
) -> dict[str, Any]:
    """Compile, sign, and write a :class:`ShortcutSpec` to disk.

    Args:
        spec: Validated spec.
        output_dir: Directory to write into. Created if missing.
        sign_mode: Passed through to ``shortcuts sign`` — ``"anyone"``
            for share-sheet imports, ``"people-who-know-me"`` for stricter
            distribution.

    Returns:
        Metadata dict with the absolute output path, name, action count,
        the workflow's stable UUID, and the file size.
    """
    shortcut = compile_spec(spec)
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{_safe_filename(shortcut.name)}.shortcut"
    shortcut.save_signed(path, mode=sign_mode)
    return {
        "path": str(path),
        "name": shortcut.name,
        "action_count": len(shortcut.actions),
        "identifier": shortcut.workflow_identifier,
        "size_bytes": path.stat().st_size,
    }
