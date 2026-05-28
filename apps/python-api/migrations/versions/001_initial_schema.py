"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-05-27
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "session",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("notebook", sa.String(), nullable=False),
        sa.Column("topic", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "page",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("source_path", sa.String(), nullable=False),
        sa.Column("preprocessed_path", sa.String(), nullable=True),
        sa.Column("width_px", sa.Integer(), nullable=False),
        sa.Column("height_px", sa.Integer(), nullable=False),
        sa.Column("pipeline_stage", sa.String(), nullable=False),
        sa.Column("overall_confidence", sa.Float(), nullable=False),
        sa.Column("review_status", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["session.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_page_session_id", "page", ["session_id"])
    op.create_table(
        "block",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("page_id", sa.Uuid(), nullable=False),
        sa.Column("block_type", sa.String(), nullable=False),
        sa.Column("reading_order", sa.Integer(), nullable=False),
        sa.Column("bbox", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("review_flag", sa.Boolean(), nullable=False),
        sa.Column("content", sa.String(), nullable=True),
        sa.Column("corrected_content", sa.String(), nullable=True),
        sa.Column("visual_semantics", sa.JSON(), nullable=True),
        sa.Column("crop_path", sa.String(), nullable=True),
        sa.Column("table_data", sa.JSON(), nullable=True),
        sa.Column("diagram_data", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["page_id"], ["page.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_block_page_id", "block", ["page_id"])
    op.create_table(
        "export_artifact",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("page_id", sa.Uuid(), nullable=True),
        sa.Column("artifact_type", sa.String(), nullable=False),
        sa.Column("file_path", sa.String(), nullable=False),
        sa.Column("vault_relative_path", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["session.id"]),
        sa.ForeignKeyConstraint(["page_id"], ["page.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_export_artifact_session_id", "export_artifact", ["session_id"])
    op.create_index("ix_export_artifact_page_id", "export_artifact", ["page_id"])
    op.create_table(
        "pipeline_run",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("stage", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["session.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pipeline_run_session_id", "pipeline_run", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_pipeline_run_session_id", table_name="pipeline_run")
    op.drop_table("pipeline_run")
    op.drop_index("ix_export_artifact_page_id", table_name="export_artifact")
    op.drop_index("ix_export_artifact_session_id", table_name="export_artifact")
    op.drop_table("export_artifact")
    op.drop_index("ix_block_page_id", table_name="block")
    op.drop_table("block")
    op.drop_index("ix_page_session_id", table_name="page")
    op.drop_table("page")
    op.drop_table("session")
