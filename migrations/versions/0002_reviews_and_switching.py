"""Vision reviews of detections, model-switching info, image storage path.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("images", sa.Column("storage_path", sa.String(500)))
    op.add_column(
        "detection_runs",
        sa.Column("requested_mode", sa.String(20), nullable=False, server_default="fast"),
    )
    op.add_column(
        "detection_runs",
        sa.Column("escalated", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.add_column("detection_runs", sa.Column("fast_ms", sa.Float))

    op.create_table(
        "detection_reviews",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "detection_id",
            sa.Integer,
            sa.ForeignKey("detections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("agrees_with_detector", sa.Boolean, nullable=False),
        sa.Column("condition", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("needs_human_review", sa.Boolean, nullable=False),
        sa.Column("rationale", sa.Text, nullable=False),
        sa.Column("input_tokens", sa.Integer, nullable=False),
        sa.Column("output_tokens", sa.Integer, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_detection_reviews_detection_id", "detection_reviews", ["detection_id"])


def downgrade() -> None:
    op.drop_table("detection_reviews")
    op.drop_column("detection_runs", "fast_ms")
    op.drop_column("detection_runs", "escalated")
    op.drop_column("detection_runs", "requested_mode")
    op.drop_column("images", "storage_path")
