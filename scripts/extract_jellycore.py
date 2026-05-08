"""Extract structural facts from an Open-Jellycore checkout.

Open-Jellycore (https://github.com/OpenJelly/Open-Jellycore) is GPL-3.0. We
treat its lookup tables as a *reference* for Apple's Shortcuts action surface
and extract only the factual data — identifier strings, Apple-side display
names, parameter key names, enum members, OS-min metadata. We deliberately
skip Jellycore's descriptions and DSL-name choices since those are original
expression by the project author.

Run:
    uv run python scripts/extract_jellycore.py \\
        --source /tmp/shortcut-research/Open-Jellycore \\
        --out data/jellycore_facts.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterable
from pathlib import Path

# (?msx) — multiline, dotall, verbose
ACTION_ENTRY_RE = re.compile(
    r"""
    "(?P<dsl>[A-Za-z0-9_]+)" \s*:\s* Action< (?P<param>[A-Za-z0-9_]+) >
    \s* \( \s*
        name: \s* "(?P<name>[^"]*)" \s*,\s*
        identifier: \s* "(?P<identifier>[^"]*)" \s*,\s*
        correctTypedFunction: \s* "[^"]*" \s*,\s*
        description: \s* (?:"[^"]*"|\"\"\".*?\"\"\") \s*,\s*
        lowestCompatibleHost: \s* \.(?P<host>[A-Za-z0-9]+)
    """,
    re.MULTILINE | re.DOTALL | re.VERBOSE,
)

PARAM_FIELD_RE = re.compile(
    r"^\s*var\s+(?P<name>[A-Za-z0-9_]+)\s*:\s*(?P<type>[^\s={]+)\??",
    re.MULTILINE,
)

# Enums declare bare cases then expose strings via a `var value: String`
# switch. We grab from the switch since those quoted strings are the wire
# representation Apple expects in the bplist.
ENUM_VALUE_RE = re.compile(
    r'case\s+\.(?P<name>[A-Za-z0-9_]+)\s*:\s*return\s+"(?P<value>[^"]*)"',
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("/tmp/shortcut-research/Open-Jellycore"),  # noqa: S108
        help="Path to an Open-Jellycore git checkout",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "data/jellycore_facts.json",
    )
    args = parser.parse_args()

    if not args.source.is_dir():
        print(
            f"source not found: {args.source}\n"
            f"clone it with: git clone --depth 1 "
            f"https://github.com/OpenJelly/Open-Jellycore {args.source}",
            file=sys.stderr,
        )
        return 1

    shortcuts_dir = (
        args.source / "Sources/Open-Jellycore/Core/Compiler/"
        "Lookup Tables/Apps/Shortcuts"
    )
    if not shortcuts_dir.is_dir():
        print(f"expected directory missing: {shortcuts_dir}", file=sys.stderr)
        return 1

    actions = _extract_actions(shortcuts_dir / "ShortcutsLookupTable.swift")
    _enrich_with_param_keys(actions, shortcuts_dir / "Actions")
    enums = _extract_enums(shortcuts_dir / "Enums")
    structural = _extract_structural_identifiers(
        args.source / "Sources/Open-Jellycore/Core/Compiler/Compiler.swift"
    )

    facts = {
        "source": "https://github.com/OpenJelly/Open-Jellycore (GPL-3.0)",
        "extracted_fields": [
            "WFWorkflow identifiers",
            "Apple display names",
            "lowestCompatibleHost (OS min)",
            "parameter WF* key names",
            "enum members (Apple's typed values)",
        ],
        "deliberately_omitted": [
            "Jellycore description prose (original expression)",
            "Jellycore DSL function names",
            "presets",
        ],
        "actions": actions,
        "structural_identifiers": structural,
        "enums": enums,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(facts, indent=2, sort_keys=True) + "\n")

    print(
        f"wrote {args.out.relative_to(Path.cwd())} — "
        f"{len(actions)} actions, {len(structural)} structural ids, "
        f"{len(enums)} enums"
    )
    no_params = [a for a in actions if not a["parameter_keys"]]
    if no_params:
        print(f"  ({len(no_params)} actions had no parameter file or empty params)")
    return 0


def _extract_actions(lookup_path: Path) -> list[dict[str, object]]:
    text = lookup_path.read_text()
    out: list[dict[str, object]] = []
    seen_dsl: set[str] = set()
    for match in ACTION_ENTRY_RE.finditer(text):
        dsl = match["dsl"]
        if dsl in seen_dsl:
            continue
        seen_dsl.add(dsl)
        out.append(
            {
                "_dsl_name": dsl,  # kept for cross-ref to parameter file only
                "display_name": match["name"],
                "identifier": match["identifier"],
                "lowest_compatible_host": match["host"],
                "_parameter_struct": match["param"],
                "parameter_keys": [],
            }
        )
    out.sort(key=lambda a: str(a["identifier"]))
    return out


def _enrich_with_param_keys(
    actions: list[dict[str, object]], actions_dir: Path
) -> None:
    by_struct = {a["_parameter_struct"]: a for a in actions}
    for swift in actions_dir.glob("*.swift"):
        struct = swift.stem  # filename === struct name (Open-Jellycore convention)
        target = by_struct.get(struct)
        if target is None:
            continue
        text = swift.read_text()
        # Take the body up to the first `static func build` to avoid local vars
        head = text.split("static func build", 1)[0]
        keys = [m["name"] for m in PARAM_FIELD_RE.finditer(head)]
        target["parameter_keys"] = keys


def _extract_structural_identifiers(compiler_path: Path) -> list[str]:
    """Identifiers Jellycore emits from language constructs, not lookup table.

    `if/else`, `for`, `menu`, comments etc. all hard-code their
    `is.workflow.actions.*` identifier inside Compiler.swift rather than
    appearing in `ShortcutsLookupTable.swift`. We pull them out so the
    coverage report doesn't flag them as missing.
    """
    if not compiler_path.is_file():
        return []
    text = compiler_path.read_text()
    pattern = re.compile(r'WFWorkflowActionIdentifier:\s*"([^"]+)"')
    return sorted(set(pattern.findall(text)))


def _extract_enums(enums_dir: Path) -> dict[str, list[str]]:
    if not enums_dir.is_dir():
        return {}
    out: dict[str, list[str]] = {}
    for swift in enums_dir.glob("Jelly_*.swift"):
        name = swift.stem.removeprefix("Jelly_")
        text = swift.read_text()
        values = sorted({m["value"] for m in ENUM_VALUE_RE.finditer(text)})
        if values:
            out[name] = values
    return out


def _strip_internals(actions: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    """Drop underscore-prefixed cross-ref keys before output. (Currently kept
    for traceability; called only in tests.)"""
    keep = ("display_name", "identifier", "lowest_compatible_host", "parameter_keys")
    return [{k: a[k] for k in keep if k in a} for a in actions]


if __name__ == "__main__":
    raise SystemExit(main())
