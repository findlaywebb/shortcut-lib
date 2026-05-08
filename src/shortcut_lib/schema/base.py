"""Base classes for the schema layer.

``Value`` is the protocol-style base for anything that can be embedded as a
parameter (variable references, templated strings, quantities). ``Action``
is the base for leaf actions (operations that produce one
WFWorkflowActions entry). Control-flow constructs override ``to_actions``
to emit multiple entries.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar
from uuid import uuid4

if TYPE_CHECKING:
    from shortcut_lib.schema.values import Output


class SchemaError(ValueError):
    """Raised when an Action or Value can't produce a valid parameter dict.

    Error messages should state what was wrong and what shape was expected
    so a calling LLM can self-correct.
    """


def fresh_uuid() -> str:
    """Return an uppercase UUID4 — Apple's convention in shortcut files."""
    return str(uuid4()).upper()


class Value(ABC):
    """Anything embeddable as a Shortcuts parameter value.

    Implementations include single-variable references (Output, NamedVar),
    magic variables (CurrentDate, Clipboard…), templated strings (Text),
    and typed value containers (Quantity, TimeOffset).
    """

    @abstractmethod
    def to_param(self) -> Any:
        """Return the wire-format dict (or scalar) for this value.

        Typical shape is ``{Value: {…}, WFSerializationType: "WF…"}``.
        """

    def to_token(self) -> dict[str, Any]:
        """Return the inner token form for embedding inside templated strings.

        Default implementation falls back to the inner ``Value`` of
        ``to_param()`` if it's a serialised dict; subclasses with simpler
        token shapes (variable references) override this directly.
        """
        param = self.to_param()
        if isinstance(param, dict) and "Value" in param:
            inner = param["Value"]
            if isinstance(inner, dict):
                return inner
        raise SchemaError(
            f"{type(self).__name__} does not have a token form usable inside Text"
        )


@dataclass
class Action(ABC):
    """Base for a single Shortcuts action (one WFWorkflowActions entry).

    Subclasses set the class variables ``identifier`` and (optionally)
    ``default_output_name``, and implement ``_params`` to emit the
    action-specific parameters dict.

    Each Action gets a fresh UUID at construction; tests can override by
    passing ``uuid=...``. ``custom_output_name`` populates Apple's
    ``CustomOutputName`` parameter, the human-readable label users see.
    """

    identifier: ClassVar[str] = ""
    default_output_name: ClassVar[str] = ""

    uuid: str = field(default_factory=fresh_uuid)
    custom_output_name: str | None = None

    @abstractmethod
    def _params(self) -> dict[str, Any]:
        """Return action-specific parameters (without UUID/CustomOutputName)."""

    def to_action_dict(self) -> dict[str, Any]:
        """Emit the {WFWorkflowActionIdentifier, WFWorkflowActionParameters} dict."""
        if not self.identifier:
            raise SchemaError(
                f"{type(self).__name__} is missing class-level `identifier`"
            )
        params = dict(self._params())  # copy so subclasses don't mutate
        params["UUID"] = self.uuid
        if self.custom_output_name:
            params["CustomOutputName"] = self.custom_output_name
        return {
            "WFWorkflowActionIdentifier": self.identifier,
            "WFWorkflowActionParameters": params,
        }

    def to_actions(self) -> list[dict[str, Any]]:
        """Emit the action(s) this construct produces. Leaf actions return one."""
        return [self.to_action_dict()]

    def output(self, name: str | None = None) -> Output:
        """Reference this action's output for embedding in later actions.

        Args:
            name: Display name for the reference. Falls back to
                ``custom_output_name`` then to the class's ``default_output_name``.
        """
        from shortcut_lib.schema.values import Output

        resolved = name or self.custom_output_name or self.default_output_name
        if not resolved:
            resolved = type(self).__name__
        return Output(uuid=self.uuid, name=resolved)


@dataclass
class RawAction(Action):
    """Pass-through action for identifiers we don't have a typed class for.

    Holds the action's identifier and parameters dict verbatim. Round-trips
    exactly, can be inspected and mutated, but offers no parameter validation.
    Used by ``Shortcut.from_workflow`` to lift a decoded dict back into a
    Shortcut wrapper, and for hand-authoring against any identifier.

    The class-level :attr:`Action.identifier` stays empty; the real
    identifier is stored on the instance as ``raw_identifier`` and emitted
    by the overridden :meth:`to_action_dict`.
    """

    raw_identifier: str = ""
    raw_params: dict[str, Any] = field(default_factory=dict)

    def to_action_dict(self) -> dict[str, Any]:
        # raw_params already contains UUID and any other Apple-side keys —
        # return as-is rather than going through _params + injection.
        if not self.raw_identifier:
            raise SchemaError("RawAction needs raw_identifier")
        return {
            "WFWorkflowActionIdentifier": self.raw_identifier,
            "WFWorkflowActionParameters": dict(self.raw_params),
        }

    def _params(self) -> dict[str, Any]:
        return self.raw_params


def coerce_value(x: object) -> Any:
    """Coerce a Python primitive, Action, or Value to a parameter value.

    - Action → its output token reference (single-variable form)
    - Value → ``x.to_param()``
    - Primitives (str/int/float/bool/None/list/dict) → returned as-is
    """
    if isinstance(x, Action):
        return x.output().to_param()
    if isinstance(x, Value):
        return x.to_param()
    if isinstance(x, dict):
        # Already a wire-format dict; don't double-wrap.
        return x
    return x


def coerce_token(x: object) -> dict[str, Any]:
    """Coerce to a *token* dict — the inner form usable inside templated strings.

    Used by ``Text`` substitutions and Quantity/TimeOffset magnitude fields
    where the parameter wants the bare token, not the full
    ``{Value, WFSerializationType}`` envelope.
    """
    if isinstance(x, Action):
        return x.output().to_token()
    if isinstance(x, Value):
        return x.to_token()
    raise SchemaError(
        f"cannot coerce {type(x).__name__} to a token — pass an Action, Output, "
        f"NamedVar, MagicVar, or other Value"
    )
