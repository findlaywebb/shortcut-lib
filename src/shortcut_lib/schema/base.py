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


# Type alias for action-parameter slots. Most parameter fields accept any of
# the items below — a primitive scalar, a previous Action's output, a Value
# (variable reference, templated string, quantity, etc.), a pre-built wire
# envelope dict, or a list of any of the above. Used by action dataclasses
# and surfaced by ``describe_action`` so LLM authors see the union rather
# than ``Any``.
type ParamValue = (
    str | int | float | bool | None | "Action" | "Value" | dict[str, Any] | list[Any]
)


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
        if not self.raw_identifier:
            raise SchemaError("RawAction needs raw_identifier")
        # Keep ``self.uuid`` (the dataclass field used by ``.output()``) and
        # the emitted action's UUID in sync. A freshly-authored
        # ``RawAction(raw_identifier="…", raw_params={})`` would otherwise
        # have a fresh ``self.uuid`` but no UUID in the emitted dict; a
        # downstream ``raw.output()`` reference would then point at a UUID
        # the action doesn't carry, resolving as a dangling ref on iOS.
        # When ``self.uuid`` is empty (lift round-trip from a sample whose
        # action carried no UUID), preserve that wire-format quirk.
        params = dict(self.raw_params)
        if self.uuid:
            params["UUID"] = self.uuid
        return {
            "WFWorkflowActionIdentifier": self.raw_identifier,
            "WFWorkflowActionParameters": params,
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


# Object Replacement Character (U+FFFC) — Apple uses this single 1-UTF-16-unit
# codepoint as the placeholder slot for an attachment inside WFTextTokenString.
_OBJECT_REPLACEMENT = "￼"


def coerce_text_field(x: object) -> Any:
    """Coerce a value for a parameter slot that Apple reads as WFTextTokenString.

    Several Apple parameter slots — ``WFURL``, ``WFDate``, JSON body /
    header dict values — refuse to read a bare ``WFTextTokenAttachment``
    envelope and present as empty / disconnected at runtime ("No URL
    Specified", an empty formatted date, etc.). Apple's wire format wraps
    even single variable references as a one-attachment ``WFTextTokenString``.

    This helper takes the raw Python value (Action, Value, str, scalar, or
    pre-built envelope) and returns the wire form Apple expects for those
    slots:

    - ``Action`` / ``Value`` → single-attachment WFTextTokenString.
    - ``str`` → bare string (matches Apple's emission for static URLs and
      similar; the runtime is permissive at that layer).
    - Pre-built ``WFTextTokenString`` envelope → passed through.
    - Pre-built ``WFTextTokenAttachment`` envelope → rewrapped as a
      one-attachment WFTextTokenString.
    - Other scalars / pre-built envelopes → returned as-is.

    Args:
        x: A raw parameter value or a coerced wire-format dict.

    Returns:
        The wire-format value safe to drop into a text-token-string slot.
    """
    if isinstance(x, str):
        return x
    coerced = coerce_value(x)
    if (
        isinstance(coerced, dict)
        and coerced.get("WFSerializationType") == "WFTextTokenAttachment"
    ):
        # Rewrap a single variable reference as a one-attachment templated
        # string. Text.to_param() already returns WFTextTokenString and
        # passes through unchanged.
        return {
            "Value": {
                "string": _OBJECT_REPLACEMENT,
                "attachmentsByRange": {"{0, 1}": coerced["Value"]},
            },
            "WFSerializationType": "WFTextTokenString",
        }
    return coerced


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
