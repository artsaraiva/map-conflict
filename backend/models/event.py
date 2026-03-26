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

    # Relationships
    articles = relationship("Article", back_populates="event", lazy="selectin")

    __table_args__ = (
        Index("idx_events_location", "latitude", "longitude"),
        Index("idx_events_type", "event_type"),
        Index("idx_events_created", "created_at"),
    )


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(2000), nullable=False)
    title = Column(String(500), nullable=False)
    source = Column(String(200), nullable=False)
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
