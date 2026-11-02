"""Record the Feed each Report arrived through

Revision ID: 003
Revises: 002
Create Date: 2026-11-02

Existing rows keep feed = NULL and their old Source keys; no backfill.
"""

from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("articles", sa.Column("feed", sa.String(20), nullable=True), if_not_exists=True)


def downgrade() -> None:
    op.drop_column("articles", "feed")
