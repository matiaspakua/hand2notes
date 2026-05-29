"""draw.io XML renderer for free-form and graph diagram types.

Generates .drawio XML for annotated_sketch, graph_network, and other geometry types.
"""

import xml.etree.ElementTree as ET
from uuid import uuid4

from hand2notes.core_models.blocks import DiagramBlock


def render_drawio(block: DiagramBlock) -> str:
    """Generate draw.io XML string from a validated DiagramBlock."""
    mxGraphModel = ET.Element(
        "mxGraphModel",
        attrib={
            "dx": "1422",
            "dy": "762",
            "grid": "1",
            "gridSize": "10",
            "guides": "1",
            "tooltips": "1",
            "connect": "1",
            "arrows": "1",
            "fold": "1",
            "page": "1",
            "pageScale": "1",
            "pageWidth": "1169",
            "pageHeight": "827",
            "math": "0",
            "shadow": "0",
        },
    )
    root = ET.SubElement(mxGraphModel, "root")
    ET.SubElement(root, "mxCell", id="0")
    ET.SubElement(root, "mxCell", id="1", parent="0")

    node_cell_ids: dict[str, str] = {}
    x, y = 100, 100
    for node in block.nodes:
        cell_id = str(uuid4())
        node_cell_ids[node.id] = cell_id
        cell = ET.SubElement(
            root,
            "mxCell",
            id=cell_id,
            value=node.label,
            style="rounded=1;whiteSpace=wrap;html=1;",
            vertex="1",
            parent="1",
        )
        ET.SubElement(
            cell,
            "mxGeometry",
            x=str(x),
            y=str(y),
            width="120",
            height="60",
            **{"as": "geometry"},
        )
        x += 160
        if x > 900:
            x = 100
            y += 100

    for edge in block.edges:
        src_cell = node_cell_ids.get(edge.source_id, "")
        tgt_cell = node_cell_ids.get(edge.target_id, "")
        if not src_cell or not tgt_cell:
            continue
        edge_id = str(uuid4())
        cell = ET.SubElement(
            root,
            "mxCell",
            id=edge_id,
            value=edge.label or "",
            style="edgeStyle=orthogonalEdgeStyle;",
            edge="1",
            source=src_cell,
            target=tgt_cell,
            parent="1",
        )
        ET.SubElement(cell, "mxGeometry", relative="1", **{"as": "geometry"})

    tree = ET.ElementTree(mxGraphModel)
    ET.indent(tree, space="  ")
    import io

    buf = io.StringIO()
    buf.write("<?xml version='1.0' encoding='utf-8'?>\n")
    tree.write(buf, encoding="unicode", xml_declaration=False)
    return buf.getvalue()
