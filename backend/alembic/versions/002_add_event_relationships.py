"""Add event_relationships table

Revision ID: 002
Revises: 001
Create Date: 2026-03-27
"""

from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "event_relationships",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source_event_id", sa.Integer(), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_event_id", sa.Integer(), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relation_type", sa.String(50), nullable=False, server_default="similar"),
        sa.Column("similarity_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("source_event_id", "target_event_id", name="uq_event_relationship"),
    )
    op.create_index("idx_rel_source", "event_relationships", ["source_event_id"])
    op.create_index("idx_rel_target", "event_relationships", ["target_event_id"])


def downgrade() -> None:
    op.drop_index("idx_rel_target", table_name="event_relationships")
    op.drop_index("idx_rel_source", table_name="event_relationships")
    op.drop_table("event_relationships")
