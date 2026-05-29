"""PlantUML source renderer for structured diagram types.

Generates .puml source from validated DiagramNode/DiagramEdge lists.
Handles: flowchart, sequence, uml_class, uml_activity, block_diagram, architecture.
"""

from hand2notes.core_models.blocks import DiagramBlock, DiagramEdge, DiagramNode
from hand2notes.core_models.enums import DiagramType


def render_plantuml(block: DiagramBlock) -> str:
    """Generate PlantUML source string from a validated DiagramBlock."""
    diagram_type = block.diagram_type
    nodes = block.nodes
    edges = block.edges

    if diagram_type == DiagramType.SEQUENCE:
        return _render_sequence(nodes, edges)
    elif diagram_type in (DiagramType.UML_CLASS,):
        return _render_class(nodes, edges)
    elif diagram_type == DiagramType.UML_ACTIVITY:
        return _render_activity(nodes, edges)
    elif diagram_type in (
        DiagramType.FLOWCHART,
        DiagramType.BLOCK_DIAGRAM,
        DiagramType.ARCHITECTURE,
    ):
        return _render_flowchart(nodes, edges)
    else:
        return _render_flowchart(nodes, edges)


def _render_flowchart(nodes: list[DiagramNode], edges: list[DiagramEdge]) -> str:
    lines = ["@startuml"]

    for node in nodes:
        node_type = (node.node_type or "").lower()
        if "start" in node_type or node.label.lower() in ("start", "begin"):
            lines.append("start")
        elif "end" in node_type or node.label.lower() in ("end", "stop", "finish"):
            lines.append("stop")
        elif "decision" in node_type or "diamond" in node_type:
            lines.append(f"if ({node.label}?) then (yes)")
            lines.append("  :Yes path;")
            lines.append("else (no)")
            lines.append("  :No path;")
            lines.append("endif")
        else:
            lines.append(f":{node.label};")

    if not nodes:
        for edge in edges:
            label = f" : {edge.label}" if edge.label else ""
            lines.append(f"[{edge.source_id}] --> [{edge.target_id}]{label}")

    lines.append("@enduml")
    return "\n".join(lines)


def _render_sequence(nodes: list[DiagramNode], edges: list[DiagramEdge]) -> str:
    lines = ["@startuml"]

    participant_ids: dict[str, str] = {}
    for node in nodes:
        node_type = (node.node_type or "").lower()
        if "actor" in node_type or "user" in node.label.lower():
            keyword = "actor"
        elif "database" in node_type or "db" in node_type:
            keyword = "database"
        else:
            keyword = "participant"
        alias = node.id.replace(" ", "_")
        participant_ids[node.id] = alias
        lines.append(f'{keyword} "{node.label}" as {alias}')

    lines.append("")

    for edge in edges:
        src = participant_ids.get(edge.source_id, edge.source_id)
        tgt = participant_ids.get(edge.target_id, edge.target_id)
        label = edge.label or ""
        arrow = "-->" if edge.label and "response" in edge.label.lower() else "->"
        lines.append(f"{src} {arrow} {tgt}: {label}")

    lines.append("@enduml")
    return "\n".join(lines)


def _render_class(nodes: list[DiagramNode], edges: list[DiagramEdge]) -> str:
    lines = ["@startuml"]
    for node in nodes:
        lines.append(f"class {node.label} {{")
        lines.append("}")
    for edge in edges:
        label = f" : {edge.label}" if edge.label else ""
        lines.append(f"{edge.source_id} --> {edge.target_id}{label}")
    lines.append("@enduml")
    return "\n".join(lines)


def _render_activity(nodes: list[DiagramNode], edges: list[DiagramEdge]) -> str:
    lines = ["@startuml"]
    lines.append("start")
    for node in nodes:
        node_type = (node.node_type or "").lower()
        if "decision" in node_type:
            lines.append(f"if ({node.label}?) then (yes)")
            lines.append("else (no)")
            lines.append("endif")
        elif "start" in node_type or "end" in node_type:
            pass
        else:
            lines.append(f":{node.label};")
    lines.append("stop")
    lines.append("@enduml")
    return "\n".join(lines)
