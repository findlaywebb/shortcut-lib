"""Scan decoded samples for observed envelope types, writing a JSON oracle.

Walk every ``samples/decoded/*.xml`` (and ``samples/decoded/private/*.xml``),
parse each as a plist, and record the ``WFSerializationType`` envelope used
for every dict-typed parameter slot.  Emit ``data/observed_envelope_types.json``
as a living CI artefact.

Run:
    uv run python scripts/scan_envelope_types.py

The output JSON is the oracle for ``tests/test_envelope_oracle.py``: if the
schema emits an envelope type that the corpus has never seen for a given
(action, slot) pair, the oracle test flags it.

Separate tracking:

- ``slots``      — (action, slot) pairs where at least one sample had a dict
  envelope.  The ``envelopes`` sub-key records each observed ``WFSerializationType``
  with a count and up to five sample citations.
- ``bare_string_slots`` — (action, slot) pairs where the slot's value was a
  bare string scalar in *every* sample observation (never a dict envelope).
"""

from __future__ import annotations

import json
import logging
import plistlib
import sys
from datetime import UTC, datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

REPO = Path(__file__).resolve().parent.parent
SAMPLES_DIR = REPO / "samples" / "decoded"
OUT_FILE = REPO / "data" / "observed_envelope_types.json"

# Maximum sample citations stored per (action, slot, envelope_type) triple.
_MAX_CITATIONS = 5


def _collect_xml_files(root: Path) -> list[Path]:
    """Return all XML plist files under *root* (including private sub-dir)."""
    files = sorted(root.glob("*.xml"))
    private = root / "private"
    if private.is_dir():
        files += sorted(private.glob("*.xml"))
    return files


def _sample_citation(xml_path: Path, action_idx: int) -> str:
    """Return a stable citation string pointing at a specific action in a file.

    Format: ``samples/decoded/<name>.xml:<n>`` (relative to repo root).
    """
    rel = xml_path.relative_to(REPO)
    return f"{rel}:{action_idx}"


def _walk_slots(
    params: dict,
    ident: str,
    citation: str,
    envelope_hits: dict,
    bare_string_hits: dict,
) -> None:
    """Record slot envelope types from one action's parameter dict.

    Args:
        params: ``WFWorkflowActionParameters`` dict for one action.
        ident: The action's ``WFWorkflowActionIdentifier``.
        citation: Pre-built sample citation string for this action.
        envelope_hits: Mutable mapping that accumulates dict-envelope hits.
            Shape: ``{ident: {slot: {stype: [citations]}}}``.
        bare_string_hits: Mutable mapping that accumulates bare-string hits.
            Shape: ``{ident: {slot: count}}``.
    """
    for slot, value in params.items():
        if slot in ("UUID", "CustomOutputName"):
            continue
        if isinstance(value, dict) and "WFSerializationType" in value:
            stype = value["WFSerializationType"]
            slot_map = envelope_hits.setdefault(ident, {}).setdefault(slot, {})
            citations = slot_map.setdefault(stype, [])
            if len(citations) < _MAX_CITATIONS:
                citations.append(citation)
        elif isinstance(value, str):
            slot_map = bare_string_hits.setdefault(ident, {})
            slot_map[slot] = slot_map.get(slot, 0) + 1


def scan(samples_dir: Path) -> dict:
    """Scan all decoded XML samples and return the raw observation dicts.

    Returns:
        Dict with keys ``xml_files``, ``total_actions``, ``envelope_hits``,
        ``bare_string_hits``.
    """
    xml_files = _collect_xml_files(samples_dir)
    if not xml_files:
        logger.warning("No XML files found under %s", samples_dir)

    total_actions = 0
    envelope_hits: dict = {}  # {ident: {slot: {stype: [citations]}}}
    bare_string_hits: dict = {}  # {ident: {slot: count}}

    for xml_path in xml_files:
        try:
            wf = plistlib.loads(xml_path.read_bytes())
        except Exception:
            logger.exception("Failed to parse %s", xml_path)
            continue

        actions = wf.get("WFWorkflowActions", [])
        for idx, action in enumerate(actions):
            ident = action.get("WFWorkflowActionIdentifier", "")
            params = action.get("WFWorkflowActionParameters", {})
            if not ident or not isinstance(params, dict):
                continue
            total_actions += 1
            citation = _sample_citation(xml_path, idx)
            _walk_slots(
                params,
                ident,
                citation,
                envelope_hits,
                bare_string_hits,
            )

    return {
        "xml_files": xml_files,
        "total_actions": total_actions,
        "envelope_hits": envelope_hits,
        "bare_string_hits": bare_string_hits,
    }


def _build_output(scan_result: dict) -> dict:
    """Build the structured JSON output from raw scan data.

    Pure-string slots that *also* appeared with dict envelopes are omitted
    from ``bare_string_slots`` (the envelope record is the richer signal).
    A slot is in ``bare_string_slots`` only if it *never* appeared as a dict
    in any sample.
    """
    xml_files = scan_result["xml_files"]
    total_actions = scan_result["total_actions"]
    envelope_hits: dict = scan_result["envelope_hits"]
    bare_string_hits: dict = scan_result["bare_string_hits"]

    # Build the ``slots`` output — sorted by identifier then slot name.
    slots_out: dict = {}
    for ident in sorted(envelope_hits):
        slots_out[ident] = {}
        for slot in sorted(envelope_hits[ident]):
            envelopes: dict = {}
            for stype in sorted(envelope_hits[ident][slot]):
                citations = envelope_hits[ident][slot][stype]
                envelopes[stype] = {
                    "count": len(citations),
                    "samples": sorted(citations),
                }
            slots_out[ident][slot] = {"envelopes": envelopes}

    # Build ``bare_string_slots`` — exclude any slot that also appears in
    # envelope_hits (polymorphic slots belong in the richer record).
    bare_out: dict = {}
    for ident in sorted(bare_string_hits):
        envelope_slots = set(envelope_hits.get(ident, {}).keys())
        pure_string_slots = sorted(
            slot for slot in bare_string_hits[ident] if slot not in envelope_slots
        )
        if pure_string_slots:
            bare_out[ident] = pure_string_slots

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "samples_scanned": len(xml_files),
        "actions_observed": total_actions,
        "slots": slots_out,
        "bare_string_slots": bare_out,
    }


def main() -> int:
    """Entry point: scan samples, write JSON oracle, print summary."""
    result = scan(SAMPLES_DIR)
    output = _build_output(result)

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")

    envelope_hits = result["envelope_hits"]
    pair_count = sum(len(slots) for slots in envelope_hits.values())

    logger.info("Scanned %d samples", output["samples_scanned"])
    logger.info("Observed %d total actions", output["actions_observed"])
    logger.info("Recorded %d (action, slot) pairs with dict envelopes", pair_count)
    logger.info("Wrote %s", OUT_FILE)

    # Report polymorphic slots (multiple envelope types for same slot).
    poly = [
        (ident, slot)
        for ident, slots in envelope_hits.items()
        for slot, stypes in slots.items()
        if len(stypes) > 1
    ]
    if poly:
        logger.info("Polymorphic slots (multiple envelope types):")
        for ident, slot in sorted(poly):
            types = sorted(envelope_hits[ident][slot].keys())
            logger.info("  %s / %s: %s", ident, slot, types)

    return 0


if __name__ == "__main__":
    sys.exit(main())
