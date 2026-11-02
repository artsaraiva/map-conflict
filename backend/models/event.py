import enum
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from backend.core.database import Base


class EventType(str, enum.Enum):
    CONFLICT = "conflict"
    NAVAL_BLOCKADE = "naval_blockade"
    DIPLOMATIC_TENSION = "diplomatic_tension"
    SANCTIONS = "sanctions"
    INTERNAL_UNREST = "internal_unrest"
    MILITARY_MOVEMENT = "military_movement"
    TRADE_DISPUTE = "trade_dispute"
    HUMANITARIAN = "humanitarian"
    OTHER = "other"


class SeverityLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    summary = Column(Text, nullable=True)
    event_type = Column(Enum(EventType), nullable=False, default=EventType.OTHER)
    severity = Column(Enum(SeverityLevel), nullable=False, default=SeverityLevel.MEDIUM)

    # Location data
    location_name = Column(String(300), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    geometry = Column(Geometry("GEOMETRY", srid=4326), nullable=True)

    # Countries involved
    countries = Column(String(500), nullable=True)  # comma-separated ISO codes

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    # Intelligence fields
    confidence_score = Column(Float, nullable=True, default=0.0)
    source_count = Column(Integer, nullable=True, default=0)
    theater = Column(String(100), nullable=True)

    # Relationships
    articles = relationship("Article", back_populates="event", lazy="raise")
    related_to = relationship(
        "EventRelationship",
        foreign_keys="EventRelationship.source_event_id",
        back_populates="source_event",
        lazy="select",
    )

    __table_args__ = (
        Index("idx_events_location", "latitude", "longitude"),
        Index("idx_events_type", "event_type"),
        Index("idx_events_created", "created_at"),
        Index("idx_events_theater", "theater"),
    )


class EventRelationship(Base):
    """
    Directed link between two events indicating semantic similarity or
    explicit narrative connection (e.g. retaliation, interception response).
    """

    __tablename__ = "event_relationships"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    target_event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    # How the target relates to the source: "similar", "followup", "retaliation", etc.
    relation_type = Column(String(50), nullable=False, default="similar")
    similarity_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    source_event = relationship(
        "Event", foreign_keys=[source_event_id], back_populates="related_to"
    )
    target_event = relationship("Event", foreign_keys=[target_event_id])

    __table_args__ = (
        UniqueConstraint("source_event_id", "target_event_id", name="uq_event_relationship"),
        Index("idx_rel_source", "source_event_id"),
        Index("idx_rel_target", "target_event_id"),
    )


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(2000), nullable=False)
    title = Column(String(500), nullable=False)
    source = Column(String(200), nullable=False)
    feed = Column(String(20), nullable=True)
    summary = Column(Text, nullable=True)
    image_url = Column(String(2000), nullable=True)
    video_url = Column(String(2000), nullable=True)
    published_at = Column(DateTime, nullable=True)
    scraped_at = Column(DateTime, default=datetime.utcnow)

    # Foreign key to event
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)
    event = relationship("Event", back_populates="articles")

    __table_args__ = (
        UniqueConstraint("url", name="uq_article_url"),
        Index("idx_articles_source", "source"),
        Index("idx_articles_scraped", "scraped_at"),
    )
