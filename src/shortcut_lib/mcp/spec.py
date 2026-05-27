"""Pydantic models for the MCP JSON shortcut spec.

The spec is the agent's authoring surface: a flat JSON document the agent
fills and hands to ``shortcut_build``. The shape is deliberately minimal:

- ``actions[]``: ordered list of action invocations.
- Each action names its class (``type``) and parameter bindings (``params``).
- An optional ``ref`` labels the action's output for reuse downstream as
  ``"${ref}"`` inside any later string parameter.

A pure ``"${ref}"`` string resolves to a single-attachment variable
reference; an interleaved string ``"hello ${ref}!"`` resolves to a templated
:class:`shortcut_lib.schema.values.Text` value.

Why this shape: flat top-level params with constrained types are the easiest
for an LLM to fill correctly first try (see Schmid / Workato MCP guidance).
Refs replace the imperative ``s.set(...)`` builder pattern with a purely
declarative one — the spec is round-trippable and JSON-Schema-validatable.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ${name} — pattern used both by ActionSpec.ref validation and the compiler.
REF_PATTERN: re.Pattern[str] = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
REF_NAME_PATTERN: re.Pattern[str] = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class ActionSpec(BaseModel):
    """One action in the shortcut.

    Attributes:
        type: Action class name (``"DictateText"``) **or** full Apple
            identifier (``"is.workflow.actions.dictate.text"``). Discover
            options via the ``shortcut_list_actions`` MCP tool.
        ref: Optional alias for this action's output, referenced as
            ``"${ref}"`` in any later string parameter. Must be a valid
            Python identifier.
        params: Keyword arguments passed to the action's dataclass. Inspect
            the expected fields via ``shortcut_get_action_schema``.
        custom_output_name: Override the user-facing label of this action's
            output. Optional.
    """

    model_config = ConfigDict(extra="forbid")

    type: str = Field(min_length=1, max_length=120)
    ref: str | None = Field(default=None, max_length=64)
    params: dict[str, Any] = Field(default_factory=dict)
    custom_output_name: str | None = Field(default=None, max_length=120)

    @field_validator("ref")
    @classmethod
    def _validate_ref(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not REF_NAME_PATTERN.match(v):
            raise ValueError(
                f"ref must be a Python identifier, got {v!r}. "
                f"Use letters, digits, underscores; must not start with a digit."
            )
        return v


class ShortcutSpec(BaseModel):
    """A complete shortcut authoring spec.

    Attributes:
        name: Display filename (no extension). Becomes ``<name>.shortcut``.
        surfaces: Where the shortcut appears in Shortcuts.app. Accepted
            values: ``"watch"``, ``"widget"``, ``"share"``, ``"menubar"``,
            ``"quick-action"``, ``"sleep"``. Empty list = main library only.
        accepted_input: Content-item classes accepted when invoked from
            the share sheet (e.g. ``"WFStringContentItem"``,
            ``"WFURLContentItem"``). Empty list = no input.
        output_classes: Content-item classes this shortcut emits as output.
        min_client: Minimum Shortcuts client version. Default 900 (~iOS 16);
            raise only if you rely on newer actions.
        actions: Ordered action list. At least one entry required.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(default="Untitled", min_length=1, max_length=120)
    surfaces: list[str] = Field(default_factory=list)
    accepted_input: list[str] = Field(default_factory=list)
    output_classes: list[str] = Field(default_factory=list)
    min_client: int = Field(default=900, ge=0, le=99999)
    actions: list[ActionSpec] = Field(min_length=1)


def find_refs(value: str) -> list[str]:
    """Return every ``${name}`` reference inside ``value`` in source order."""
    return REF_PATTERN.findall(value)


def pure_ref(value: str) -> str | None:
    """If ``value`` is exactly ``${name}`` (with optional surrounding ws), return ``name``.

    Returns ``None`` for any other string — interleaved templates or plain
    text. The compiler uses this to distinguish a single-attachment variable
    reference from a templated :class:`Text`.
    """
    stripped = value.strip()
    match = REF_PATTERN.fullmatch(stripped)
    return match.group(1) if match else None
