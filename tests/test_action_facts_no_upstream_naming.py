"""Guard: the action-fact dataset must contain only Apple-side identifiers.

The dataset is bootstrapped from Open-Jellycore's catalogue but ships only
factual fields about Apple's API. Any string with the prefix ``jelly.`` or
``Jelly_`` is upstream original expression (their invented identifiers,
their Swift type prefix) and must not leak into the shipped JSON.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FACTS = Path(__file__).parent.parent / "data" / "jellycore_facts.json"

UPSTREAM_PREFIXES = ("jelly.", "Jelly_")


def _walk_strings(node: object) -> list[str]:
    if isinstance(node, str):
        return [node]
    if isinstance(node, dict):
        out: list[str] = []
        for k, v in node.items():
            if isinstance(k, str):
                out.append(k)
            out.extend(_walk_strings(v))
        return out
    if isinstance(node, list):
        out = []
        for v in node:
            out.extend(_walk_strings(v))
        return out
    return []


def test_no_upstream_naming_leaks_into_shipped_json() -> None:
    if not FACTS.exists():
        pytest.skip("data/jellycore_facts.json not present")
    facts = json.loads(FACTS.read_text())
    leaks = [
        s
        for s in _walk_strings(facts)
        if any(s.startswith(p) for p in UPSTREAM_PREFIXES)
    ]
    assert not leaks, (
        f"upstream-prefix strings ({UPSTREAM_PREFIXES}) found in shipped JSON: "
        f"{leaks[:5]}"
    )
