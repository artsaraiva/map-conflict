"""Add confidence_score, source_count, theater to events

Revision ID: 001
Revises: 000
Create Date: 2026-03-27
"""

from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = "000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "events",
        sa.Column("confidence_score", sa.Float(), nullable=True, server_default="0.0"),
        if_not_exists=True,
    )
    op.add_column(
        "events",
        sa.Column("source_count", sa.Integer(), nullable=True, server_default="0"),
        if_not_exists=True,
    )
    op.add_column(
        "events",
        sa.Column("theater", sa.String(100), nullable=True),
        if_not_exists=True,
    )
    op.create_index("idx_events_theater", "events", ["theater"], if_not_exists=True)


def downgrade() -> None:
    op.drop_index("idx_events_theater", table_name="events")
    op.drop_column("events", "theater")
    op.drop_column("events", "source_count")
    op.drop_column("events", "confidence_score")
