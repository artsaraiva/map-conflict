"""Event intake: what happens to each Report handed to `ingest`."""

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from backend.models.event import Event
from backend.processing.geocoder import GeocodedLocation
from backend.processing.intake import Report, ingest
from backend.processing.nlp import ArticleAnalysis

pytestmark = pytest.mark.asyncio

STRIKE = "Houthi missiles hit a tanker transiting the southern Red Sea near Hodeidah"


class FakeClassifier:
    """Answers per Report title; an Exception value is raised instead of returned."""

    def __init__(self, **analyses):
        self.analyses = analyses
        self.calls = []

    async def __call__(self, title, description):
        self.calls.append(title)
        answer = self.analyses[title]
        if isinstance(answer, Exception):
            raise answer
        return answer


def geopolitical(severity="medium", event_type="conflict", location="Red Sea"):
    return ArticleAnalysis(
        locations=[location], event_type=event_type, severity=severity,
        summary="", countries=["YE"], is_geopolitical=True,
    )


NOT_GEOPOLITICAL = ArticleAnalysis(
    locations=[], event_type="other", severity="low", summary="", countries=[], is_geopolitical=False,
)


async def geocode(name):
    return GeocodedLocation(name=name, latitude=15.0, longitude=42.0)


def report(title, *, source="bbc.co.uk", description=STRIKE):
    return Report(url=f"https://{source}/{title}", title=title, description=description,
                  source=source, feed="rss")


@pytest.fixture
def session_factory(session):
    return async_sessionmaker(session.bind, expire_on_commit=False)


async def test_new_report_creates_a_stored_event(session_factory):
    classify = FakeClassifier(strike=geopolitical())

    [outcome] = await ingest([report("strike")], classify, geocode, session_factory)

    assert outcome.kind == "created"
    async with session_factory() as s:
        stored = await s.get(Event, outcome.event.id)
    assert stored.location_name == "Red Sea"
    assert stored.source_count == 1


async def test_matching_report_from_another_source_corroborates_the_same_event(session_factory):
    classify = FakeClassifier(bbc=geopolitical(), reuters=geopolitical())

    [first] = await ingest([report("bbc")], classify, geocode, session_factory)
    [second] = await ingest([report("reuters", source="reuters.com")], classify, geocode, session_factory)

    assert second.kind == "corroborated"
    assert second.event.id == first.event.id
    assert second.event.source_count == 2
    assert second.event.confidence_score == 0.4


async def test_repeated_url_is_already_seen_without_classifying(session_factory):
    classify = FakeClassifier(strike=geopolitical())
    await ingest([report("strike")], classify, geocode, session_factory)

    [outcome] = await ingest([report("strike")], classify, geocode, session_factory)

    assert outcome.kind == "already_seen"
    assert classify.calls == ["strike"]


async def test_non_geopolitical_report_is_stored_and_seen_next_time(session_factory):
    classify = FakeClassifier(football=NOT_GEOPOLITICAL)

    [first] = await ingest([report("football")], classify, geocode, session_factory)
    [second] = await ingest([report("football")], classify, geocode, session_factory)

    assert (first.kind, second.kind) == ("not_geopolitical", "already_seen")


async def test_more_severe_corroborating_report_raises_severity(session_factory):
    classify = FakeClassifier(early=geopolitical("medium"), later=geopolitical("critical"))

    await ingest([report("early")], classify, geocode, session_factory)
    [outcome] = await ingest([report("later", source="reuters.com")], classify, geocode, session_factory)

    assert outcome.kind == "corroborated"
    assert outcome.event.severity.value == "critical"


async def test_one_failing_report_does_not_stop_the_batch(session_factory):
    classify = FakeClassifier(
        strike=geopolitical(), broken=RuntimeError("boom"),
        talks=geopolitical(event_type="diplomatic_tension", location="Geneva"),
    )
    batch = [
        report("strike"),
        report("broken"),
        report("talks", description="Envoys resume ceasefire negotiations in Geneva on Monday"),
    ]

    outcomes = await ingest(batch, classify, geocode, session_factory)

    assert [o.kind for o in outcomes] == ["created", "failed", "created"]
    assert str(outcomes[1].error) == "boom"
    [retry] = await ingest([report("broken")], FakeClassifier(broken=geopolitical()), geocode, session_factory)
    assert retry.kind == "corroborated"  # nothing of the failed Report was stored
