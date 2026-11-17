"""Initial schema: knowledge base (documents, chunks) and inspection data.

Revision ID: 0001
Revises:
Create Date: 2026-11-16
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import TSVECTOR

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMBEDDING_DIM = 384  # fixed in the migration on purpose: migrations must be reproducible


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "documents",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("source_key", sa.String(100), nullable=False, unique=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("source_url", sa.String(1000)),
        sa.Column("license", sa.String(200), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "chunks",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "document_id",
            sa.Integer,
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("ordinal", sa.Integer, nullable=False),
        sa.Column("section", sa.String(300)),
        sa.Column("page_start", sa.Integer, nullable=False),
        sa.Column("page_end", sa.Integer, nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=False),
        sa.Column(
            "tsv",
            TSVECTOR,
            sa.Computed("to_tsvector('english', text)", persisted=True),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_chunks_embedding_hnsw",
        "chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.create_index("ix_chunks_tsv_gin", "chunks", ["tsv"], postgresql_using="gin")

    op.create_table(
        "images",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False, unique=True),
        sa.Column("insulator_type", sa.String(50), nullable=False),
        sa.Column("width", sa.Integer, nullable=False),
        sa.Column("height", sa.Integer, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "detection_runs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "image_id", sa.Integer, sa.ForeignKey("images.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("model_name", sa.String(200), nullable=False),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("inference_ms", sa.Float, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_detection_runs_image_id", "detection_runs", ["image_id"])

    op.create_table(
        "detections",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "run_id",
            sa.Integer,
            sa.ForeignKey("detection_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("class_name", sa.String(100), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("x1", sa.Float, nullable=False),
        sa.Column("y1", sa.Float, nullable=False),
        sa.Column("x2", sa.Float, nullable=False),
        sa.Column("y2", sa.Float, nullable=False),
    )
    op.create_index("ix_detections_run_id", "detections", ["run_id"])
    op.create_index("ix_detections_class_name", "detections", ["class_name"])


def downgrade() -> None:
    op.drop_table("detections")
    op.drop_table("detection_runs")
    op.drop_table("images")
    op.drop_table("chunks")
    op.drop_table("documents")
