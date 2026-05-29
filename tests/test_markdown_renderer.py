
from hand2notes.core_models.enums import BlockType
from hand2notes.core_models.models import Block, BoundingBox, Page, Session, VaultConfig
from hand2notes.markdown_export.renderer import render_note


def test_render_note_skips_front_matter_and_preserves_ascii_continuation(tmp_path):
    session = Session(
        name="Render Test",
        notebook="tests",
        topic="markdown",
        tags=["renderer"],
    )

    page = Page(
        session_id=session.id,
        sequence=1,
        source_path=tmp_path / "page1.png",
        width_px=100,
        height_px=200,
        blocks=[
            Block(
                page_id=session.id,
                block_type=BlockType.NUMBERED_LIST,
                reading_order=0,
                bbox=BoundingBox(x=0, y=0, width=10, height=10),
                confidence=1.0,
                content="1 . First item\n2 . Second item",
            ),
            Block(
                page_id=session.id,
                block_type=BlockType.PARAGRAPH,
                reading_order=1,
                bbox=BoundingBox(x=0, y=20, width=10, height=10),
                confidence=1.0,
                content="\t   |\n       | continuation line\n       | second line",
            ),
        ],
    )

    config = VaultConfig(
        vault_root=tmp_path,
        folder_template="{{notebook}}/{{name}}",
        export_mode="overwrite",
        include_front_matter=False,
    )

    rendered = render_note(session, [page], config)
    assert rendered == (
        "1 . First item\n"
        "2 . Second item\n"
        "\t   |\n"
        "       | continuation line\n"
        "       | second line"
    )
