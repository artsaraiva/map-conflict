"""Event intake: what happens to each Report handed to `ingest`."""

import asyncio
from datetime import datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from backend.models.event import Article, Event, Link
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
        locations=[location] if location else [], event_type=event_type, severity=severity,
        summary="", countries=["YE"], is_geopolitical=True,
    )


NOT_GEOPOLITICAL = ArticleAnalysis(
    locations=[], event_type="other", severity="low", summary="", countries=[], is_geopolitical=False,
)


async def geocode(name):
    return GeocodedLocation(name=name, latitude=15.0, longitude=42.0)


async def relate_nothing(event, candidates):
    return {}


class FakeRelate:
    """Answers a Link type per candidate Event title, and records the candidate titles of each call."""

    def __init__(self, **answers):
        self.answers = answers
        self.calls = []

    async def __call__(self, event, candidates):
        self.calls.append(sorted(c.title for c in candidates))
        return {c.id: self.answers.get(c.title) for c in candidates}


def report(title, *, source="bbc.co.uk", description=STRIKE, feed="rss", url=None):
    return Report(url=url or f"https://{source}/{title}", title=title, description=description,
                  source=source, feed=feed)


@pytest.fixture
def session_factory(session):
    return async_sessionmaker(session.bind, expire_on_commit=False)


async def test_new_report_creates_a_stored_event(session_factory):
    classify = FakeClassifier(strike=geopolitical())

    [outcome] = await ingest([report("strike")], classify, geocode, relate_nothing, session_factory)

    assert outcome.kind == "created"
    async with session_factory() as s:
        stored = await s.get(Event, outcome.event.id)
    assert stored.location_name == "Red Sea"
    assert stored.source_count == 1


async def test_matching_report_from_another_source_corroborates_the_same_event(session_factory):
    classify = FakeClassifier(bbc=geopolitical(), reuters=geopolitical())

    [first] = await ingest([report("bbc")], classify, geocode, relate_nothing, session_factory)
    [second] = await ingest([report("reuters", source="reuters.com")], classify, geocode, relate_nothing, session_factory)

    assert second.kind == "corroborated"
    assert second.event.id == first.event.id
    assert second.event.source_count == 2
    assert second.event.confidence_score == 0.4


async def test_repeated_url_is_already_seen_without_classifying(session_factory):
    classify = FakeClassifier(strike=geopolitical())
    await ingest([report("strike")], classify, geocode, relate_nothing, session_factory)

    [outcome] = await ingest([report("strike")], classify, geocode, relate_nothing, session_factory)

    assert outcome.kind == "already_seen"
    assert classify.calls == ["strike"]


async def test_non_geopolitical_report_is_stored_and_seen_next_time(session_factory):
    classify = FakeClassifier(football=NOT_GEOPOLITICAL)

    [first] = await ingest([report("football")], classify, geocode, relate_nothing, session_factory)
    [second] = await ingest([report("football")], classify, geocode, relate_nothing, session_factory)

    assert (first.kind, second.kind) == ("not_geopolitical", "already_seen")


async def test_report_with_no_location_is_unplaced_and_never_classified_again(session_factory):
    classify = FakeClassifier(vague=geopolitical(location=None))

    [first] = await ingest([report("vague")], classify, geocode, relate_nothing, session_factory)
    [second] = await ingest([report("vague")], classify, geocode, relate_nothing, session_factory)

    assert (first.kind, second.kind) == ("unplaced", "already_seen")
    assert classify.calls == ["vague"]


async def test_report_that_fails_to_geocode_is_unplaced_and_never_classified_again(session_factory):
    classify = FakeClassifier(nowhere=geopolitical(location="Atlantis"))

    async def geocode_nothing(name):
        return None

    [first] = await ingest([report("nowhere")], classify, geocode_nothing, relate_nothing, session_factory)
    [second] = await ingest([report("nowhere")], classify, geocode_nothing, relate_nothing, session_factory)

    assert (first.kind, second.kind) == ("unplaced", "already_seen")
    assert classify.calls == ["nowhere"]


async def test_report_whose_classifier_errors_fails_and_is_classified_again_next_run(session_factory):
    classify = FakeClassifier(strike=RuntimeError("OpenAI is down"))

    [first] = await ingest([report("strike")], classify, geocode, relate_nothing, session_factory)
    classify.analyses["strike"] = geopolitical()
    [second] = await ingest([report("strike")], classify, geocode, relate_nothing, session_factory)

    assert (first.kind, second.kind) == ("failed", "created")
    assert classify.calls == ["strike", "strike"]


async def test_more_severe_corroborating_report_raises_severity(session_factory):
    classify = FakeClassifier(early=geopolitical("medium"), later=geopolitical("critical"))

    await ingest([report("early")], classify, geocode, relate_nothing, session_factory)
    [outcome] = await ingest([report("later", source="reuters.com")], classify, geocode, relate_nothing, session_factory)

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

    outcomes = await ingest(batch, classify, geocode, relate_nothing, session_factory)

    assert [o.kind for o in outcomes] == ["created", "failed", "created"]
    assert str(outcomes[1].error) == "boom"
    [retry] = await ingest([report("broken")], FakeClassifier(broken=geopolitical()), geocode, relate_nothing, session_factory)
    assert retry.kind == "corroborated"  # nothing of the failed Report was stored


# Reports as the adapters hand them over: RSS and Telegram leave `source` empty,
# GDELT gives the Source's raw `domain`.
BBC_VIA = {
    "rss": lambda: report("rss", source="", url="https://www.bbc.co.uk/news/world-1"),
    "gdelt": lambda: report("gdelt", source="bbc.com", feed="gdelt", url="https://www.bbc.com/news/articles/c1"),
}


@pytest.mark.parametrize("first, second", [("rss", "gdelt"), ("gdelt", "rss")])
async def test_same_source_through_two_feeds_counts_once(session_factory, first, second):
    classify = FakeClassifier(rss=geopolitical(), gdelt=geopolitical())

    await ingest([BBC_VIA[first]()], classify, geocode, relate_nothing, session_factory)
    [outcome] = await ingest([BBC_VIA[second]()], classify, geocode, relate_nothing, session_factory)

    assert outcome.kind == "corroborated"
    assert outcome.event.source_count == 1
    assert outcome.event.confidence_score == 0.2


async def test_unmapped_source_counts_as_its_own_source(session_factory):
    classify = FakeClassifier(rss=geopolitical(), telegram=geopolitical())
    telegram = report("telegram", source="", feed="telegram", url="https://t.me/RNintel/4242")

    await ingest([BBC_VIA["rss"]()], classify, geocode, relate_nothing, session_factory)
    [outcome] = await ingest([telegram], classify, geocode, relate_nothing, session_factory)

    assert outcome.kind == "corroborated"
    assert outcome.event.source_count == 2


async def test_two_unmapped_gdelt_domains_are_two_sources(session_factory):
    classify = FakeClassifier(ynet=geopolitical(), toi=geopolitical())

    await ingest([report("ynet", source="ynetnews.com", feed="gdelt")], classify, geocode, relate_nothing, session_factory)
    [outcome] = await ingest([report("toi", source="timesofisrael.com", feed="gdelt")], classify, geocode, relate_nothing, session_factory)

    assert outcome.kind == "corroborated"
    assert outcome.event.source_count == 2


async def test_concurrent_matching_reports_from_two_sources_make_one_event(session_factory):
    classify = FakeClassifier(bbc=geopolitical(), reuters=geopolitical())
    both_geocoded = asyncio.Barrier(2)

    async def geocode_together(name):
        await both_geocoded.wait()  # neither Feed looks for a match until both are placed
        return await geocode(name)

    outcomes = await asyncio.gather(
        ingest([report("bbc")], classify, geocode_together, relate_nothing, session_factory),
        ingest([report("reuters", source="reuters.com", feed="gdelt")], classify, geocode_together, relate_nothing, session_factory),
    )

    [first], [second] = outcomes
    assert sorted([first.kind, second.kind]) == ["corroborated", "created"]
    assert first.event.id == second.event.id
    async with session_factory() as s:
        assert await s.scalar(select(func.count()).select_from(Event)) == 1


async def test_event_created_inside_a_theater_stores_its_name(session_factory):
    classify = FakeClassifier(strike=geopolitical())  # geocoded to the southern Red Sea

    [outcome] = await ingest([report("strike")], classify, geocode, relate_nothing, session_factory)

    async with session_factory() as s:
        assert (await s.get(Event, outcome.event.id)).theater == "Red Sea and Bab el-Mandeb"


async def test_event_created_outside_every_theater_stores_no_theater(session_factory):
    classify = FakeClassifier(protest=geopolitical(event_type="internal_unrest", location="Paris"))

    async def geocode_paris(name):
        return GeocodedLocation(name=name, latitude=48.86, longitude=2.35)

    [outcome] = await ingest([report("protest")], classify, geocode_paris, relate_nothing, session_factory)

    async with session_factory() as s:
        assert (await s.get(Event, outcome.event.id)).theater is None


# ── Links ────────────────────────────────────────────────────────────────────
# Earlier Events are stored directly, with no Reports, so a new Report never corroborates them.


async def add_event(session, title, *, hours_ago=1, lat=15.5, lng=42.5,
                    summary="Saudi air defences intercept a drone over Jizan"):
    event = Event(title=title, summary=summary, location_name="Red Sea", latitude=lat, longitude=lng,
                  created_at=datetime.utcnow() - timedelta(hours=hours_ago))
    session.add(event)
    await session.commit()
    return event


async def stored_links(session_factory):
    async with session_factory() as s:
        return (await s.execute(select(Link.from_event_id, Link.to_event_id, Link.link_type))).all()


async def test_new_event_answered_response_to_links_to_the_earlier_event(session, session_factory):
    earlier = await add_event(session, "interception")
    relate = FakeRelate(interception="response_to")

    [outcome] = await ingest([report("strike")], FakeClassifier(strike=geopolitical()), geocode, relate,
                             session_factory)

    assert await stored_links(session_factory) == [(outcome.event.id, earlier.id, "response_to")]


@pytest.mark.parametrize("answer", [None, "similar"])
async def test_answer_that_is_not_a_link_type_stores_no_link(session, session_factory, answer):
    await add_event(session, "interception")
    relate = FakeRelate(interception=answer)

    await ingest([report("strike")], FakeClassifier(strike=geopolitical()), geocode, relate, session_factory)

    assert await stored_links(session_factory) == []


async def test_only_events_within_500_km_and_72_hours_are_offered_to_relate(session, session_factory):
    # The new Event is placed at 15°N 42°E; one degree of longitude there is about 107 km
    await add_event(session, "inside", hours_ago=70, lat=15.0, lng=46.5)  # ~480 km
    await add_event(session, "too far", lat=15.0, lng=47.5)  # ~590 km
    await add_event(session, "too old", hours_ago=75)
    relate = FakeRelate()

    await ingest([report("strike")], FakeClassifier(strike=geopolitical()), geocode, relate, session_factory)

    assert relate.calls == [["inside"]]


async def test_relate_receives_the_five_eligible_events_with_the_most_word_overlap(session, session_factory):
    for i, summary in enumerate([
        "Houthi missiles hit a tanker in the southern Red Sea",
        "Houthi missiles hit a cargo ship near Hodeidah",
        "A tanker transiting the Red Sea is hit by a drone",
        "Missiles fired at a tanker near Hodeidah",
        "Houthi drones target a ship in the Red Sea",
    ]):
        await add_event(session, f"overlap {i}", hours_ago=10 - i, lat=16.0, summary=summary)
    # The newest and nearest eligible Event, but with no words in common
    await add_event(session, "no overlap", hours_ago=0, lat=15.0, summary="Envoys resume ceasefire negotiations in Geneva")
    relate = FakeRelate()

    await ingest([report("strike")], FakeClassifier(strike=geopolitical()), geocode, relate, session_factory)

    assert relate.calls == [["overlap 0", "overlap 1", "overlap 2", "overlap 3", "overlap 4"]]


async def test_relate_is_not_called_without_an_eligible_event(session, session_factory):
    await add_event(session, "too far", lat=50.45, lng=30.52)
    relate = FakeRelate()

    [outcome] = await ingest([report("strike")], FakeClassifier(strike=geopolitical()), geocode, relate,
                             session_factory)

    assert outcome.kind == "created"
    assert relate.calls == []


async def test_corroborating_report_does_not_call_relate(session, session_factory):
    await add_event(session, "interception")
    classify = FakeClassifier(bbc=geopolitical(), reuters=geopolitical())
    relate = FakeRelate()
    await ingest([report("bbc")], classify, geocode, relate, session_factory)

    [outcome] = await ingest([report("reuters", source="reuters.com")], classify, geocode, relate, session_factory)

    assert outcome.kind == "corroborated"
    assert relate.calls == [["interception"]]  # only when the bbc Report created the Event


async def test_relate_failing_leaves_the_event_created_with_no_link(session, session_factory):
    await add_event(session, "interception")

    async def relate_down(event, candidates):
        raise RuntimeError("OpenAI is down")

    [outcome] = await ingest([report("strike")], FakeClassifier(strike=geopolitical()), geocode, relate_down,
                             session_factory)

    assert outcome.kind == "created"
    async with session_factory() as s:
        assert await s.scalar(select(func.count()).select_from(Article)) == 1
        assert await s.get(Event, outcome.event.id) is not None
    assert await stored_links(session_factory) == []


async def test_new_event_is_committed_before_relate_runs(session, session_factory):
    await add_event(session, "interception")
    seen = []

    async def relate_checking_commit(event, candidates):
        async with session_factory() as s:  # a separate session sees only committed rows
            seen.append(await s.get(Event, event.id) is not None)
        return {}

    await ingest([report("strike")], FakeClassifier(strike=geopolitical()), geocode, relate_checking_commit,
                 session_factory)

    assert seen == [True]
