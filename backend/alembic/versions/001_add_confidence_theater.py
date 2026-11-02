"""Add confidence_score, source_count, theater to events

Revision ID: 001
Revises:
Create Date: 2026-03-27
"""

from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "events",
        sa.Column("confidence_score", sa.Float(), nullable=True, server_default="0.0"),
    )
    op.add_column(
        "events",
        sa.Column("source_count", sa.Integer(), nullable=True, server_default="0"),
    )
    op.add_column(
        "events",
        sa.Column("theater", sa.String(100), nullable=True),
    )
    op.create_index("idx_events_theater", "events", ["theater"])


def downgrade() -> None:
    op.drop_index("idx_events_theater", table_name="events")
    op.drop_column("events", "theater")
    op.drop_column("events", "source_count")
    op.drop_column("events", "confidence_score")
