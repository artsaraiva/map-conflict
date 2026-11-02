"""
NLP processing: extracts locations from article text using spaCy,
and classifies articles using OpenAI API.
"""

import json
import logging
import re
import unicodedata
from typing import Optional
from dataclasses import dataclass

import spacy
from openai import AsyncOpenAI

from backend.core.config import get_settings
from backend.models.event import Event

logger = logging.getLogger(__name__)

# Load spaCy model (small English model for NER)
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    logger.warning(
        "spaCy model not found. Run: python -m spacy download en_core_web_sm"
    )
    nlp = None


@dataclass
class ArticleAnalysis:
    locations: list[str]
    event_type: str
    severity: str
    summary: str
    countries: list[str]
    is_geopolitical: bool


def extract_locations(text: str) -> list[str]:
    """Extract location entities from text using spaCy NER."""
    if nlp is None:
        return []

    doc = nlp(text)
    locations = []
    for ent in doc.ents:
        if ent.label_ in ("GPE", "LOC", "FAC"):
            location = ent.text.strip()
            if location and location not in locations:
                locations.append(location)

    return locations


async def classify_article(title: str, description: str) -> Optional[ArticleAnalysis]:
    """
    Use OpenAI to classify a Report and extract structured data.
    Keyword classification is used only when no OpenAI key is configured; an
    OpenAI error raises instead of falling back.
    """
    settings = get_settings()
    if not settings.openai_api_key:
        logger.warning("No OpenAI API key configured, using fallback classification")
        return _fallback_classification(title, description)

    client = AsyncOpenAI(api_key=settings.openai_api_key)

    prompt = f"""Analyze this news article and determine if it's geopolitically relevant.

Title: {title}
Description: {description}

Respond with JSON only, no other text. Schema:
{{
    "is_geopolitical": true/false,
    "locations": ["list of specific geographic locations mentioned"],
    "countries": ["list of country ISO-2 codes involved"],
    "event_type": "one of: conflict, naval_blockade, diplomatic_tension, sanctions, internal_unrest, military_movement, trade_dispute, humanitarian, other",
    "severity": "one of: low, medium, high, critical",
    "summary": "1-2 sentence summary focused on the geopolitical significance"
}}

Rules:
- Only set is_geopolitical to true for articles about international relations, conflicts, military, sanctions, diplomacy, territorial disputes, or significant internal political events.
- Be specific with locations (e.g., "Strait of Hormuz" not just "Middle East").
- Use ISO-2 country codes (e.g., "US", "CN", "IR").
- Severity: critical = active military conflict; high = imminent threat/major diplomatic crisis; medium = ongoing tensions; low = routine political news.
"""

    # An OpenAI error propagates: Event intake leaves the Report unstored, so the next run retries it
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=500,
        response_format={"type": "json_object"},
    )

    result = json.loads(response.choices[0].message.content)

    return ArticleAnalysis(
        locations=result.get("locations", []),
        event_type=result.get("event_type", "other"),
        severity=result.get("severity", "medium"),
        summary=result.get("summary", ""),
        countries=result.get("countries", []),
        is_geopolitical=result.get("is_geopolitical", False),
    )


def _describe_event(event: Event) -> str:
    event_type = event.event_type.value if event.event_type else "other"
    return (f"{event.title} | {event.summary or ''} | type: {event_type} | "
            f"place: {event.location_name} | time: {event.created_at:%Y-%m-%d %H:%M} UTC")


async def relate_events(event: Event, candidates: list[Event]) -> dict[int, str | None]:
    """
    Ask OpenAI, in one call, how a new Event relates to each earlier candidate Event.
    Maps candidate id to `response_to`, `escalation_of`, `same_campaign` or None.
    With no OpenAI key, proposes no Links.
    """
    settings = get_settings()
    if not settings.openai_api_key:
        return {}

    # Bounded, so a slow model delays Link proposal for one Event, not the Feed's Reports
    client = AsyncOpenAI(api_key=settings.openai_api_key, timeout=30, max_retries=1)
    listed = "\n".join(f"- id {c.id}: {_describe_event(c)}" for c in candidates)

    prompt = f"""A new geopolitical event was reported. Decide, for each earlier event, whether the new event is linked to it.

New event: {_describe_event(event)}

Earlier events:
{listed}

Link types:
- "response_to": the new event answers the earlier one (e.g. an interception of, or retaliation for, an attack).
- "escalation_of": the new event raises the stakes of the earlier one (larger scale, new weapons, new targets).
- "same_campaign": both belong to the same deliberate, ongoing operation, with neither answering the other.
- null: not linked. Similar wording, place or topic alone is not a link.

Choose the most specific type: "response_to" or "escalation_of" over "same_campaign".

Respond with JSON only, no other text. Schema:
{{"links": {{"<earlier event id>": "response_to" | "escalation_of" | "same_campaign" | null}}}}
"""

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=300,
        response_format={"type": "json_object"},
    )

    links = json.loads(response.choices[0].message.content).get("links") or {}
    return {int(event_id): link_type for event_id, link_type in links.items() if str(event_id).isdigit()}


def _fallback_classification(title: str, description: str) -> ArticleAnalysis:
    """
    Simple keyword-based classification, used only when no OpenAI key is configured.
    Extracts locations via spaCy and uses keyword matching for type.
    """
    text = f"{title} {description}"
    locations = extract_locations(text)

    # Simple keyword-based type detection
    text_lower = text.lower()

    conflict_keywords = [
        "war",
        "attack",
        "strike",
        "bomb",
        "missile",
        "troops",
        "military",
        "killed",
        "battle",
    ]
    naval_keywords = [
        "navy",
        "naval",
        "strait",
        "blockade",
        "ship",
        "maritime",
        "fleet",
    ]
    diplomatic_keywords = [
        "diplomat",
        "embassy",
        "talks",
        "summit",
        "treaty",
        "agreement",
        "negotiate",
    ]
    sanction_keywords = ["sanction", "embargo", "tariff", "ban", "restrict"]
    unrest_keywords = ["protest", "riot", "unrest", "coup", "uprising", "revolution"]

    event_type = "other"
    if any(kw in text_lower for kw in conflict_keywords):
        event_type = "conflict"
    elif any(kw in text_lower for kw in naval_keywords):
        event_type = "naval_blockade"
    elif any(kw in text_lower for kw in diplomatic_keywords):
        event_type = "diplomatic_tension"
    elif any(kw in text_lower for kw in sanction_keywords):
        event_type = "sanctions"
    elif any(kw in text_lower for kw in unrest_keywords):
        event_type = "internal_unrest"

    # Only consider it geopolitical if we found locations and a relevant type
    is_geopolitical = len(locations) > 0 and event_type != "other"

    return ArticleAnalysis(
        locations=locations,
        event_type=event_type,
        severity="medium",
        summary=description[:200] if description else title,
        countries=[],
        is_geopolitical=is_geopolitical,
    )


# ── Text similarity utilities (for cross-channel deduplication) ─────────────

# Regex that matches emoji, variation selectors, ZWJ sequences, and other
# non-letter/non-digit symbols commonly found in Telegram posts.
_EMOJI_RE = re.compile(
    "["
    "\U0001f600-\U0001f64f"  # emoticons
    "\U0001f300-\U0001f5ff"  # symbols & pictographs
    "\U0001f680-\U0001f6ff"  # transport & map
    "\U0001f1e0-\U0001f1ff"  # flags (iOS)
    "\U00002702-\U000027b0"  # dingbats
    "\U0000fe00-\U0000fe0f"  # variation selectors
    "\U0000200d"  # zero-width joiner
    "\U000024c2-\U0001f251"
    "]+",
    flags=re.UNICODE,
)

# Punctuation / non-word chars to strip when tokenizing
_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)


def strip_emoji(text: str) -> str:
    """Remove emoji characters from text."""
    return _EMOJI_RE.sub("", text)


def _tokenize(text: str) -> set[str]:
    """
    Lowercase, strip emoji and punctuation, split into word tokens.
    Returns a set for Jaccard computation.
    """
    cleaned = strip_emoji(text)
    cleaned = _PUNCT_RE.sub(" ", cleaned)
    tokens = cleaned.lower().split()
    # Filter very short tokens (articles, prepositions, hashtag remnants)
    return {t for t in tokens if len(t) > 1}


def text_similarity(text_a: str, text_b: str) -> float:
    """
    Compute Jaccard word-overlap similarity between two texts.
    Returns a float in [0, 1]. Higher = more similar.
    """
    if not text_a or not text_b:
        return 0.0

    tokens_a = _tokenize(text_a)
    tokens_b = _tokenize(text_b)

    if not tokens_a or not tokens_b:
        return 0.0

    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b

    return len(intersection) / len(union)
