from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ArticleResponse(BaseModel):
    id: int
    url: str
    title: str
    source: str
    summary: Optional[str] = None
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    published_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EventResponse(BaseModel):
    id: int
    title: str
    summary: Optional[str] = None
    event_type: str
    severity: str
    location_name: str
    latitude: float
    longitude: float
    countries: Optional[str] = None
    created_at: datetime
    confidence_score: Optional[float] = None
    source_count: Optional[int] = None
    theater: Optional[str] = None
    articles: list[ArticleResponse] = []

    class Config:
        from_attributes = True


class EventListResponse(BaseModel):
    events: list[EventResponse]
    total: int


class EventMapPoint(BaseModel):
    """Lightweight event data for map rendering."""

    id: int
    title: str
    event_type: str
    severity: str
    latitude: float
    longitude: float
    location_name: str
    article_count: int
    image_url: Optional[str] = None
    sources: list[str] = []
    created_at: datetime
    confidence_score: Optional[float] = None
    source_count: Optional[int] = None
    theater: Optional[str] = None

    class Config:
        from_attributes = True


class RelatedEventResponse(BaseModel):
    """Lightweight event data returned by the /related endpoint."""

    id: int
    title: str
    event_type: str
    severity: str
    location_name: str
    latitude: float
    longitude: float
    theater: Optional[str] = None
    confidence_score: Optional[float] = None
    created_at: datetime
    relation_type: str
    similarity_score: Optional[float] = None
