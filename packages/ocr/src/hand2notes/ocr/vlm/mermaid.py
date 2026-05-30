"""Mermaid diagram sanitisation — the safety net for unreliable VLM diagram output.

Vision models emit Mermaid that is frequently malformed: duplicate edges, the same
box re-numbered into many nodes, runaway loops, or fences truncated mid-block. These
helpers clean what is salvageable and discard what is degenerate, so the surrounding
text is never lost to a broken diagram.
"""

from __future__ import annotations

import re

# A diagram with more unique edges than this is almost certainly a VLM runaway
# (the model looping over a table); discard it rather than emit garbage.
MERMAID_MAX_EDGES = 25
MERMAID_FENCE_RE = re.compile(r"```mermaid\n(.*?)\n```", re.DOTALL)
_EDGE_RE = re.compile(r"^(.*?)\s-->(?:\|[^|]*\|)?\s(.*?)\s*$")
_NODE_RE = re.compile(r"^([A-Za-z0-9_]+)\s*(?:\[(.*)\])?$")
_EDGE_LABEL_RE = re.compile(r"-->\|([^|]*)\|")


def _node_parts(node: str) -> tuple[str, str | None]:
    """Split a node reference into (id, optional [label] text)."""
    m = _NODE_RE.match(node.strip())
    if not m:
        return node.strip(), None
    return m.group(1), m.group(2)


def sanitize_mermaid_body(body: str) -> str | None:
    """Clean a Mermaid flowchart body; return cleaned text, or None to discard.

    - De-duplicates identical edges (VLMs repeat them).
    - Collapses nodes that share the same [label] onto one node id, so a loop that
      re-numbers the same two boxes (A, AB, AC … all "[ICTA]") becomes one edge.
    - Discards the whole block when it still looks like a runaway (too many distinct
      edges, a huge fan-out, or many more raw edge lines than unique edges).
    """
    header = ""
    edges: list[tuple[str, str, str]] = []  # (raw_src, raw_dst, edge_label)
    for raw_line in body.splitlines():
        s = raw_line.strip()
        if not s:
            continue
        if s.startswith(("flowchart", "graph")) and not header:
            header = s
            continue
        m = _EDGE_RE.match(s)
        if m:
            label_m = _EDGE_LABEL_RE.search(s)
            edge_label = label_m.group(1).strip() if label_m else ""
            edges.append((m.group(1).strip(), m.group(2).strip(), edge_label))

    if not header:
        header = "flowchart TD"
    if not edges:
        return None

    # Resolve each raw node id (e.g. "A") to its declared [label] wherever one appears,
    # so bare-id references on continuation lines merge with their box.
    id_to_label: dict[str, str] = {}
    for src, dst, _ in edges:
        for node in (src, dst):
            nid, lbl = _node_parts(node)
            if lbl and nid not in id_to_label:
                id_to_label[nid] = lbl

    def label_of(node: str) -> str:
        nid, lbl = _node_parts(node)
        return (lbl or id_to_label.get(nid, nid)).strip().lower()

    label_to_id: dict[str, str] = {}
    label_to_decl: dict[str, str] = {}
    seen_edges: set[tuple[str, str, str]] = set()
    clean_edges: list[tuple[str, str, str]] = []
    fanout: dict[str, set[str]] = {}
    next_id = 0
    for src, dst, lbl in edges:
        for node in (src, dst):
            key = label_of(node)
            if key not in label_to_id:
                nid = f"N{next_id}"
                next_id += 1
                label_to_id[key] = nid
                _, decl = _node_parts(node)
                display = decl or id_to_label.get(_node_parts(node)[0], node)
                label_to_decl[key] = f"{nid}[{display}]"
        sid, did = label_to_id[label_of(src)], label_to_id[label_of(dst)]
        if sid == did:
            continue
        sig = (sid, did, lbl)
        if sig in seen_edges:
            continue
        seen_edges.add(sig)
        clean_edges.append(sig)
        fanout.setdefault(sid, set()).add(did)

    if not clean_edges:
        return None
    if len(clean_edges) > MERMAID_MAX_EDGES or max(len(t) for t in fanout.values()) > 12:
        return None
    if len(edges) > 15 and len(edges) > 3 * len(clean_edges):
        return None

    out = [header]
    for decl in label_to_decl.values():
        out.append(f"    {decl}")
    for sid, did, lbl in clean_edges:
        arrow = f" -->|{lbl}| " if lbl else " --> "
        out.append(f"    {sid}{arrow}{did}")
    return "\n".join(out)


def sanitize_mermaid_blocks(text: str) -> str:
    """Sanitize every ```mermaid block; drop blocks that are degenerate runaways."""

    def repl(m: re.Match) -> str:
        cleaned = sanitize_mermaid_body(m.group(1))
        if cleaned is None:
            return ""  # discard degenerate diagram, keep surrounding text
        return f"```mermaid\n{cleaned}\n```"

    return MERMAID_FENCE_RE.sub(repl, text)


def close_dangling_fence(text: str) -> str:
    """Append a closing ``` when a ```mermaid block was left unterminated.

    A runaway diagram pass can be truncated by num_predict mid-block, leaving an open
    fence; closing it lets the sanitizer see (and discard) the block.
    """
    if text.count("```") % 2 == 1:
        return text + "\n```"
    return text


def unwrap_outer_fence(text: str) -> str:
    """Strip a code fence that wraps the WHOLE answer, preserving inner fences.

    The model sometimes wraps its entire reply in ```markdown … ``` while also emitting
    inner ```mermaid blocks. Remove only the outer wrapper, never the diagram fences.
    Uses regex to match the outer pair so inner fences are never touched.
    """
    stripped = text.strip()
    if not stripped.startswith("```") or not stripped.endswith("```"):
        return text
    nl = stripped.find("\n")
    if nl == -1:
        return text
    lang = stripped[3:nl].strip().lower()
    if lang not in ("", "markdown", "md", "text"):
        return text
    # Find the LAST standalone ``` in the text — that's the outer closing fence.
    # First try newline-prefixed (``` on its own line), then fall back to end-of-string.
    last = stripped.rfind("\n```")
    if last == -1 or last < nl:
        # Closing fence might be at the very end without a leading newline.
        if stripped.rstrip().endswith("```"):
            last = len(stripped) - 3
        else:
            last = -1
    if last < 0 or last <= nl:
        return text
    content = stripped[nl + 1 : last]
    # If there's a stray ``` inside the content (inner fence with no closing),
    # the outer opening may have been matched to the first inner closing.
    # In that case, try finding the LAST ``` from the end.
    if content.lstrip().startswith("```"):
        # The VLM likely embedded an inner ``` without proper nesting.
        # Find the actual outer closing by looking for standalone ``` lines.
        lines = stripped.splitlines()
        # Starting after the first line, find all lines that are exactly ```
        close_indices = [i for i, ln in enumerate(lines[1:], start=1) if ln.strip() == "```"]
        if close_indices and close_indices[-1] >= 1:
            content_lines = lines[1:close_indices[-1]]
            return "\n".join(content_lines)
    return content.strip()
