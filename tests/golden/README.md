# Golden Fixtures

Per constitution Principle V (Test-First with Golden Fixtures), every diagram type,
table variant, and layout category MUST have at least one golden fixture, created
**before** the corresponding pipeline stage is implemented.

## Layout

```
tests/golden/<category>/<fixture-name>/
  input.jpg            # source notebook page image
  expected-*.json      # expected blocks / layout
  expected-*.md        # expected Markdown / OCR text
  expected-*.puml      # expected PlantUML diagram source
```

## Categories

| Category    | Asserts on                          | Added in phase |
|-------------|-------------------------------------|----------------|
| `ocr/`      | extracted text + structure          | Phase 3 (US1)  |
| `layout/`   | detected blocks + reading order     | Phase 3 (US1)  |
| `tables/`   | reconstructed Markdown / CSV tables | Phase 7 (US3)  |
| `diagrams/` | generated PlantUML / draw.io source | Phase 4 (US2)  |

See `specs/001-handwritten-to-obsidian/quickstart.md` → "Adding a Golden Fixture".
