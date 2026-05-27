# Fixture: mixed-heading-list

**Category**: ocr
**Content types**: title, heading (×2), paragraph, bullet_list

## Input image (input.jpg)

A handwritten notebook page containing:
- A title in large letters: "Meeting Notes"
- A heading: "Introduction"
- One paragraph sentence
- A bullet list with three items
- A heading: "Next Steps"
- One closing sentence

## Expected output (expected-text.md)

See `expected-text.md`.

## Acceptance criteria

- Title maps to `#` heading
- Section headings map to `##`
- Bullet items render as `- ` list items
- Reading order matches top-to-bottom page layout
