"""Replace event_relationships with typed Links in event_links

Revision ID: 004
Revises: 003
Create Date: 2026-11-02

The old rows were word-overlap hints, not Links, so they are dropped. No backfill:
Links accumulate from Events created after this migration.
"""

from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("event_relationships", if_exists=True)
    op.create_table(
        "event_links",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("from_event_id", sa.Integer(), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("to_event_id", sa.Integer(), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("link_type", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("from_event_id", "to_event_id", name="uq_event_link"),
        if_not_exists=True,
    )
    op.create_index("idx_link_from", "event_links", ["from_event_id"], if_not_exists=True)
    op.create_index("idx_link_to", "event_links", ["to_event_id"], if_not_exists=True)


def downgrade() -> None:
    op.drop_table("event_links")
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
