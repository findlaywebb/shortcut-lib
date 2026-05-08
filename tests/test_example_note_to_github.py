"""Validate the note_to_github example builds a structurally-correct workflow.

The example is the proof-point for Tier 2: HTTP + base64 + dictionary
parameters all wire together end-to-end. We don't actually hit GitHub
(the token is a placeholder); we just check the action sequence is
shaped correctly.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

EXAMPLES = Path(__file__).parent.parent / "examples"
sys.path.insert(0, str(EXAMPLES))

from note_to_github import build  # noqa: E402  # ty: ignore[unresolved-import]


def test_workflow_emits_expected_action_sequence() -> None:
    workflow = build().to_workflow()
    actions = workflow["WFWorkflowActions"]
    identifiers = [a["WFWorkflowActionIdentifier"] for a in actions]

    # gettext/setvariable appear several times by design (multi-step pipeline).
    # The actions below run exactly once — using ``count`` catches regressions
    # where a refactor accidentally double-emits one of them.
    expected_once = [
        "is.workflow.actions.getclipboard",
        "is.workflow.actions.format.date",
        "is.workflow.actions.base64encode",
        "is.workflow.actions.text.replace",
        "is.workflow.actions.downloadurl",
        "is.workflow.actions.notification",
    ]
    for ident in expected_once:
        assert identifiers.count(ident) == 1, (
            f"expected {ident} exactly once, got {identifiers.count(ident)}"
        )
    # gettext and setvariable are present multiple times — assert "at least one".
    for ident in ("is.workflow.actions.gettext", "is.workflow.actions.setvariable"):
        assert ident in identifiers


def _find(actions: list[dict[str, Any]], identifier: str) -> dict[str, Any]:
    for action in actions:
        if action["WFWorkflowActionIdentifier"] == identifier:
            return action["WFWorkflowActionParameters"]
    raise KeyError(identifier)


def test_download_url_carries_auth_and_json_body() -> None:
    actions = build().to_workflow()["WFWorkflowActions"]
    download = _find(actions, "is.workflow.actions.downloadurl")

    assert download["WFHTTPMethod"] == "PUT"
    assert download["WFHTTPBodyType"] == "JSON"
    assert download["ShowHeaders"] is True

    headers = download["WFHTTPHeaders"]["Value"]["WFDictionaryFieldValueItems"]
    keys = {entry["WFKey"]["Value"]["string"] for entry in headers}
    assert {"Authorization", "Accept", "X-GitHub-Api-Version"} <= keys

    body_items = download["WFJSONValues"]["Value"]["WFDictionaryFieldValueItems"]
    body_keys = {entry["WFKey"]["Value"]["string"] for entry in body_items}
    assert body_keys == {"message", "content"}


def test_signs_to_disk(tmp_path: Path) -> None:
    """Confirm the example's full pipeline (Python → bplist → AEA) doesn't error.

    Doesn't hit the network; doesn't validate that GitHub would accept the
    request. Just proves the schema → encoder → CLI sign chain works.
    """
    out = tmp_path / "Note to GitHub.shortcut"
    build().save_signed(out)
    assert out.exists() and out.stat().st_size > 0
