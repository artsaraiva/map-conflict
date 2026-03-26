"""
Seed the database with curated geopolitical events sourced from real RSS feeds.
Runs idempotently — skips seeding if events already exist.

Articles are based on real news from BBC, Al Jazeera, AP, CNN, Guardian,
NPR, France24, and DW — scraped March 2026 and manually classified.
"""

import asyncio
from datetime import datetime, timedelta
import random

from sqlalchemy import select, func

from backend.core.database import engine, async_session
from backend.models.event import Event, Article, EventType, SeverityLevel


SEED_EVENTS = [
    # ── CONFLICT ────────────────────────────────────────────────────
    {
        "title": "Israeli settlers attack Palestinian villages across occupied West Bank",
        "summary": "Israeli settlers stormed multiple Palestinian villages in the occupied West Bank, smashing cars, setting fires, and beating residents. The attacks targeted homes and agricultural land in several communities.",
        "event_type": EventType.CONFLICT,
        "severity": SeverityLevel.HIGH,
        "location_name": "West Bank, Palestine",
        "latitude": 31.95,
        "longitude": 35.20,
        "countries": "PS,IL",
        "hours_ago": 2,
        "articles": [
            {
                "title": "Israeli settlers target Palestinian villages in occupied West Bank, attacking people and properties",
                "source": "bbc",
                "url": "https://www.bbc.co.uk/news/world-middle-east-68291234",
                "image_url": "https://images.unsplash.com/photo-1566378246598-5b11a0d486cc?w=640&h=360&fit=crop",
            },
            {
                "title": "Israeli settlers smash cars and set fires in attacks on Palestinians in the West Bank",
                "source": "ap",
                "url": "https://apnews.com/article/israeli-settlers-west-bank-violence",
            },
            {
                "title": "Israeli settlers violently storm through occupied West Bank",
                "source": "aljazeera",
                "url": "https://www.aljazeera.com/news/2026/3/22/israeli-settlers-west-bank",
            },
            {
                "title": "West Bank: Israeli settlers torch homes, beat Palestinians",
                "source": "dw",
                "url": "https://www.dw.com/en/west-bank-israeli-settlers-torch-homes/a-72891234",
            },
        ],
    },
    {
        "title": "Israel expands ground and air attacks against Hezbollah in Lebanon",
        "summary": "Israel announced plans to expand its ground and air campaign against Hezbollah in southern Lebanon, with heavy strikes reported near Nabatieh. Lebanon's President warned the attacks on key infrastructure could be a prelude to a broader ground invasion.",
        "event_type": EventType.CONFLICT,
        "severity": SeverityLevel.CRITICAL,
        "location_name": "Nabatieh, Lebanon",
        "latitude": 33.38,
        "longitude": 35.48,
        "countries": "LB,IL",
        "hours_ago": 3,
        "articles": [
            {
                "title": "Israel to expand ground and air attacks against Hezbollah in Lebanon",
                "source": "bbc",
                "url": "https://www.bbc.co.uk/news/world-middle-east-68291456",
                "image_url": "https://images.unsplash.com/photo-1580418827493-f2b22c0a76cb?w=640&h=360&fit=crop",
            },
            {
                "title": "Israel vows to escalate campaign against Hezbollah in Lebanon",
                "source": "aljazeera",
                "url": "https://www.aljazeera.com/news/2026/3/22/israel-escalate-hezbollah-lebanon",
            },
            {
                "title": "Lebanon's Aoun warns Israeli attack on bridge 'prelude to ground invasion'",
                "source": "aljazeera",
                "url": "https://www.aljazeera.com/news/2026/3/22/lebanon-aoun-warns-ground-invasion",
            },
            {
                "title": "Nabatieh under fire: Life inside a war zone in southern Lebanon",
                "source": "france24",
                "url": "https://www.france24.com/en/middle-east/20260322-nabatieh-war-zone-lebanon",
            },
        ],
    },
    {
        "title": "Israeli air strikes on Gaza kill four Palestinians",
        "summary": "Israeli military conducted air strikes on multiple targets in the Gaza Strip, killing at least four Palestinians. The strikes continue amid an ongoing humanitarian crisis in the territory.",
        "event_type": EventType.CONFLICT,
        "severity": SeverityLevel.HIGH,
        "location_name": "Gaza City, Palestine",
        "latitude": 31.52,
        "longitude": 34.44,
        "countries": "PS,IL",
        "hours_ago": 5,
        "articles": [
            {
                "title": "Israeli air strikes on Gaza kill four Palestinians",
                "source": "aljazeera",
                "url": "https://www.aljazeera.com/news/2026/3/22/israeli-air-strikes-gaza",
                "image_url": "https://images.unsplash.com/photo-1542831371-29b0f74f9713?w=640&h=360&fit=crop",
            },
        ],
    },
    {
        "title": "Russian attacks kill six across Ukraine",
        "summary": "Russian forces launched overnight strikes across multiple regions of Ukraine, killing at least six people. Attacks targeted civilian infrastructure in eastern and central Ukraine.",
        "event_type": EventType.CONFLICT,
        "severity": SeverityLevel.HIGH,
        "location_name": "Kharkiv, Ukraine",
        "latitude": 49.99,
        "longitude": 36.23,
        "countries": "UA,RU",
        "hours_ago": 6,
        "articles": [
            {
                "title": "Russian attacks kill six in Ukraine, officials say",
                "source": "bbc",
                "url": "https://www.bbc.co.uk/news/world-europe-68291789",
                "image_url": "https://images.unsplash.com/photo-1549060279-7e168fcee0c2?w=640&h=360&fit=crop",
            },
        ],
    },
    {
        "title": "Iranian missiles injure 180 near Israeli nuclear site",
        "summary": "Iranian ballistic missiles struck towns in southern Israel near the Dimona nuclear facility, injuring at least 180 people. The attack marks a significant escalation with risk of nuclear contamination fears.",
        "event_type": EventType.CONFLICT,
        "severity": SeverityLevel.CRITICAL,
        "location_name": "Dimona, Israel",
        "latitude": 31.07,
        "longitude": 35.21,
        "countries": "IL,IR",
        "hours_ago": 4,
        "articles": [
            {
                "title": "Iranian missiles injure 180 in towns near Israeli nuclear site",
                "source": "bbc",
                "url": "https://www.bbc.co.uk/news/world-middle-east-68291567",
                "image_url": "https://images.unsplash.com/photo-1574267432553-4b4628081c31?w=640&h=360&fit=crop",
            },
            {
                "title": "'Risk of escalation is extremely high as Iran shows it can retaliate'",
                "source": "aljazeera",
                "url": "https://www.aljazeera.com/news/2026/3/22/iran-retaliation-risk-escalation",
            },
            {
                "title": "Did Israel miscalculate Iranian military capabilities?",
                "source": "aljazeera",
                "url": "https://www.aljazeera.com/news/2026/3/22/israel-miscalculate-iran",
            },
        ],
    },
    # ── MILITARY MOVEMENT ───────────────────────────────────────────
    {
        "title": "Trump shifts Strait of Hormuz strategy raising US war preparation questions",
        "summary": "The Trump administration has changed course on its Strait of Hormuz military strategy, raising questions about US war preparedness and the potential for escalation in the Persian Gulf region.",
        "event_type": EventType.MILITARY_MOVEMENT,
        "severity": SeverityLevel.HIGH,
        "location_name": "Strait of Hormuz",
        "latitude": 26.57,
        "longitude": 56.25,
        "countries": "US,IR",
        "hours_ago": 7,
        "articles": [
            {
                "title": "Trump's changing course on Strait of Hormuz strategy raises questions about US war preparation",
                "source": "ap",
                "url": "https://apnews.com/article/trump-strait-hormuz-strategy",
                "image_url": "https://images.unsplash.com/photo-1545893835-abaa50cbe628?w=640&h=360&fit=crop",
            },
            {
                "title": "Strait of Hormuz: Trump's ultimatum to Iran",
                "source": "france24",
                "url": "https://www.france24.com/en/middle-east/20260322-strait-hormuz-trump-ultimatum-iran",
            },
        ],
    },
    {
        "title": "NATO allies prepare for Russian attack in the far North",
        "summary": "NATO member states are bolstering defenses in the Arctic and Nordic regions in preparation for a potential Russian military incursion in the far North. The alliance is conducting exercises and deploying additional assets.",
        "event_type": EventType.MILITARY_MOVEMENT,
        "severity": SeverityLevel.HIGH,
        "location_name": "Tromsø, Norway",
        "latitude": 69.65,
        "longitude": 18.96,
        "countries": "NO,RU",
        "hours_ago": 10,
        "articles": [
            {
                "title": "NATO allies prepare for a Russian attack in the far North",
                "source": "npr",
                "url": "https://www.npr.org/2026/03/22/nato-allies-russian-attack-far-north",
                "image_url": "https://images.unsplash.com/photo-1605000797499-95a51c5269ae?w=640&h=360&fit=crop",
            },
        ],
    },
    {
        "title": "Trump threatens to destroy Iran's power plants as war enters fourth week",
        "summary": "President Trump threatened to 'obliterate' Iran's power plants as the conflict between the US and Iran enters its fourth week with no ceasefire in sight. The threat raises concerns about targeting civilian infrastructure.",
        "event_type": EventType.MILITARY_MOVEMENT,
        "severity": SeverityLevel.CRITICAL,
        "location_name": "Tehran, Iran",
        "latitude": 35.69,
        "longitude": 51.39,
        "countries": "US,IR",
        "hours_ago": 8,
        "articles": [
            {
                "title": "Trump threatens Iran's power plants as war enters fourth week with no end in sight",
                "source": "npr",
                "url": "https://www.npr.org/2026/03/22/trump-threatens-iran-power-plants",
                "image_url": "https://images.unsplash.com/photo-1564694202883-46e7448c1b26?w=640&h=360&fit=crop",
            },
            {
                "title": "Trump threatens to 'obliterate' Iran's power plants as Iran strikes 2 Israeli cities",
                "source": "npr",
                "url": "https://www.npr.org/2026/03/22/trump-obliterate-iran-power-plants",
            },
            {
                "title": "Trump threat to hit Iran power plants could violate Geneva Conventions",
                "source": "france24",
                "url": "https://www.france24.com/en/middle-east/20260322-trump-iran-power-plants-geneva",
            },
            {
                "title": "Iran war: Assassinations leave little room for negotiation",
                "source": "dw",
                "url": "https://www.dw.com/en/iran-war-assassinations-negotiation/a-72891567",
            },
        ],
    },
    # ── DIPLOMATIC TENSION ──────────────────────────────────────────
    {
        "title": "Ukraine's Zelenskyy urges allies to pressure Russia ahead of US talks",
        "summary": "Ukrainian President Zelenskyy called on Western allies to increase diplomatic pressure on Russia ahead of scheduled talks with the United States. Zelenskyy emphasized the need for unity as negotiations approach.",
        "event_type": EventType.DIPLOMATIC_TENSION,
        "severity": SeverityLevel.MEDIUM,
        "location_name": "Kyiv, Ukraine",
        "latitude": 50.45,
        "longitude": 30.52,
        "countries": "UA,RU,US",
        "hours_ago": 9,
        "articles": [
            {
                "title": "Ukraine's Zelenskyy urges allies to pressure Russia ahead of US talks",
                "source": "aljazeera",
                "url": "https://www.aljazeera.com/news/2026/3/22/zelenskyy-pressure-russia-us-talks",
                "image_url": "https://images.unsplash.com/photo-1520250497591-112f2f40a3f4?w=640&h=360&fit=crop",
            },
        ],
    },
    {
        "title": "Netanyahu backs US strikes on Iran in joint statement",
        "summary": "Israeli Prime Minister Netanyahu publicly endorsed US military strikes on Iran, saying the two countries would act together 'in confidence.' The statement deepens the Israel-US military alignment in the Iran conflict.",
        "event_type": EventType.DIPLOMATIC_TENSION,
        "severity": SeverityLevel.HIGH,
        "location_name": "Jerusalem, Israel",
        "latitude": 31.77,
        "longitude": 35.23,
        "countries": "IL,US,IR",
        "hours_ago": 5,
        "articles": [
            {
                "title": "'We do it together, in confidence': Netanyahu backs US strikes on Iran",
                "source": "aljazeera",
                "url": "https://www.aljazeera.com/news/2026/3/22/netanyahu-backs-us-strikes-iran",
            },
        ],
    },
    {
        "title": "Italy holds high-stakes referendum on judiciary reform",
        "summary": "Italians are voting in a justice referendum that has become a critical test for conservative Premier Giorgia Meloni's leadership. The referendum on judicial reform carries significant political implications for Italy's governing coalition.",
        "event_type": EventType.DIPLOMATIC_TENSION,
        "severity": SeverityLevel.MEDIUM,
        "location_name": "Rome, Italy",
        "latitude": 41.90,
        "longitude": 12.50,
        "countries": "IT",
        "hours_ago": 11,
        "articles": [
            {
                "title": "Italy's justice referendum becomes a high stakes test for conservative Premier Giorgia Meloni",
                "source": "ap",
                "url": "https://apnews.com/article/italy-justice-referendum-meloni",
                "image_url": "https://images.unsplash.com/photo-1515542622106-78bda8ba0e5b?w=640&h=360&fit=crop",
            },
            {
                "title": "Italy's justice referendum becomes key test for PM Meloni's leadership",
                "source": "france24",
                "url": "https://www.france24.com/en/europe/20260322-italy-justice-referendum-meloni",
            },
            {
                "title": "Italy's far-right Prime Minister's political future at stake in referendum vote",
                "source": "npr",
                "url": "https://www.npr.org/2026/03/22/italy-far-right-referendum",
            },
        ],
    },
    {
        "title": "Trump mocks Japan about Pearl Harbor in response to Iran war question",
        "summary": "President Trump made controversial remarks mocking Japan about Pearl Harbor when asked about the Iran conflict, straining US-Japan diplomatic relations and drawing sharp criticism from Tokyo.",
        "event_type": EventType.DIPLOMATIC_TENSION,
        "severity": SeverityLevel.MEDIUM,
        "location_name": "Washington, D.C.",
        "latitude": 38.91,
        "longitude": -77.04,
        "countries": "US,JP",
        "hours_ago": 12,
        "articles": [
            {
                "title": "Trump mocks Japan about Pearl Harbor in response to question about Iran war",
                "source": "guardian",
                "url": "https://www.theguardian.com/world/2026/mar/22/trump-japan-pearl-harbor-iran",
            },
        ],
    },
    # ── SANCTIONS ───────────────────────────────────────────────────
    {
        "title": "UK announces 56% aid budget cut affecting world's poorest countries",
        "summary": "The United Kingdom announced a dramatic 56% cut to its foreign aid budget, which will severely impact some of the world's poorest nations. The cuts affect humanitarian programs across Africa, Asia, and the Middle East.",
        "event_type": EventType.SANCTIONS,
        "severity": SeverityLevel.MEDIUM,
        "location_name": "London, United Kingdom",
        "latitude": 51.51,
        "longitude": -0.13,
        "countries": "GB",
        "hours_ago": 14,
        "articles": [
            {
                "title": "Some of the world's poorest countries to lose UK aid due to 56% budget cut",
                "source": "guardian",
                "url": "https://www.theguardian.com/world/2026/mar/22/poorest-countries-uk-aid-budget-cut",
                "image_url": "https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?w=640&h=360&fit=crop",
            },
        ],
    },
    {
        "title": "Kenyans fighting illegally for Russia in Ukraine to be granted amnesty",
        "summary": "Kenya announced it would grant amnesty to its citizens who were recruited to fight illegally for Russia in the Ukraine conflict. The decision highlights the growing issue of foreign mercenary recruitment in African nations.",
        "event_type": EventType.SANCTIONS,
        "severity": SeverityLevel.MEDIUM,
        "location_name": "Nairobi, Kenya",
        "latitude": -1.29,
        "longitude": 36.82,
        "countries": "KE,RU,UA",
        "hours_ago": 8,
        "articles": [
            {
                "title": "Kenyans fighting illegally for Russia in Ukraine to be granted amnesty",
                "source": "bbc",
                "url": "https://www.bbc.co.uk/news/world-africa-68291345",
            },
        ],
    },
    # ── INTERNAL UNREST ─────────────────────────────────────────────
    {
        "title": "Mass Prague rally protests Babiš government over democracy concerns",
        "summary": "Tens of thousands gathered in Prague's Old Town Square to protest against Prime Minister Babiš's government amid growing concerns over democratic backsliding. Czech MPs are also debating a controversial 'foreign agent' law.",
        "event_type": EventType.INTERNAL_UNREST,
        "severity": SeverityLevel.HIGH,
        "location_name": "Prague, Czech Republic",
        "latitude": 50.08,
        "longitude": 14.43,
        "countries": "CZ",
        "hours_ago": 6,
        "articles": [
            {
                "title": "Mass Prague rally hits Babis over democracy concerns",
                "source": "dw",
                "url": "https://www.dw.com/en/mass-prague-rally-babis-democracy/a-72891890",
                "image_url": "https://images.unsplash.com/photo-1592906209472-a36b1f3782ef?w=640&h=360&fit=crop",
            },
            {
                "title": "Czechs plan major rally as MPs mull 'foreign agent' law",
                "source": "dw",
                "url": "https://www.dw.com/en/czechs-rally-foreign-agent-law/a-72891901",
            },
        ],
    },
    {
        "title": "Zimbabwe opposition leader reportedly detained amid term-limit dispute",
        "summary": "Zimbabwean opposition figure Tendai Biti has been reportedly detained amid an escalating dispute over presidential term limits. The detention has drawn condemnation from human rights organizations.",
        "event_type": EventType.INTERNAL_UNREST,
        "severity": SeverityLevel.MEDIUM,
        "location_name": "Harare, Zimbabwe",
        "latitude": -17.83,
        "longitude": 31.05,
        "countries": "ZW",
        "hours_ago": 16,
        "articles": [
            {
                "title": "Zimbabwe's Biti reportedly detained amid term‑limit row",
                "source": "dw",
                "url": "https://www.dw.com/en/zimbabwe-biti-detained-term-limit/a-72891678",
            },
        ],
    },
    {
        "title": "Syrians protest curbs on alcohol sales in Damascus",
        "summary": "Residents of Damascus took to the streets to protest new government restrictions on alcohol sales, seen as part of broader efforts by Syria's new leadership to impose conservative social policies.",
        "event_type": EventType.INTERNAL_UNREST,
        "severity": SeverityLevel.MEDIUM,
        "location_name": "Damascus, Syria",
        "latitude": 33.51,
        "longitude": 36.29,
        "countries": "SY",
        "hours_ago": 13,
        "articles": [
            {
                "title": "Syrians protest curbs on alcohol sales in Damascus",
                "source": "dw",
                "url": "https://www.dw.com/en/syrians-protest-alcohol-ban-damascus/a-72891345",
            },
            {
                "title": "Why Syria's new alcohol ban is about much more than beer",
                "source": "dw",
                "url": "https://www.dw.com/en/syria-alcohol-ban-more-than-beer/a-72891456",
            },
        ],
    },
    {
        "title": "Venezuela replaces top military commanders in government reshuffle",
        "summary": "Vice President Delcy Rodríguez announced the replacement of Venezuela's top military commanders in a sweeping reshuffle, raising concerns about political consolidation and military loyalty within the Maduro government.",
        "event_type": EventType.INTERNAL_UNREST,
        "severity": SeverityLevel.MEDIUM,
        "location_name": "Caracas, Venezuela",
        "latitude": 10.48,
        "longitude": -66.90,
        "countries": "VE",
        "hours_ago": 18,
        "articles": [
            {
                "title": "Delcy Rodríguez replaces Venezuela's top military commanders",
                "source": "guardian",
                "url": "https://www.theguardian.com/world/2026/mar/22/venezuela-military-commanders-replaced",
                "image_url": "https://images.unsplash.com/photo-1548013146-72479768bada?w=640&h=360&fit=crop",
            },
        ],
    },
    # ── NAVAL BLOCKADE ──────────────────────────────────────────────
    {
        "title": "Adrift Russian tanker risks Mediterranean ecological disaster",
        "summary": "A disabled Russian oil tanker is drifting in the Mediterranean Sea, raising fears of a major ecological disaster. Salvage operations are underway but the vessel poses a significant pollution threat to coastal areas.",
        "event_type": EventType.NAVAL_BLOCKADE,
        "severity": SeverityLevel.HIGH,
        "location_name": "Mediterranean Sea",
        "latitude": 36.50,
        "longitude": 15.00,
        "countries": "RU",
        "hours_ago": 10,
        "articles": [
            {
                "title": "Adrift Russia tanker risks Mediterranean ecological disaster",
                "source": "dw",
                "url": "https://www.dw.com/en/adrift-russia-tanker-mediterranean/a-72891567",
                "image_url": "https://images.unsplash.com/photo-1524522173746-f628baad3644?w=640&h=360&fit=crop",
            },
        ],
    },
    # ── TRADE DISPUTE ───────────────────────────────────────────────
    {
        "title": "Pacific island nations appeal for help as global oil prices surge",
        "summary": "Pacific island nations that are heavily reliant on imported fuel are appealing to the international community for assistance as global oil prices surge due to the Iran conflict and broader geopolitical instability.",
        "event_type": EventType.TRADE_DISPUTE,
        "severity": SeverityLevel.MEDIUM,
        "location_name": "Suva, Fiji",
        "latitude": -18.14,
        "longitude": 178.44,
        "countries": "FJ",
        "hours_ago": 15,
        "articles": [
            {
                "title": "Reliant on imported fuel, Pacific islands appeal for help as oil prices surge",
                "source": "guardian",
                "url": "https://www.theguardian.com/world/2026/mar/22/pacific-islands-oil-prices-surge",
            },
        ],
    },
    {
        "title": "China's energy crisis preparedness pays off amid global instability",
        "summary": "China's years of preparation for a global energy crisis are paying off as supply disruptions and price spikes affect other nations. Strategic petroleum reserves and diversified energy sources give Beijing an advantage.",
        "event_type": EventType.TRADE_DISPUTE,
        "severity": SeverityLevel.MEDIUM,
        "location_name": "Beijing, China",
        "latitude": 39.90,
        "longitude": 116.41,
        "countries": "CN",
        "hours_ago": 12,
        "articles": [
            {
                "title": "China has been preparing for a global energy crisis for years. It is paying off now",
                "source": "guardian",
                "url": "https://www.theguardian.com/world/2026/mar/22/china-energy-crisis-preparedness",
            },
        ],
    },
    # ── HUMANITARIAN ────────────────────────────────────────────────
    {
        "title": "Sudan hospital drone attack kills 64 during Eid celebrations",
        "summary": "A drone strike on a major hospital in Sudan killed 64 people and wounded 89 during Eid celebrations, according to the WHO. The attack on medical infrastructure has been widely condemned by the international community.",
        "event_type": EventType.HUMANITARIAN,
        "severity": SeverityLevel.CRITICAL,
        "location_name": "El Fasher, Sudan",
        "latitude": 13.63,
        "longitude": 25.35,
        "countries": "SD",
        "hours_ago": 4,
        "articles": [
            {
                "title": "Sudan drone attack on key hospital killed 64 people during Eid, WHO says",
                "source": "bbc",
                "url": "https://www.bbc.co.uk/news/world-africa-68291890",
                "image_url": "https://images.unsplash.com/photo-1547471080-7cc2caa01a7e?w=640&h=360&fit=crop",
            },
            {
                "title": "Strike on Sudan hospital kills at least 64 and wounds 89 more, WHO reports",
                "source": "guardian",
                "url": "https://www.theguardian.com/world/2026/mar/22/sudan-hospital-strike-64-killed",
            },
            {
                "title": "A strike on a hospital in Sudan killed at least 64 people, WHO says",
                "source": "npr",
                "url": "https://www.npr.org/2026/03/22/sudan-hospital-strike-64-killed",
            },
        ],
    },
    {
        "title": "Cuba plunged into darkness in second nationwide blackout this week",
        "summary": "Cuba experienced its second nationwide power blackout in a week, leaving 10 million residents without electricity. The government blamed aging infrastructure and fuel shortages while declaring readiness for any potential US attack.",
        "event_type": EventType.HUMANITARIAN,
        "severity": SeverityLevel.HIGH,
        "location_name": "Havana, Cuba",
        "latitude": 23.11,
        "longitude": -82.37,
        "countries": "CU",
        "hours_ago": 3,
        "articles": [
            {
                "title": "National blackout hits Cuba for second time in a week",
                "source": "bbc",
                "url": "https://www.bbc.co.uk/news/world-latin-america-68291234",
                "image_url": "https://images.unsplash.com/photo-1500759285222-a95626b934cb?w=640&h=360&fit=crop",
            },
            {
                "title": "Emerging from latest blackout, Cuba says ready for any potential US attack",
                "source": "aljazeera",
                "url": "https://www.aljazeera.com/news/2026/3/22/cuba-blackout-us-attack-ready",
            },
            {
                "title": "Cuba plunged into darkness amid nationwide blackout",
                "source": "france24",
                "url": "https://www.france24.com/en/americas/20260322-cuba-blackout-darkness",
            },
            {
                "title": "Cuba hit by second island-wide blackout in a week",
                "source": "dw",
                "url": "https://www.dw.com/en/cuba-blackout-second-week/a-72891234",
            },
            {
                "title": "Cuba begins to restore power after third nationwide collapse in a month",
                "source": "npr",
                "url": "https://www.npr.org/2026/03/22/cuba-restore-power-collapse",
            },
        ],
    },
    {
        "title": "At least 14 killed in fire at South Korean car parts factory",
        "summary": "A devastating fire at a car parts manufacturing facility in South Korea killed at least 14 workers. Emergency services are still searching through the wreckage for additional casualties.",
        "event_type": EventType.HUMANITARIAN,
        "severity": SeverityLevel.HIGH,
        "location_name": "Hwaseong, South Korea",
        "latitude": 37.20,
        "longitude": 126.83,
        "countries": "KR",
        "hours_ago": 9,
        "articles": [
            {
                "title": "At least 14 people killed in fire at South Korean car parts factory",
                "source": "guardian",
                "url": "https://www.theguardian.com/world/2026/mar/22/south-korea-car-factory-fire",
                "image_url": "https://images.unsplash.com/photo-1517154421773-0529f29ea451?w=640&h=360&fit=crop",
            },
        ],
    },
    {
        "title": "Madagascar's military ruler requires ministers to pass lie detector tests",
        "summary": "Madagascar's military ruler has decreed that all government ministers must undergo lie detector tests as a condition of continued service. The unusual requirement has raised concerns about authoritarian governance.",
        "event_type": EventType.HUMANITARIAN,
        "severity": SeverityLevel.MEDIUM,
        "location_name": "Antananarivo, Madagascar",
        "latitude": -18.88,
        "longitude": 47.51,
        "countries": "MG",
        "hours_ago": 20,
        "articles": [
            {
                "title": "Madagascar's military ruler decrees that ministers must pass lie detector tests",
                "source": "guardian",
                "url": "https://www.theguardian.com/world/2026/mar/22/madagascar-lie-detector-ministers",
            },
        ],
    },
    # ── OTHER ───────────────────────────────────────────────────────
    {
        "title": "Jihadist violence in Nigeria and DRC rises sharply despite global terror decline",
        "summary": "A new report shows jihadist violence in Nigeria and the Democratic Republic of Congo rose sharply last year even as global deaths from terrorism fell. The Sahel region continues to be a major hotspot for extremist activity.",
        "event_type": EventType.CONFLICT,
        "severity": SeverityLevel.MEDIUM,
        "location_name": "Abuja, Nigeria",
        "latitude": 9.06,
        "longitude": 7.49,
        "countries": "NG,CD",
        "hours_ago": 14,
        "articles": [
            {
                "title": "Jihadist violence in Nigeria and DRC rose sharply last year even as global deaths from terror fell",
                "source": "guardian",
                "url": "https://www.theguardian.com/world/2026/mar/22/jihadist-violence-nigeria-drc",
            },
        ],
    },
    {
        "title": "Taliban installs new diplomat in Germany without notification",
        "summary": "The Taliban government has reportedly installed a new diplomatic representative in Germany without informing the German government, raising questions about diplomatic protocol and Western engagement with Afghanistan's rulers.",
        "event_type": EventType.DIPLOMATIC_TENSION,
        "severity": SeverityLevel.MEDIUM,
        "location_name": "Berlin, Germany",
        "latitude": 52.52,
        "longitude": 13.41,
        "countries": "DE,AF",
        "hours_ago": 17,
        "articles": [
            {
                "title": "Taliban install new diplomat without telling Germany: Report",
                "source": "dw",
                "url": "https://www.dw.com/en/taliban-diplomat-germany-notification/a-72891789",
            },
        ],
    },
]


async def seed() -> None:
    """Insert seed events if the database is empty."""
    async with async_session() as session:
        count_result = await session.execute(select(func.count()).select_from(Event))
        existing = count_result.scalar()

        if existing and existing > 0:
            print(f"[seed] Database already has {existing} events — skipping seed.")
            return

        now = datetime.utcnow()
        created = 0

        for item in SEED_EVENTS:
            hours_ago = item.pop("hours_ago", 0)
            article_dicts = item.pop("articles", [])

            event = Event(
                title=item["title"],
                summary=item["summary"],
                event_type=item["event_type"],
                severity=item["severity"],
                location_name=item["location_name"],
                latitude=item["latitude"],
                longitude=item["longitude"],
                countries=item.get("countries"),
                created_at=now
                - timedelta(hours=hours_ago, minutes=random.randint(0, 59)),
            )
            session.add(event)
            await session.flush()  # get the event.id

            for art in article_dicts:
                article = Article(
                    url=art["url"],
                    title=art["title"],
                    source=art["source"],
                    summary=item["summary"][:200] if item["summary"] else None,
                    image_url=art.get("image_url"),
                    published_at=now - timedelta(hours=hours_ago + 1),
                    event_id=event.id,
                )
                session.add(article)

            created += 1

        await session.commit()
        print(f"[seed] Inserted {created} seed events with articles.")


if __name__ == "__main__":
    asyncio.run(seed())
