"""Variable references, magic variables, templated strings, typed values."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from shortcut_lib.schema.base import SchemaError, Value, coerce_token


@dataclass(frozen=True)
class Output(Value):
    """Reference to another action's output by UUID.

    Created via ``Action.output()`` — you usually don't construct directly.
    """

    uuid: str
    name: str = "Output"

    def to_param(self) -> dict[str, Any]:
        return {
            "Value": self.to_token(),
            "WFSerializationType": "WFTextTokenAttachment",
        }

    def to_token(self) -> dict[str, Any]:
        return {
            "OutputName": self.name,
            "OutputUUID": self.uuid,
            "Type": "ActionOutput",
        }


@dataclass(frozen=True)
class NamedVar[T](Value):
    """Reference to a named variable created by a Set Variable action.

    The phantom type parameter ``T`` carries (informationally) the type of
    the variable's bound value. It does not gate parameter slots today —
    every slot accepts ``ParamValue`` — but it lets call sites annotate
    intent and prepares the schema for per-slot typing in a later release.

    Two construction paths:

    1. Direct: ``NamedVar("Token")``. Useful when the binding lives in a
       different scope from the use site. The variable name is a string
       literal; typos here are silent (iOS shows an empty value at runtime).
    2. Via :meth:`shortcut_lib.builder.Shortcut.set`: returns a typed
       handle bound to a Python identifier. Recommended whenever the bind
       and use sites live in the same builder, because typos at use sites
       become :class:`NameError` at static-type-check time.

    Example:

    .. code-block:: python

        token = s.set("Token", token_text)            # NamedVar[Any] handle
        # …
        auth = Text("Bearer {t}", substitutions={"t": token})  # use the handle

        # Equivalent direct form (no static check on the name):
        s.add(SetVariable(name="Token", input=token_text))
        auth = Text("Bearer {t}", substitutions={"t": NamedVar("Token")})
    """

    name: str

    def to_param(self) -> dict[str, Any]:
        return {
            "Value": self.to_token(),
            "WFSerializationType": "WFTextTokenAttachment",
        }

    def to_token(self) -> dict[str, Any]:
        return {"VariableName": self.name, "Type": "Variable"}


@dataclass(frozen=True)
class MagicVar(Value):
    """Reserved magic variables.

    Use the module-level singletons (``CurrentDate``, ``Clipboard``,
    ``Ask``, ``ShortcutInput``, ``RepeatItem``, ``RepeatIndex``) rather than
    instantiating directly.
    """

    type_name: str

    def to_param(self) -> dict[str, Any]:
        return {
            "Value": self.to_token(),
            "WFSerializationType": "WFTextTokenAttachment",
        }

    def to_token(self) -> dict[str, Any]:
        return {"Type": self.type_name}


CurrentDate = MagicVar("CurrentDate")
Clipboard = MagicVar("Clipboard")
Ask = MagicVar("Ask")
ShortcutInput = MagicVar("ExtensionInput")
RepeatItem = MagicVar("RepeatItem")
RepeatIndex = MagicVar("RepeatIndex")

#: Canonical set of ``Type`` strings for magic variables — always in scope
#: without a preceding SetVariable / AppendVariable.  Derived from the
#: module-level singletons so additions here propagate automatically.
MAGIC_VAR_TYPE_NAMES: frozenset[str] = frozenset(
    mv.type_name
    for mv in (CurrentDate, Clipboard, Ask, ShortcutInput, RepeatItem, RepeatIndex)
)


_PLACEHOLDER = "￼"  # Object Replacement Character — Apple's convention
_TEMPLATE_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


@dataclass
class Text(Value):
    """Templated string with embedded variable substitutions.

    The template uses ``{name}`` placeholders. Each placeholder must have
    a matching keyword in ``substitutions`` whose value is an
    :class:`Action` or :class:`Value` (typically Output or MagicVar).

    On encoding, placeholders are replaced with the ``￼`` object
    replacement character and ``attachmentsByRange`` is populated with
    NSRange-keyed token references — Apple's WFTextTokenString format.
    """

    template: str
    substitutions: dict[str, Any] = field(default_factory=dict)

    def to_param(self) -> dict[str, Any]:
        rendered: list[str] = []
        attachments: dict[str, dict[str, Any]] = {}
        cursor_utf16 = 0
        last = 0

        for match in _TEMPLATE_RE.finditer(self.template):
            literal = self.template[last : match.start()]
            rendered.append(literal)
            cursor_utf16 += _utf16_len(literal)

            name = match.group(1)
            if name not in self.substitutions:
                raise SchemaError(
                    f"Text template references {{{name}}} but no "
                    f"substitution provided. "
                    f"Available: {list(self.substitutions)}"
                )
            rendered.append(_PLACEHOLDER)
            attachments[f"{{{cursor_utf16}, 1}}"] = coerce_token(
                self.substitutions[name]
            )
            cursor_utf16 += 1
            last = match.end()

        rendered.append(self.template[last:])
        return {
            "Value": {
                "string": "".join(rendered),
                "attachmentsByRange": attachments,
            },
            "WFSerializationType": "WFTextTokenString",
        }

    def to_token(self) -> dict[str, Any]:
        # Templated strings only embed in string fields — they don't make
        # sense as a token inside another templated string.
        raise SchemaError("Text cannot be used as a token inside another Text")


def _utf16_len(s: str) -> int:
    """Count UTF-16 code units (supplementary-plane chars take two)."""
    return sum(2 if ord(c) > 0xFFFF else 1 for c in s)


@dataclass(frozen=True)
class Quantity(Value):
    """Number-with-unit value (durations, sizes, etc.).

    Unit strings follow Apple's vocabulary: "min", "hour", "day", "sec",
    "week", "month", "year". For non-time quantities, see the relevant
    action's documentation.
    """

    magnitude: object
    unit: str

    def to_param(self) -> dict[str, Any]:
        if isinstance(self.magnitude, int | float):
            mag: Any = self.magnitude
        else:
            mag = coerce_token(self.magnitude)
        return {
            "Value": {"Magnitude": mag, "Unit": self.unit},
            "WFSerializationType": "WFQuantityFieldValue",
        }

    def to_token(self) -> dict[str, Any]:
        raise SchemaError("Quantity isn't usable as a token inside Text")


@dataclass(frozen=True)
class TimeOffset(Value):
    """Date-arithmetic offset — used by Adjust Date.

    Args:
        operation: e.g. "Add", "Subtract".
        unit: e.g. "Minute", "Hour", "Day".
        value: scalar or variable to offset by.
    """

    operation: str
    unit: str
    value: object

    def to_param(self) -> dict[str, Any]:
        if isinstance(self.value, int | float):
            inner_value: Any = self.value
        else:
            inner_value = coerce_token(self.value)
        return {
            "Value": {
                "Operation": self.operation,
                "Unit": self.unit,
                "Value": inner_value,
            },
            "WFSerializationType": "WFTimeOffsetValue",
        }

    def to_token(self) -> dict[str, Any]:
        raise SchemaError("TimeOffset isn't usable as a token inside Text")
