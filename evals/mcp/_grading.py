"""Task model and deterministic graders for the MCP eval harness.

The agent's emitted ``.shortcut`` file is the source of truth: we decode it
with the library and check the graders deterministically, with no
LLM-as-judge. The task model lives here too because the graders are defined
entirely by it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from shortcut_lib.decode import DecodeError, decode_file

_TASKS_DIR = Path(__file__).parent / "tasks"


# ── Task model ───────────────────────────────────────────────────────


@dataclass
class Graders:
    name_contains: str | None = None
    min_actions: int = 1
    max_actions: int = 50
    must_contain: list[str] = field(default_factory=list)
    # Each inner list is an OR-group: the attempt passes the group if at
    # least one identifier in it appears. Use when several actions are
    # legitimate answers to the same prompt (e.g. "show the result" could
    # be ShowResult OR ShowNotification OR Alert).
    must_contain_any: list[list[str]] = field(default_factory=list)
    # Attempt FAILS if any listed identifier appears in the built shortcut.
    # Use to forbid a tempting-but-wrong action (e.g. a generic notification
    # where a specific one is required).
    must_not_contain: list[str] = field(default_factory=list)
    surfaces: list[str] = field(default_factory=list)
    decode_succeeds: bool = True
    recovery_expected: bool = False
    # Refuse-case. When True the attempt PASSES iff no .shortcut file was
    # produced; building anything FAILS. The content checks (must_contain /
    # must_contain_any / surfaces / decode_succeeds) are skipped entirely.
    expect_no_build: bool = False


@dataclass
class Task:
    id: str
    prompt: str
    graders: Graders

    @classmethod
    def from_file(cls, path: Path) -> Task:
        raw = json.loads(path.read_text())
        return cls(
            id=raw["id"],
            prompt=raw["prompt"],
            graders=Graders(**raw.get("graders", {})),
        )


def load_tasks(task_filter: str | None = None) -> list[Task]:
    files = sorted(_TASKS_DIR.glob("*.json"))
    tasks = [Task.from_file(f) for f in files]
    if task_filter:
        tasks = [t for t in tasks if task_filter in t.id]
    if not tasks:
        raise SystemExit(f"No tasks matched filter {task_filter!r}.")
    return tasks


# ── Grading ──────────────────────────────────────────────────────────


def grade(
    task: Task,
    output_dir: Path,
    built_path: str | None,
    saw_recovery: bool,
) -> tuple[bool, str]:
    """Return ``(passed, reason)`` for the attempt.

    The agent's emitted ``.shortcut`` file is the source of truth. We decode
    it and check the graders deterministically: no LLM-as-judge.
    """
    g = task.graders
    candidate = Path(built_path) if built_path else newest_shortcut(output_dir)
    have_build = candidate is not None and candidate.exists()

    # Refuse-cases short-circuit: the right answer is to build nothing.
    if g.expect_no_build:
        if have_build:
            stem = candidate.stem if candidate else "?"
            return False, f"expected refusal but built {stem}"
        return True, "refused as expected (no build)"

    if not have_build:
        return False, "no .shortcut file produced"

    if g.name_contains and g.name_contains.lower() not in candidate.stem.lower():
        return False, (
            f"filename {candidate.stem!r} missing required substring "
            f"{g.name_contains!r}"
        )

    try:
        decoded = decode_file(candidate)
    except DecodeError as exc:
        if g.decode_succeeds:
            return False, f"decode failed: {exc}"
        return True, "decode failed as expected"

    actions = decoded.workflow.get("WFWorkflowActions") or []
    identifiers = [a.get("WFWorkflowActionIdentifier") for a in actions]

    if not (g.min_actions <= len(actions) <= g.max_actions):
        return False, (
            f"action count {len(actions)} outside [{g.min_actions}, {g.max_actions}]"
        )
    missing = [ident for ident in g.must_contain if ident not in identifiers]
    if missing:
        return False, f"missing required action identifiers: {missing}"

    forbidden = [ident for ident in g.must_not_contain if ident in identifiers]
    if forbidden:
        return False, f"forbidden action identifiers present: {forbidden}"

    unsatisfied_groups = [
        group
        for group in g.must_contain_any
        if not any(ident in identifiers for ident in group)
    ]
    if unsatisfied_groups:
        return False, (f"none of any-of groups satisfied: {unsatisfied_groups}")

    surfaces = decoded.workflow.get("WFWorkflowTypes") or []
    missing_surfaces = [s for s in g.surfaces if s not in surfaces]
    if missing_surfaces:
        return False, f"missing required surfaces: {missing_surfaces}"

    if g.recovery_expected and not saw_recovery:
        return False, "task expected recovery from an error, but none was seen"

    return True, "ok"


def newest_shortcut(directory: Path) -> Path | None:
    files = sorted(
        directory.glob("*.shortcut"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return files[0] if files else None
