"""Tests for the consolidated validate_workflow entry point.

Each test targets one validator or one cross-cutting property (stable ordering).
Workflow dicts are hand-crafted or built via the schema layer to keep the tests
fast and independent of the CLI / file-system.
"""

from __future__ import annotations

from shortcut_lib.builder import Shortcut
from shortcut_lib.schema.actions.dictate_text import DictateText
from shortcut_lib.schema.actions.set_clipboard import SetClipboard
from shortcut_lib.schema.actions.set_variable import SetVariable  # noqa: F401
from shortcut_lib.validate import ValidationFinding, validate_workflow

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_UUID_A = "AAAA1111-0000-0000-0000-000000000001"
_UUID_B = "BBBB2222-0000-0000-0000-000000000002"
_UUID_C = "CCCC3333-0000-0000-0000-000000000003"


def _codes(findings: list[ValidationFinding]) -> list[str]:
    return [f.code for f in findings]


def _minimal_workflow(actions: list[dict]) -> dict:
    """Wrap actions in a bare workflow dict for testing."""
    return {
        "WFWorkflowActions": actions,
        "WFWorkflowImportQuestions": [],
    }


# ---------------------------------------------------------------------------
# 1. Clean workflow → no findings
# ---------------------------------------------------------------------------


def test_validate_emits_no_findings_for_clean_workflow() -> None:
    """Schema-authored dictate-to-clipboard shortcut returns an empty list."""
    s = Shortcut(name="Test Clean")
    text = s.add(DictateText())
    s.add(SetClipboard(input=text))
    findings = validate_workflow(s.to_workflow())
    assert findings == [], f"Expected no findings, got: {findings}"


# ---------------------------------------------------------------------------
# 2. envelope-mismatch (error)
# ---------------------------------------------------------------------------


def test_validate_envelope_mismatch_flagged() -> None:
    """WFURL on DownloadURL with WFTextTokenAttachment (oracle says WFTextTokenString only)."""
    # Oracle observation: WFURL slot on is.workflow.actions.downloadurl
    # only ever carries WFTextTokenString.  Emitting WFTextTokenAttachment
    # is a mismatch that will cause the URL to read as empty at runtime.
    workflow = {
        "WFWorkflowActions": [
            # SetVariable first so "SomeURL" is in scope (avoids variable-not-set noise).
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.setvariable",
                "WFWorkflowActionParameters": {
                    "UUID": _UUID_B,
                    "WFVariableName": "SomeURL",
                },
            },
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.downloadurl",
                "WFWorkflowActionParameters": {
                    "UUID": _UUID_A,
                    "WFURL": {
                        "Value": {"VariableName": "SomeURL", "Type": "Variable"},
                        "WFSerializationType": "WFTextTokenAttachment",  # wrong
                    },
                },
            },
        ],
        "WFWorkflowImportQuestions": [],
    }
    findings = validate_workflow(workflow)
    mismatch = [f for f in findings if f.code == "envelope-mismatch"]
    assert len(mismatch) == 1
    f = mismatch[0]
    assert f.severity == "error"
    assert f.action_identifier == "is.workflow.actions.downloadurl"
    assert f.parameter_key == "WFURL"
    assert "WFTextTokenAttachment" in f.message
    assert "WFTextTokenString" in f.message


# ---------------------------------------------------------------------------
# 3. variable-not-set (error)
# ---------------------------------------------------------------------------


def test_validate_variable_not_set_flagged() -> None:
    """NamedVar reference to an undeclared variable is flagged as an error."""
    workflow = _minimal_workflow(
        [
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.setclipboard",
                "WFWorkflowActionParameters": {
                    "UUID": _UUID_A,
                    "WFInput": {
                        "Value": {"VariableName": "DoesNotExist", "Type": "Variable"},
                        "WFSerializationType": "WFTextTokenAttachment",
                    },
                },
            }
        ]
    )
    findings = validate_workflow(workflow)
    not_set = [f for f in findings if f.code == "variable-not-set"]
    assert len(not_set) == 1
    f = not_set[0]
    assert f.severity == "error"
    assert f.action_index == 0
    assert "DoesNotExist" in f.message


def test_validate_variable_set_before_use_is_clean() -> None:
    """SetVariable then NamedVar reference — no variable-not-set finding."""
    s = Shortcut(name="VarTest")
    var = s.set("MyToken", "hello")
    s.add(SetClipboard(input=var))
    findings = validate_workflow(s.to_workflow())
    assert all(f.code != "variable-not-set" for f in findings)


# ---------------------------------------------------------------------------
# 4. output-uuid-orphan (error)
# ---------------------------------------------------------------------------


def test_validate_output_uuid_orphan_flagged() -> None:
    """ActionOutput reference to a UUID not present in any earlier action is flagged."""
    workflow = _minimal_workflow(
        [
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.setclipboard",
                "WFWorkflowActionParameters": {
                    "UUID": _UUID_A,
                    "WFInput": {
                        "Value": {
                            "OutputName": "Dictated Text",
                            "OutputUUID": _UUID_B,  # no action has this UUID
                            "Type": "ActionOutput",
                        },
                        "WFSerializationType": "WFTextTokenAttachment",
                    },
                },
            }
        ]
    )
    findings = validate_workflow(workflow)
    orphans = [f for f in findings if f.code == "output-uuid-orphan"]
    assert len(orphans) == 1
    f = orphans[0]
    assert f.severity == "error"
    assert f.action_index == 0
    assert _UUID_B in f.message


def test_validate_output_uuid_valid_back_ref_is_clean() -> None:
    """ActionOutput reference to a preceding action's UUID is valid (no finding)."""
    s = Shortcut(name="BackRef")
    text = s.add(DictateText())
    s.add(SetClipboard(input=text))
    findings = validate_workflow(s.to_workflow())
    assert all(f.code != "output-uuid-orphan" for f in findings)


def test_validate_output_uuid_forward_reference_flagged() -> None:
    """ActionOutput referencing a later action's UUID is flagged.

    iOS resolves ActionOutput references in execution order; a forward
    reference (action 0 referencing action 1's UUID) cannot resolve
    because action 1 hasn't run yet when action 0 emits.
    """
    workflow = _minimal_workflow(
        [
            # Action 0 references action 1's UUID — invalid forward ref.
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.setclipboard",
                "WFWorkflowActionParameters": {
                    "UUID": _UUID_A,
                    "WFInput": {
                        "Value": {
                            "OutputName": "Dictated Text",
                            "OutputUUID": _UUID_B,  # belongs to action 1, not yet emitted
                            "Type": "ActionOutput",
                        },
                        "WFSerializationType": "WFTextTokenAttachment",
                    },
                },
            },
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.dictatetext",
                "WFWorkflowActionParameters": {"UUID": _UUID_B},
            },
        ]
    )
    findings = validate_workflow(workflow)
    orphans = [f for f in findings if f.code == "output-uuid-orphan"]
    assert len(orphans) == 1
    f = orphans[0]
    assert f.severity == "error"
    assert f.action_index == 0
    # Message should reference the forward UUID; existence later in the
    # flow doesn't make a forward reference valid.
    assert _UUID_B in f.message


# ---------------------------------------------------------------------------
# 5. import-question-action-index-out-of-range (error)
# ---------------------------------------------------------------------------


def test_validate_import_question_index_out_of_range() -> None:
    """ActionIndex equal to len(actions) (off-by-one) is flagged as an error."""
    workflow = {
        "WFWorkflowActions": [
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.gettext",
                "WFWorkflowActionParameters": {"UUID": _UUID_A},
            }
        ],
        "WFWorkflowImportQuestions": [
            {
                "ActionIndex": 1,  # len(actions) == 1, so max valid is 0
                "Category": "Parameter",
                "ParameterKey": "WFTextActionText",
                "Text": "Enter something",
            }
        ],
    }
    findings = validate_workflow(workflow)
    oob = [f for f in findings if f.code == "import-question-action-index-out-of-range"]
    assert len(oob) == 1
    f = oob[0]
    assert f.severity == "error"
    assert "1" in f.message


def test_validate_import_question_valid_index_is_clean() -> None:
    """ActionIndex of 0 with one action present — no finding."""
    workflow = {
        "WFWorkflowActions": [
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.gettext",
                "WFWorkflowActionParameters": {"UUID": _UUID_A},
            }
        ],
        "WFWorkflowImportQuestions": [
            {
                "ActionIndex": 0,
                "Category": "Parameter",
                "ParameterKey": "WFTextActionText",
                "Text": "Enter something",
            }
        ],
    }
    findings = validate_workflow(workflow)
    oob = [f for f in findings if f.code == "import-question-action-index-out-of-range"]
    assert oob == []


# ---------------------------------------------------------------------------
# 6. Stable sort order: (action_index, code)
# ---------------------------------------------------------------------------


def test_validate_findings_stable_order() -> None:
    """Multiple errors from different validators are sorted by (action_index, code)."""
    # Action 0: output-uuid-orphan (references _UUID_C which doesn't exist earlier)
    # Action 1: variable-not-set (references "Ghost" which was never set)
    # Import question: action-index-out-of-range (no action_index — sorts last)
    workflow = {
        "WFWorkflowActions": [
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.setclipboard",
                "WFWorkflowActionParameters": {
                    "UUID": _UUID_A,
                    "WFInput": {
                        "Value": {
                            "OutputName": "X",
                            "OutputUUID": _UUID_C,
                            "Type": "ActionOutput",
                        },
                        "WFSerializationType": "WFTextTokenAttachment",
                    },
                },
            },
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.setvariable",
                "WFWorkflowActionParameters": {
                    "UUID": _UUID_B,
                    "WFVariableName": "X",
                    "WFInput": {
                        "Value": {"VariableName": "Ghost", "Type": "Variable"},
                        "WFSerializationType": "WFTextTokenAttachment",
                    },
                },
            },
        ],
        "WFWorkflowImportQuestions": [
            {
                "ActionIndex": 5,  # out of range — action_index is None in finding
                "Category": "Parameter",
                "ParameterKey": "WFVariableName",
                "Text": "Enter var name",
            }
        ],
    }
    findings = validate_workflow(workflow)
    assert len(findings) >= 3, f"Expected at least 3 findings, got {findings}"

    # Findings with action_index should precede those without.
    indexed = [f for f in findings if f.action_index is not None]
    unindexed = [f for f in findings if f.action_index is None]

    # Within indexed findings: sorted by (action_index, code).
    # action_index is int (not None) here — filtered above.
    for i in range(len(indexed) - 1):
        a, b = indexed[i], indexed[i + 1]
        a_idx = a.action_index or 0
        b_idx = b.action_index or 0
        assert (a_idx, a.code) <= (b_idx, b.code), (
            f"Findings out of order at position {i}: "
            f"({a.action_index}, {a.code!r}) > ({b.action_index}, {b.code!r})"
        )

    # All unindexed findings come after all indexed findings in the list.
    if indexed and unindexed:
        last_indexed_pos = max(findings.index(f) for f in indexed)
        first_unindexed_pos = min(findings.index(f) for f in unindexed)
        assert last_indexed_pos < first_unindexed_pos


# ---------------------------------------------------------------------------
# 7. unknown-envelope → info severity
# ---------------------------------------------------------------------------


def test_validate_oracle_unknown_envelope_is_info() -> None:
    """A WFSerializationType the oracle has never seen anywhere → info finding."""
    # Use a completely fictional action identifier so there are no oracle
    # observations for (action, slot), then use a fictional type that is
    # also absent from every observed type in the oracle.
    workflow = _minimal_workflow(
        [
            {
                "WFWorkflowActionIdentifier": "com.example.fictional.action",
                "WFWorkflowActionParameters": {
                    "UUID": _UUID_A,
                    "SomeParam": {
                        "Value": "data",
                        "WFSerializationType": "WFTotallyInventedType12345",
                    },
                },
            }
        ]
    )
    findings = validate_workflow(workflow)
    unknown = [f for f in findings if f.code == "unknown-envelope"]
    assert len(unknown) == 1
    f = unknown[0]
    assert f.severity == "info"
    assert f.action_index == 0
    assert "WFTotallyInventedType12345" in f.message


# ---------------------------------------------------------------------------
# 8. use-before-set — sequential variable scope (regression for deep-review B)
# ---------------------------------------------------------------------------


def test_validate_use_before_set_flagged() -> None:
    """Action 0 referencing MyVar via NamedVar wire, action 1 sets it — flagged.

    The pre-refactor validator pre-collected all SetVariable names globally,
    making use-before-set invisible.  After the sequential-walk fix, action 0's
    reference is checked before action 1's SetVariable is accumulated, so the
    finding is emitted at action_index=0.
    """
    workflow = _minimal_workflow(
        [
            # Action 0: references MyVar which has not been set yet.
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.setclipboard",
                "WFWorkflowActionParameters": {
                    "UUID": _UUID_A,
                    "WFInput": {
                        "Value": {"VariableName": "MyVar", "Type": "Variable"},
                        "WFSerializationType": "WFTextTokenAttachment",
                    },
                },
            },
            # Action 1: binds MyVar — too late for action 0.
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.setvariable",
                "WFWorkflowActionParameters": {
                    "UUID": _UUID_B,
                    "WFVariableName": "MyVar",
                },
            },
        ]
    )
    findings = validate_workflow(workflow)
    not_set = [f for f in findings if f.code == "variable-not-set"]
    assert len(not_set) == 1, (
        f"Expected exactly 1 variable-not-set finding, got: {not_set}"
    )
    f = not_set[0]
    assert f.severity == "error"
    assert f.action_index == 0
    assert "MyVar" in f.message


def test_validate_set_then_use_is_clean() -> None:
    """SetVariable at action 0 then NamedVar reference at action 1 — no finding."""
    workflow = _minimal_workflow(
        [
            # Action 0: binds MyVar.
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.setvariable",
                "WFWorkflowActionParameters": {
                    "UUID": _UUID_A,
                    "WFVariableName": "MyVar",
                },
            },
            # Action 1: references MyVar — valid, set at action 0.
            {
                "WFWorkflowActionIdentifier": "is.workflow.actions.setclipboard",
                "WFWorkflowActionParameters": {
                    "UUID": _UUID_B,
                    "WFInput": {
                        "Value": {"VariableName": "MyVar", "Type": "Variable"},
                        "WFSerializationType": "WFTextTokenAttachment",
                    },
                },
            },
        ]
    )
    findings = validate_workflow(workflow)
    not_set = [f for f in findings if f.code == "variable-not-set"]
    assert not_set == [], f"Expected no variable-not-set findings, got: {not_set}"


# ---------------------------------------------------------------------------
# 9. Top-level package import symmetry
# ---------------------------------------------------------------------------


def test_top_level_import() -> None:
    """validate_workflow and ValidationFinding are importable from the package root."""
    from shortcut_lib import ValidationFinding, validate_workflow

    assert callable(validate_workflow)
    assert ValidationFinding is not None
