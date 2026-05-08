"""Command-line entry points."""

from __future__ import annotations

import argparse
import json
import plistlib
import sys
from collections import Counter
from pathlib import Path
from typing import Any, cast

from shortcut_lib.decode import DecodeError, decode_file
from shortcut_lib.summary import workflow_to_summary


def decode_main(argv: list[str] | None = None) -> int:
    """Decode a .shortcut file and print its workflow dict.

    Default output is XML plist (lossless, round-trippable). JSON is convenient
    for scripting but loses bplist type fidelity (e.g. dates, data blobs).
    """
    parser = argparse.ArgumentParser(description="Decode an Apple Shortcuts file.")
    parser.add_argument("input", type=Path, help="Path to a .shortcut file")
    parser.add_argument(
        "--format",
        choices=("xml", "json", "summary", "buzz"),
        default="xml",
        help="Output format (default: xml). 'buzz' is a compact, "
        "LLM-readable representation; 'summary' is a header-only digest.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Write to file instead of stdout",
    )
    args = parser.parse_args(argv)

    try:
        decoded = decode_file(args.input)
    except DecodeError as exc:
        print(f"decode failed: {exc}", file=sys.stderr)
        return 1

    if args.format == "summary":
        out = _summarise(decoded.workflow, decoded.signing_subject).encode()
    elif args.format == "buzz":
        out = workflow_to_summary(decoded.workflow).encode()
    elif args.format == "json":
        out = json.dumps(decoded.workflow, indent=2, default=_json_default).encode()
    else:
        out = plistlib.dumps(decoded.workflow, fmt=plistlib.FMT_XML)

    if args.output:
        args.output.write_bytes(out)
    else:
        sys.stdout.buffer.write(out)
        if not out.endswith(b"\n"):
            sys.stdout.buffer.write(b"\n")
    return 0


def _json_default(obj: object) -> object:
    if isinstance(obj, bytes):
        return f"<bytes:{len(obj)}>"
    raise TypeError(f"unserialisable: {type(obj).__name__}")


def _summarise(workflow: dict[str, object], signer: str) -> str:
    actions = cast(list[dict[str, Any]], workflow.get("WFWorkflowActions") or [])
    counter: Counter[str] = Counter(
        a["WFWorkflowActionIdentifier"]
        for a in actions
        if isinstance(a.get("WFWorkflowActionIdentifier"), str)
    )

    types = cast(list[str], workflow.get("WFWorkflowTypes") or [])
    lines = [
        f"signed by:    {signer}",
        f"client min:   {workflow.get('WFWorkflowMinimumClientVersionString')}",
        f"surfaces:     {', '.join(types) if types else '(none)'}",
        f"actions:      {len(actions)} total, {len(counter)} distinct",
        "",
        "action breakdown:",
        *(f"  {count:3d}  {ident}" for ident, count in counter.most_common()),
    ]
    return "\n".join(lines) + "\n"
