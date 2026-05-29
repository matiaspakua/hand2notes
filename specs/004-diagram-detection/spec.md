# Feature Specification: Improve Diagram Detection Accuracy in OCR Pipeline

**Feature Branch**: `004-diagram-detection`

**Created**: 2026-05-29

**Status**: Draft

**Input**: User description: "Improve diagram detection accuracy in OCR pipeline"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Handwritten flowcharts and decision trees are reliably transcribed (Priority: P1)

Students, engineers, and researchers frequently sketch flowcharts and decision trees in handwritten notes. When converting these notes to digital Obsidian vaults, users expect the diagram logic to be preserved as navigable Mermaid diagrams that reflect the original intent.

**Why this priority**: Flowcharts and decision trees are structural diagrams with explicit decision paths. Accurate transcription of these is critical for understanding logic and workflows. Without this, users lose key information and must manually re-draw complex diagrams.

**Independent Test**: Can be fully tested by importing a handwritten flowchart and asserting the resulting Mermaid diagram contains: (1) all decision nodes and conditions, (2) all branches, (3) correct flow direction, (4) no spurious loops. Delivers direct value to technical note-takers.

**Acceptance Scenarios**:

1. **Given** a handwritten flowchart with 3+ decision branches, **When** the page is converted, **Then** the resulting Mermaid diagram contains all branches and conditions with ≥85% semantic accuracy
2. **Given** a handwritten state diagram, **When** the page is converted, **Then** all states and transitions are captured as valid Mermaid syntax
3. **Given** a diagram with feedback loops or cycles, **When** the page is converted, **Then** the diagram is syntactically valid and renders without errors

---

### User Story 2 - Tables, graphs, and sketched charts are distinguished from text (Priority: P2)

Handwritten notes often mix structured data (tables, grids, bar charts) with prose text. Users need diagrams and structured data to be recognized as such, not transcribed as bulleted lists or paragraphs, so the final vault preserves the original information hierarchy.

**Why this priority**: Incorrect classification of structured data as prose loses formatting and readability. Users can work around missing details in diagrams, but a destroyed table structure is harder to recover from.

**Independent Test**: Can be tested by converting a page with mixed content (prose + hand-drawn table + sketch), asserting output contains exactly one Markdown table block and one diagram block (not all-text). Delivers clarity and prevents data-loss scenarios.

**Acceptance Scenarios**:

1. **Given** a page with handwritten text and a sketched table, **When** converted, **Then** output contains a recognized Markdown table (not a bulleted list) with ≥90% column accuracy
2. **Given** a page with a bar chart sketch, **When** converted, **Then** output contains a diagram block (Mermaid) or structured chart, not raw text
3. **Given** mixed prose and diagram, **When** converted, **Then** transcription preserves the layout intent (diagrams separate from text prose)

---

### User Story 3 - Pipeline detects and handles ambiguous or malformed diagram input gracefully (Priority: P3)

Some sketches are too abstract, incomplete, or illegible to be safely transcribed into Mermaid syntax. Users expect the system to either produce a best-effort transcription or gracefully report the limitation (e.g., "diagram too complex" or fall back to text description).

**Why this priority**: Edge cases exist; graceful degradation prevents pipeline crashes and preserves user trust. Lower priority because well-formed diagrams are the primary use case.

**Independent Test**: Can be tested by converting a page with a very sketchy, illegible diagram, asserting the pipeline completes without error (either with a diagram, text fallback, or explicit confidence-low marker). Validates robustness.

**Acceptance Scenarios**:

1. **Given** a very sketchy, partially visible diagram, **When** converted, **Then** pipeline completes without crashing (produces output or fallback)
2. **Given** a diagram with handwriting too faint to read clearly, **When** converted, **Then** result includes a confidence flag or text fallback for review
3. **Given** abstract doodles that don't form a recognizable diagram, **When** converted, **Then** system skips diagram extraction and continues with text transcription

---

### Edge Cases

- What happens when a page has overlapping diagrams (one on top of another)?
- How does the system handle diagrams with mixed languages (e.g., English labels, Spanish annotations)?
- What if a diagram has more than 50 nodes or 100 edges? System MUST degrade gracefully (fallback to text or confidence flag) rather than timeout or crash
- How does the system recover if Mermaid syntax generation produces invalid output?
- Can the system detect and handle ASCII art or text-based diagrams (e.g., pseudocode boxes)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST identify and extract diagram regions from handwritten pages with ≥85% recall (diagrams present are detected)
- **FR-002**: System MUST transcribe detected diagrams into valid Mermaid syntax with ≥80% precision (generated syntax is valid and renders)
- **FR-003**: System MUST distinguish between diagram types (flowchart, graph, state machine, entity-relationship, class diagram, sequence diagram) and apply appropriate Mermaid graph type
- **FR-004**: System MUST preserve diagram semantics including all nodes, edges, labels, and decision logic with ≥85% accuracy
- **FR-005**: System MUST sanitize and validate generated Mermaid syntax before output (no infinite loops, no orphaned nodes, edge count within reasonable bounds)
- **FR-006**: System MUST tag each diagram block with a confidence score (0–100) and diagram type for user review
- **FR-007**: System MUST include text-based fallback descriptions for diagrams if Mermaid syntax generation fails or confidence is too low (<60%)
- **FR-008**: System MUST handle malformed or incomplete diagram input gracefully without crashing (e.g., timeout, partial output, or fallback to text)
- **FR-009**: System MUST support handwritten AND sketched diagrams (both pen-drawn and marked-up printed diagrams)
- **FR-010**: System MUST log diagram detection decisions and confidence scores for debugging and quality analysis

### Key Entities

- **DiagramBlock**: Represents a detected diagram; contains diagram_type (enum: flowchart, graph, state, erd, class, sequence, other), mermaid_source (string), confidence_score (0–100), original_text_fallback (string), extraction_metadata (bounding box, detected language)
- **DiagramRegion**: Represents a spatial region on the page containing diagram-like content; contains region_type (enum: structured_text, flowchart, graph, sketch, mixed), layout_bounds, and detected_elements (list of nodes/edges/labels)
- **VLM Diagram Output**: JSON structure emitted by the VLM diagram pass containing: diagram_regions (list), diagram_descriptions (list of text), detected_types (list of inferred diagram types)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Handwritten flowcharts with 3–10 decision nodes are transcribed with ≥85% semantic accuracy (all nodes and edges preserved, logic correct)
- **SC-002**: Diagram detection recall is ≥85% (≥85% of diagrams present in test corpus are identified and extracted)
- **SC-003**: Mermaid syntax generation produces valid, renderable output for ≥90% of detected diagrams (no syntax errors, renders without timeout)
- **SC-004**: Mixed-content pages (text + diagram) maintain proper separation in output (no diagrams merged into text blocks, no text mixed into diagram regions)
- **SC-005**: Diagram extraction does not increase end-to-end conversion time by more than 15% for typical pages (≤2 seconds additional latency per page)
- **SC-006**: System gracefully handles illegible or malformed diagram input without crashing; 100% of pages complete conversion (either with diagram or fallback)
- **SC-007**: Confidence scores are well-calibrated: diagrams with confidence ≥80% render correctly ≥90% of the time; diagrams with confidence <60% include text fallback

## Assumptions

- **VLM Capability**: The local VLM (Qwen2.5-VL 7B) is capable of identifying and describing diagram structure when prompted with appropriate prompts and image preprocessing
- **Diagram Diversity**: Test corpus includes flowcharts, state diagrams, entity-relationship diagrams, and class diagrams; system is not required to handle exotic diagram types (e.g., Sankey diagrams, timeline graphics)
- **Handwriting Legibility**: Input images are reasonably legible (written in black or dark ink, not faint pencil); extremely faint or obscured diagrams may have low confidence
- **Mermaid Compatibility**: Output diagrams should use Mermaid syntax versions supported by Obsidian (flowchart, graph, state machine, class, sequence, ER, pie, gantt as applicable)
- **Single-Pass vs. Two-Pass**: Current pipeline uses a two-pass approach (text + diagram); diagram detection can be a dedicated VLM pass or integrated into existing text pass based on implementation choice
- **Scope Exclusion**: Hand-drawn photos, inserted printed diagrams (photos of diagrams), and 3D sketches are out of scope; focus is on 2D pen-drawn diagrams on paper
- **Review Workflow**: Diagram confidence scores and fallback text enable user review/correction but are not a substitute for perfect accuracy; users expect to review low-confidence diagrams
