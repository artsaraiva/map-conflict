"""Create the events and articles tables as they stood before 001

Revision ID: 000
Revises:
Create Date: 2026-11-02

Databases built by the old `create_all` bootstrap already have these tables and no
alembic_version row; this step leaves them alone, and the later steps skip whatever
they already hold, so `alembic upgrade head` brings them to the current schema.
"""

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry

revision = "000"
down_revision = None
branch_labels = None
depends_on = None

EVENT_TYPES = (
    "CONFLICT", "NAVAL_BLOCKADE", "DIPLOMATIC_TENSION", "SANCTIONS", "INTERNAL_UNREST",
    "MILITARY_MOVEMENT", "TRADE_DISPUTE", "HUMANITARIAN", "OTHER",
)
SEVERITY_LEVELS = ("LOW", "MEDIUM", "HIGH", "CRITICAL")


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    if sa.inspect(op.get_bind()).has_table("events"):
        return

    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("event_type", sa.Enum(*EVENT_TYPES, name="eventtype"), nullable=False),
        sa.Column("severity", sa.Enum(*SEVERITY_LEVELS, name="severitylevel"), nullable=False),
        sa.Column("location_name", sa.String(300), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("geometry", Geometry("GEOMETRY", srid=4326), nullable=True),
        sa.Column("countries", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
    )
    op.create_index("idx_events_location", "events", ["latitude", "longitude"])
    op.create_index("idx_events_type", "events", ["event_type"])
    op.create_index("idx_events_created", "events", ["created_at"])

    op.create_table(
        "articles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("url", sa.String(2000), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("source", sa.String(200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("image_url", sa.String(2000), nullable=True),
        sa.Column("video_url", sa.String(2000), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("scraped_at", sa.DateTime(), nullable=True),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id"), nullable=True),
        sa.UniqueConstraint("url", name="uq_article_url"),
    )
    op.create_index("idx_articles_source", "articles", ["source"])
    op.create_index("idx_articles_scraped", "articles", ["scraped_at"])


def downgrade() -> None:
    op.drop_table("articles")
    op.drop_table("events")
    op.execute("DROP TYPE IF EXISTS eventtype")
    op.execute("DROP TYPE IF EXISTS severitylevel")
