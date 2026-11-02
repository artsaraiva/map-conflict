from pydantic import AfterValidator, BaseModel
from datetime import datetime, timezone
from typing import Annotated, Optional

# The columns are naive and hold UTC; mark them so clients don't read them as local time.
UtcDatetime = Annotated[
    datetime, AfterValidator(lambda v: v if v.tzinfo else v.replace(tzinfo=timezone.utc))
]


class ArticleResponse(BaseModel):
    id: int
    url: str
    title: str
    source: str
    feed: Optional[str] = None
    summary: Optional[str] = None
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    published_at: Optional[UtcDatetime] = None

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
    created_at: UtcDatetime
    confidence_score: Optional[float] = None
    source_count: Optional[int] = None
    theater: Optional[str] = None
    articles: list[ArticleResponse] = []

    class Config:
        from_attributes = True


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
    created_at: UtcDatetime
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
    created_at: UtcDatetime
    relation_type: str
    similarity_score: Optional[float] = None
