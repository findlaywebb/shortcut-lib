"""LLM-readable summary of a decoded workflow.

Dumps a workflow dict as a compact, line-per-action listing — one indented
line per action, control flow visualised as ``if``/``else``/``end``,
variables as ``$Name`` rather than full UUIDs, templated strings inlined.

Goal: roughly 10x fewer tokens than the XML plist for the same shortcut,
and unambiguous enough that Claude can re-author from the summary.

The summary is *informational*; it doesn't round-trip. For round-trip use
the decoded workflow dict directly.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

CONTROL_FLOW: dict[str, str] = {
    "is.workflow.actions.conditional": "if",
    "is.workflow.actions.repeat.each": "for-each",
    "is.workflow.actions.repeat.count": "repeat",
    "is.workflow.actions.choosefrommenu": "menu",
}

# Identifiers we shorten in display. Anything not here keeps its tail
# segment (e.g. is.workflow.actions.text.split -> "text.split").
SHORT_NAMES: dict[str, str] = {
    "is.workflow.actions.gettext": "text",
    "is.workflow.actions.setvariable": "set",
    "is.workflow.actions.getvariable": "get",
    "is.workflow.actions.appendvariable": "append",
    "is.workflow.actions.runworkflow": "run-shortcut",
    "is.workflow.actions.notification": "notify",
    "is.workflow.actions.showresult": "show",
    "is.workflow.actions.ask": "ask",
    "is.workflow.actions.comment": "#",
    "is.workflow.actions.getclipboard": "clipboard.get",
    "is.workflow.actions.setclipboard": "clipboard.set",
    "is.workflow.actions.format.date": "format-date",
    "is.workflow.actions.adjustdate": "adjust-date",
}


def workflow_to_summary(workflow: dict[str, Any]) -> str:
    """Render a decoded workflow as a multi-line summary string."""
    actions: list[dict[str, Any]] = workflow.get("WFWorkflowActions") or []
    name = workflow.get("WFWorkflowName") or "(unnamed)"
    types: list[str] = workflow.get("WFWorkflowTypes") or []
    min_client = workflow.get("WFWorkflowMinimumClientVersionString") or "-"

    uuid_to_name = _build_uuid_index(actions)

    header = [
        f"# {name}",
        f"# surfaces: {', '.join(types) if types else '(none)'}",
        f"# min client: {min_client}",
        f"# {len(actions)} actions",
        "",
    ]

    body: list[str] = []
    indent = 0
    for action in actions:
        ident = action.get("WFWorkflowActionIdentifier", "")
        params = action.get("WFWorkflowActionParameters") or {}

        if ident in CONTROL_FLOW:
            mode = params.get("WFControlFlowMode", 0)
            keyword = CONTROL_FLOW[ident]
            if mode == 0:  # open
                head = _format_control_head(keyword, params, uuid_to_name)
                body.append(_indent(indent) + head + ":")
                indent += 1
            elif mode == 1:  # else / case
                indent = max(indent - 1, 0)
                middle = _format_control_middle(keyword, params, uuid_to_name)
                body.append(_indent(indent) + middle + ":")
                indent += 1
            elif mode == 2:  # close
                indent = max(indent - 1, 0)
                body.append(_indent(indent) + f"end {keyword}")
            else:
                body.append(_indent(indent) + f"# unknown {keyword} mode={mode}")
        else:
            body.append(_indent(indent) + _format_leaf(ident, params, uuid_to_name))

    return "\n".join(header + body) + "\n"


def _build_uuid_index(actions: Iterable[dict[str, Any]]) -> dict[str, str]:
    """Map every action's UUID to a human name we'll use in $references."""
    out: dict[str, str] = {}
    for action in actions:
        params = action.get("WFWorkflowActionParameters") or {}
        uuid = params.get("UUID")
        if not isinstance(uuid, str):
            continue
        name = params.get("CustomOutputName")
        if not isinstance(name, str) or not name.strip():
            ident = action.get("WFWorkflowActionIdentifier", "")
            name = _short_name(ident)
        out[uuid] = name
    return out


def _short_name(identifier: str) -> str:
    if identifier in SHORT_NAMES:
        return SHORT_NAMES[identifier]
    if identifier.startswith("is.workflow.actions."):
        return identifier.removeprefix("is.workflow.actions.")
    return identifier


def _indent(level: int) -> str:
    return "  " * level


def _format_control_head(
    keyword: str, params: dict[str, Any], uuids: dict[str, str]
) -> str:
    if keyword == "if":
        cond = params.get("WFCondition")
        operand = _format_value(_input_value(params), uuids)
        compare = _condition_compare(params, uuids)
        return f"if {operand} {_condition_op(cond)} {compare}".rstrip()
    if keyword == "for-each":
        target = _format_value(_input_value(params), uuids)
        return f"for each in {target}"
    if keyword == "repeat":
        n = _format_value(params.get("WFRepeatCount"), uuids)
        return f"repeat {n} times"
    if keyword == "menu":
        prompt = _format_value(params.get("WFMenuPrompt"), uuids)
        items = params.get("WFMenuItems") or []
        if isinstance(items, list) and items:
            label_list = ", ".join(_format_value(item, uuids) for item in items)
            return f"menu {prompt} [{label_list}]"
        return f"menu {prompt}"
    return keyword


def _format_control_middle(
    keyword: str, params: dict[str, Any], uuids: dict[str, str]
) -> str:
    if keyword == "if":
        return "else"
    if keyword == "menu":
        label = _format_value(params.get("WFMenuItemTitle"), uuids)
        return f"case {label}"
    return keyword


def _condition_op(code: object) -> str:
    """Best-effort enum mapping for `WFCondition` (numeric in current iOS)."""
    from shortcut_lib.schema.control import CONDITION_NAMES

    if not isinstance(code, int):
        return "?"
    return CONDITION_NAMES.get(code, f"<op {code!r}>")


def _condition_compare(params: dict[str, Any], uuids: dict[str, str]) -> str:
    if "WFNumberValue" in params:
        return _format_value(params["WFNumberValue"], uuids)
    if "WFConditionalActionString" in params:
        return _format_value(params["WFConditionalActionString"], uuids)
    return ""


def _input_value(params: dict[str, Any]) -> Any:
    """`if` and `for-each` wrap their input in a Variable envelope; unwrap."""
    raw = params.get("WFInput")
    if isinstance(raw, dict) and raw.get("Type") == "Variable":
        return raw.get("Variable")
    return raw


def _format_leaf(identifier: str, params: dict[str, Any], uuids: dict[str, str]) -> str:
    short = _short_name(identifier)
    output_decl = ""
    custom = params.get("CustomOutputName")
    uuid = params.get("UUID")
    if isinstance(custom, str) and custom.strip():
        output_decl = f" -> ${custom}"
    elif isinstance(uuid, str) and uuids.get(uuid) == _short_name(identifier):
        # Action produces output but no custom name — still expose its short
        output_decl = f" -> ${_short_name(identifier)}"

    arg_strs: list[str] = []
    for key, value in params.items():
        if key in {"UUID", "CustomOutputName"}:
            continue
        arg_strs.append(f"{key}={_format_value(value, uuids)}")
    args = " ".join(arg_strs)
    return f"{short}{(' ' + args) if args else ''}{output_decl}"


def _format_value(value: Any, uuids: dict[str, str]) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    if isinstance(value, str):
        return _format_string(value)
    if isinstance(value, dict):
        return _format_dict(value, uuids)
    if isinstance(value, list):
        items = ", ".join(_format_value(v, uuids) for v in value)
        return f"[{items}]"
    if isinstance(value, bytes):
        return f"<bytes:{len(value)}>"
    return repr(value)


def _format_string(s: str) -> str:
    if any(ch in s for ch in '"\n'):
        return json.dumps(s)
    return f'"{s}"'


def _format_dict(value: dict[str, Any], uuids: dict[str, str]) -> str:
    serialization = value.get("WFSerializationType")
    inner = value.get("Value")

    if serialization == "WFTextTokenAttachment" and isinstance(inner, dict):
        return _format_token(inner, uuids)
    if serialization == "WFTextTokenString" and isinstance(inner, dict):
        return _format_templated_string(inner, uuids)
    if serialization == "WFQuantityFieldValue" and isinstance(inner, dict):
        magnitude = _format_value(inner.get("Magnitude"), uuids)
        unit = inner.get("Unit") or ""
        return f"{magnitude} {unit}".strip()
    if serialization == "WFTimeOffsetValue" and isinstance(inner, dict):
        op = inner.get("Operation") or ""
        unit = inner.get("Unit") or ""
        magnitude = _format_value(inner.get("Value"), uuids)
        return f"({op} {magnitude} {unit})".strip()

    # Variable envelope (used by condition inputs etc.)
    if value.get("Type") == "Variable" and isinstance(value.get("Variable"), dict):
        return _format_dict(value["Variable"], uuids)

    # Token-shaped dict without serialization wrapper (rare but seen)
    if "OutputUUID" in value and "Type" in value:
        return _format_token(value, uuids)
    if "VariableName" in value and value.get("Type") == "Variable":
        return f"${value['VariableName']}"

    # Fallback: collapse to short repr — keeps output dense without losing
    # structural hints. Full XML stays available via --format xml.
    if not value:
        return "{}"
    keys = ", ".join(value.keys())
    return f"{{{keys}}}"


def _format_token(token: dict[str, Any], uuids: dict[str, str]) -> str:
    """Render a single-variable reference token."""
    typ = token.get("Type")
    if typ == "ActionOutput":
        uuid = token.get("OutputUUID")
        name = uuids.get(uuid) if isinstance(uuid, str) else None
        # Stale gallery shortcuts sometimes reference a UUID that no longer
        # exists; fall back to OutputName so the summary stays informative.
        if not name:
            fallback = token.get("OutputName")
            name = fallback if isinstance(fallback, str) and fallback else "?"
        return _var_ref(name)
    if typ == "Variable":
        return _var_ref(str(token.get("VariableName", "?")))
    if isinstance(typ, str):
        return f"@{typ}"
    return "<token>"


def _var_ref(name: str) -> str:
    """`$Name` for plain identifiers, `${Name with space}` otherwise."""
    if name and all(ch.isalnum() or ch == "_" for ch in name):
        return f"${name}"
    return f"${{{name}}}"


def _format_templated_string(value: dict[str, Any], uuids: dict[str, str]) -> str:
    """Inline a WFTextTokenString — replace ￼ placeholders with $vars."""
    string = value.get("string", "")
    attachments = value.get("attachmentsByRange") or {}
    if not isinstance(string, str):
        return repr(string)

    # Sort by NSRange offset so we walk left-to-right
    sorted_ranges: list[tuple[int, int, dict[str, Any]]] = []
    for key, token in attachments.items():
        if not isinstance(key, str) or not isinstance(token, dict):
            continue
        offset, length = _parse_nsrange(key)
        if offset is None:
            continue
        sorted_ranges.append((offset, length, token))
    sorted_ranges.sort(key=lambda r: r[0])

    # NSRange is in UTF-16 code units; Python strings count differently for
    # supplementary-plane characters, but for object-replacement (￼)
    # which is BMP it works out the same.
    out: list[str] = []
    cursor = 0
    for offset, length, token in sorted_ranges:
        out.append(string[cursor:offset])
        out.append(_format_token(token, uuids))
        cursor = offset + length
    out.append(string[cursor:])
    rendered = "".join(out).replace("￼", "")
    return _format_string(rendered)


def _parse_nsrange(key: str) -> tuple[int | None, int]:
    """`{20, 1}` -> (20, 1)."""
    stripped = key.strip().strip("{}")
    parts = [p.strip() for p in stripped.split(",")]
    if len(parts) != 2:
        return (None, 0)
    try:
        return (int(parts[0]), int(parts[1]))
    except ValueError:
        return (None, 0)
