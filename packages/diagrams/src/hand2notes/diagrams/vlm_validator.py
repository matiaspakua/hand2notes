"""VLM response validator.

Parses the constrained JSON returned by either VLM client into typed
DiagramNode / DiagramEdge objects. Sets reconstruction_confidence and flags
malformed output with review_flag=True rather than crashing.
"""

import logging
from dataclasses import dataclass, field

from hand2notes.core_models.blocks import DiagramEdge, DiagramNode
from hand2notes.core_models.enums import DiagramType, EdgeDirection

log = logging.getLogger(__name__)

_VALID_DIAGRAM_TYPES = {t.value for t in DiagramType}
_VALID_DIRECTIONS = {d.value for d in EdgeDirection}


@dataclass
class ValidationResult:
    diagram_type: DiagramType = DiagramType.UNKNOWN
    nodes: list[DiagramNode] = field(default_factory=list)
    edges: list[DiagramEdge] = field(default_factory=list)
    reconstruction_confidence: float = 0.0
    review_flag: bool = False
    raw_json: dict | None = None


def validate_vlm_response(raw: dict) -> ValidationResult:
    """Parse and validate a VLM JSON response into typed structures.

    Invalid or missing fields fall back to safe defaults and set review_flag=True
    so the user can manually inspect the output.
    """
    result = ValidationResult(raw_json=raw)
    review_needed = False

    # --- diagram type ---
    raw_type = raw.get("type", "")
    if raw_type in _VALID_DIAGRAM_TYPES:
        result.diagram_type = DiagramType(raw_type)
    else:
        log.warning("Unknown diagram type %r — defaulting to unknown", raw_type)
        result.diagram_type = DiagramType.UNKNOWN
        review_needed = True

    # --- confidence ---
    raw_conf = raw.get("confidence", 0.0)
    try:
        conf = float(raw_conf)
        result.reconstruction_confidence = max(0.0, min(1.0, conf))
    except (TypeError, ValueError):
        log.warning("Invalid confidence value %r", raw_conf)
        result.reconstruction_confidence = 0.0
        review_needed = True

    # --- nodes ---
    raw_nodes = raw.get("nodes", [])
    if not isinstance(raw_nodes, list):
        log.warning("nodes field is not a list")
        raw_nodes = []
        review_needed = True

    for i, n in enumerate(raw_nodes):
        if not isinstance(n, dict):
            log.warning("Node %d is not a dict: %r", i, n)
            review_needed = True
            continue
        node_id = str(n.get("id", f"node_{i}"))
        label = str(n.get("label", node_id))
        node_type = n.get("node_type") or None
        result.nodes.append(DiagramNode(id=node_id, label=label, node_type=node_type))

    # --- edges ---
    raw_edges = raw.get("edges", [])
    if not isinstance(raw_edges, list):
        log.warning("edges field is not a list")
        raw_edges = []
        review_needed = True

    for i, e in enumerate(raw_edges):
        if not isinstance(e, dict):
            log.warning("Edge %d is not a dict: %r", i, e)
            review_needed = True
            continue
        source = str(e.get("source_id", ""))
        target = str(e.get("target_id", ""))
        if not source or not target:
            log.warning("Edge %d missing source_id or target_id", i)
            review_needed = True
            continue
        raw_dir = e.get("direction", EdgeDirection.FORWARD.value)
        direction = EdgeDirection(raw_dir) if raw_dir in _VALID_DIRECTIONS else EdgeDirection.FORWARD
        result.edges.append(
            DiagramEdge(
                source_id=source,
                target_id=target,
                label=e.get("label") or None,
                direction=direction,
            )
        )

    result.review_flag = review_needed or result.reconstruction_confidence < 0.5
    return result
