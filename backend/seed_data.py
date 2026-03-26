"""
Seed the database with sample geopolitical events for testing.
Run: python -m backend.seed_data
"""
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from backend.core.config import get_settings
from backend.core.database import Base
from backend.models.event import Event, Article, EventType, SeverityLevel


SAMPLE_EVENTS = [
    {
        "title": "Iran Closes Strait of Hormuz Amid Rising Tensions",
        "summary": "Iran has ordered a naval blockade of the Strait of Hormuz, one of the world's most critical oil chokepoints, in response to escalating tensions with the United States and its allies. Global oil prices have surged.",
        "event_type": EventType.NAVAL_BLOCKADE,
        "severity": SeverityLevel.CRITICAL,
        "location_name": "Strait of Hormuz",
        "latitude": 26.56,
        "longitude": 56.27,
        "countries": "IR,US",
        "articles": [
            {
                "url": "https://edition.cnn.com/2026/03/12/americas/panama-canal-strait-hormuz-oil-iran-war-intl-latam",
                "title": "Iran closes Strait of Hormuz as oil prices spike globally",
                "source": "cnn",
                "summary": "Iran has closed the Strait of Hormuz, one of the world's most important oil chokepoints, as tensions escalate.",
            },
        ],
    },
    {
        "title": "Renewed Fighting in Eastern Ukraine Donbas Region",
        "summary": "Heavy artillery exchanges and infantry clashes have intensified along the front lines in the Donbas region, with both sides reporting significant casualties.",
        "event_type": EventType.CONFLICT,
        "severity": SeverityLevel.CRITICAL,
        "location_name": "Eastern Ukraine",
        "latitude": 49.0,
        "longitude": 36.0,
        "countries": "UA,RU",
        "articles": [
            {
                "url": "https://example.com/ukraine-donbas",
                "title": "Fighting intensifies in Donbas as winter offensive continues",
                "source": "reuters",
                "summary": "Both sides have escalated operations in the Donbas region with heavy artillery exchanges.",
            },
        ],
    },
    {
        "title": "China Conducts Military Exercises Near Taiwan Strait",
        "summary": "The Chinese People's Liberation Army has launched large-scale military exercises in the waters surrounding Taiwan, including live-fire drills and naval maneuvers.",
        "event_type": EventType.MILITARY_MOVEMENT,
        "severity": SeverityLevel.HIGH,
        "location_name": "Taiwan Strait",
        "latitude": 23.5,
        "longitude": 121.0,
        "countries": "CN,TW",
        "articles": [
            {
                "url": "https://example.com/taiwan-exercises",
                "title": "China launches largest military exercises near Taiwan in years",
                "source": "bbc",
                "summary": "PLA conducts unprecedented military drills around Taiwan including live fire exercises.",
            },
        ],
    },
    {
        "title": "India-Pakistan Border Tensions Escalate in Kashmir",
        "summary": "Cross-border shelling has intensified along the Line of Control in Kashmir, with both nations deploying additional troops to the disputed region.",
        "event_type": EventType.CONFLICT,
        "severity": SeverityLevel.HIGH,
        "location_name": "Kashmir",
        "latitude": 34.5,
        "longitude": 78.0,
        "countries": "IN,PK",
        "articles": [
            {
                "url": "https://example.com/kashmir-tensions",
                "title": "Cross-border shelling resumes along Line of Control",
                "source": "aljazeera",
                "summary": "India and Pakistan exchange fire along the LoC as tensions in Kashmir reach new heights.",
            },
        ],
    },
    {
        "title": "US Announces New Sanctions Package Against Russia",
        "summary": "The United States has imposed a sweeping new round of sanctions targeting Russian financial institutions, energy companies, and senior government officials.",
        "event_type": EventType.SANCTIONS,
        "severity": SeverityLevel.MEDIUM,
        "location_name": "Washington DC",
        "latitude": 38.9,
        "longitude": -77.04,
        "countries": "US,RU",
        "articles": [
            {
                "url": "https://example.com/us-russia-sanctions",
                "title": "Biden administration unveils most extensive Russia sanctions yet",
                "source": "ap",
                "summary": "New sanctions target Russia's largest banks and energy sector.",
            },
        ],
    },
    {
        "title": "Houthi Forces Attack Commercial Shipping in Red Sea",
        "summary": "Yemen's Houthi rebels have launched multiple missile and drone attacks against commercial vessels transiting the Bab el-Mandeb strait, disrupting global shipping routes.",
        "event_type": EventType.NAVAL_BLOCKADE,
        "severity": SeverityLevel.HIGH,
        "location_name": "Bab el-Mandeb",
        "latitude": 12.8,
        "longitude": 43.35,
        "countries": "YE",
        "articles": [
            {
                "url": "https://example.com/houthi-red-sea",
                "title": "Houthi attacks force major shipping companies to reroute from Red Sea",
                "source": "reuters",
                "summary": "Commercial vessels avoid Red Sea as Houthi attacks intensify.",
            },
        ],
    },
    {
        "title": "Mass Protests in Tbilisi Against Foreign Agent Law",
        "summary": "Hundreds of thousands of Georgians have taken to the streets of Tbilisi to protest a controversial 'foreign agent' law seen as Russian-influenced legislation that threatens EU membership prospects.",
        "event_type": EventType.INTERNAL_UNREST,
        "severity": SeverityLevel.MEDIUM,
        "location_name": "Tbilisi",
        "latitude": 41.69,
        "longitude": 44.8,
        "countries": "GE",
        "articles": [
            {
                "url": "https://example.com/georgia-protests",
                "title": "Massive protests rock Tbilisi as Georgians resist foreign agent law",
                "source": "guardian",
                "summary": "Pro-EU demonstrators flood the streets opposing Russia-style legislation.",
            },
        ],
    },
    {
        "title": "M23 Rebels Advance Toward Goma in Eastern DRC",
        "summary": "The M23 rebel group has made significant territorial gains in North Kivu province, advancing toward the city of Goma and displacing tens of thousands of civilians.",
        "event_type": EventType.CONFLICT,
        "severity": SeverityLevel.HIGH,
        "location_name": "Eastern Congo",
        "latitude": -2.0,
        "longitude": 29.0,
        "countries": "CD,RW",
        "articles": [
            {
                "url": "https://example.com/drc-m23",
                "title": "M23 rebels threaten Goma as DRC conflict intensifies",
                "source": "bbc",
                "summary": "Rebels backed by Rwanda advance in Eastern DRC, causing mass displacement.",
            },
        ],
    },
    {
        "title": "Sudan Civil War Humanitarian Crisis Deepens",
        "summary": "The ongoing civil war between the Sudanese Armed Forces and the Rapid Support Forces has created one of the world's worst humanitarian disasters, with millions displaced.",
        "event_type": EventType.HUMANITARIAN,
        "severity": SeverityLevel.CRITICAL,
        "location_name": "Khartoum",
        "latitude": 15.59,
        "longitude": 32.53,
        "countries": "SD",
        "articles": [
            {
                "url": "https://example.com/sudan-crisis",
                "title": "UN warns of famine as Sudan conflict enters second year",
                "source": "aljazeera",
                "summary": "Millions face starvation as fighting between SAF and RSF continues.",
            },
        ],
    },
    {
        "title": "North Korea Fires Ballistic Missiles Into Sea of Japan",
        "summary": "North Korea has launched multiple ballistic missiles toward the Sea of Japan, prompting emergency security meetings in South Korea and Japan.",
        "event_type": EventType.MILITARY_MOVEMENT,
        "severity": SeverityLevel.HIGH,
        "location_name": "Korean DMZ",
        "latitude": 38.5,
        "longitude": 126.97,
        "countries": "KP,KR,JP",
        "articles": [
            {
                "url": "https://example.com/nk-missiles",
                "title": "North Korea launches multiple ballistic missiles in latest provocation",
                "source": "npr",
                "summary": "Pyongyang fires series of ballistic missiles as regional tensions mount.",
            },
        ],
    },
    {
        "title": "EU-China Trade Dispute Over Electric Vehicle Tariffs",
        "summary": "The European Union has imposed significant tariffs on Chinese electric vehicle imports, prompting retaliatory trade measures from Beijing.",
        "event_type": EventType.TRADE_DISPUTE,
        "severity": SeverityLevel.MEDIUM,
        "location_name": "Beijing",
        "latitude": 39.91,
        "longitude": 116.39,
        "countries": "CN,EU",
        "articles": [
            {
                "url": "https://example.com/eu-china-tariffs",
                "title": "EU slaps tariffs on Chinese EVs as trade war escalates",
                "source": "reuters",
                "summary": "New tariffs on Chinese electric vehicles threaten broader trade conflict.",
            },
        ],
    },
    {
        "title": "Israeli Military Operation in Gaza Strip Continues",
        "summary": "The Israeli Defense Forces continue large-scale military operations in the Gaza Strip, with ongoing airstrikes and ground operations amidst a severe humanitarian crisis.",
        "event_type": EventType.CONFLICT,
        "severity": SeverityLevel.CRITICAL,
        "location_name": "Gaza Strip",
        "latitude": 31.5,
        "longitude": 35.5,
        "countries": "IL,PS",
        "articles": [
            {
                "url": "https://example.com/gaza-operation",
                "title": "Israeli forces expand operations in Gaza as ceasefire talks stall",
                "source": "cnn",
                "summary": "Military operations continue in Gaza with no ceasefire agreement in sight.",
            },
            {
                "url": "https://example.com/gaza-humanitarian",
                "title": "UN agencies warn of catastrophic humanitarian conditions in Gaza",
                "source": "guardian",
                "summary": "Aid organizations struggle to deliver supplies as conflict intensifies.",
            },
        ],
    },
]


async def seed_database():
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=True)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        for event_data in SAMPLE_EVENTS:
            articles_data = event_data.pop("articles", [])

            event = Event(**event_data)
            event.created_at = datetime.utcnow() - timedelta(hours=len(SAMPLE_EVENTS))
            session.add(event)
            await session.flush()

            for article_data in articles_data:
                article = Article(
                    **article_data,
                    event_id=event.id,
                    published_at=datetime.utcnow() - timedelta(hours=2),
                )
                session.add(article)

        await session.commit()

    await engine.dispose()
    print(f"Seeded {len(SAMPLE_EVENTS)} events with articles.")


if __name__ == "__main__":
    asyncio.run(seed_database())
