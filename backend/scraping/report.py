"""The Report shape every Feed adapter returns."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Report:
    """
    A single Report: published by one Source, received through one Feed.

    Adapters fill the content fields. `published_at` must be timezone-aware,
    or naive and already UTC. `run_feed` stamps `feed`, and `source` from the URL unless the adapter set it.
    """

    url: str
    title: str
    description: str = ""
    published_at: Optional[datetime] = None
    image_url: Optional[str] = None
    video_url: Optional[str] = None
    source: str = ""
    feed: str = ""
