"""Shortcut builder — collects schema actions and emits the workflow dict."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from shortcut_lib.encode import SignMode, encode_to_bplist, sign_to_file
from shortcut_lib.schema.base import Action, SchemaError


def _new_workflow_uuid() -> str:
    return str(uuid4()).upper()


# Subset of WFWorkflowTypes / WFQuickActionSurfaces values. Apple's full
# enum is in `~/Documents/FMP/tech/Apple_Shortcuts/Design_Intent.md` (or
# the iOS-Shortcuts-Reference attribution in docs/sources.md). Strings
# pass through verbatim, so unknowns aren't a hard error.
SURFACE_TO_TYPE: dict[str, str] = {
    "watch": "Watch",
    "widget": "NCWidget",
    "share": "ActionExtension",
    "menubar": "MenuBar",
    "quick-action": "QuickActions",
    "sleep": "Sleep",
}


@dataclass
class Shortcut:
    """An authored shortcut.

    Build by adding Actions or control-flow constructs. Each ``add()``
    returns the same object for chaining and so the caller can reference
    its output:

        s = Shortcut(name="Demo")
        text = s.add(DictateText())
        s.add(SetClipboard(input=text))
        s.save_signed("Demo.shortcut")

    Args:
        name: Display name shown in the Shortcuts app.
        surfaces: Where this shortcut appears — any of "watch",
            "widget", "share", "menubar", "quick-action", "sleep". Or
            pass the raw Apple strings directly.
        min_client: Minimum Shortcuts client version. Defaults to 900
            (~iOS 16); raise for actions that need newer features.
    """

    name: str = "Untitled"
    surfaces: list[str] = field(default_factory=list)
    min_client: int = 900
    icon_glyph: int = 61512  # default to a generic icon
    icon_color: int = 4282601983  # red
    workflow_identifier: str = field(default_factory=_new_workflow_uuid)
    accepted_input: list[str] = field(default_factory=list)
    output_classes: list[str] = field(default_factory=list)
    actions: list[Action] = field(default_factory=list)

    def add(self, action: Action) -> Action:
        """Append an action; return it so its output can be referenced."""
        if not isinstance(action, Action):
            raise SchemaError(
                f"Shortcut.add expects an Action, got {type(action).__name__}"
            )
        self.actions.append(action)
        return action

    def extend(self, actions: list[Action]) -> None:
        """Append several actions in order."""
        for a in actions:
            self.add(a)

    def to_workflow(self) -> dict[str, Any]:
        """Emit the WFWorkflow* top-level dict ready for encoding."""
        action_dicts: list[dict[str, Any]] = []
        for action in self.actions:
            action_dicts.extend(action.to_actions())
        self._resolve_self_refs(action_dicts)

        # NB: WFWorkflowName is intentionally not emitted. None of the decoded
        # samples contain it; the Shortcuts app derives the display name from
        # the imported file's filename. Keeping it in self.name for
        # composition (RunWorkflow.workflowName) and signed-file naming only.
        types = [SURFACE_TO_TYPE.get(s, s) for s in self.surfaces]
        return {
            "WFWorkflowMinimumClientVersion": self.min_client,
            "WFWorkflowMinimumClientVersionString": str(self.min_client),
            "WFWorkflowClientVersion": "4033.0.4.3",
            "WFWorkflowIcon": {
                "WFWorkflowIconGlyphNumber": self.icon_glyph,
                "WFWorkflowIconStartColor": self.icon_color,
            },
            "WFWorkflowTypes": types,
            "WFQuickActionSurfaces": [],
            "WFWorkflowInputContentItemClasses": list(self.accepted_input),
            "WFWorkflowOutputContentItemClasses": list(self.output_classes),
            "WFWorkflowImportQuestions": [],
            "WFWorkflowHasOutputFallback": False,
            "WFWorkflowHasShortcutInputVariables": False,
            "WFWorkflowActions": action_dicts,
        }

    def to_bplist(self) -> bytes:
        """Encode as a binary plist (unsigned)."""
        return encode_to_bplist(self.to_workflow())

    def save_signed(self, path: Path | str, *, mode: SignMode = "anyone") -> None:
        """Encode, sign via the macOS shortcuts CLI, and write to disk."""
        sign_to_file(self.to_workflow(), path, mode=mode)

    def _resolve_self_refs(self, action_dicts: list[dict[str, Any]]) -> None:
        """Replace `__SELF__` markers from RunWorkflow(target='self')."""
        for action in action_dicts:
            params = action.get("WFWorkflowActionParameters") or {}
            wf = params.get("WFWorkflow")
            if isinstance(wf, dict) and wf.get("workflowIdentifier") == "__SELF__":
                wf["workflowIdentifier"] = self.workflow_identifier
                wf["workflowName"] = self.name
            if params.get("WFWorkflowName") == "__SELF__":
                params["WFWorkflowName"] = self.name
