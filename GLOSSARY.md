# Geopolitics Map

A live map that turns fragmented news into a strategic world view: where pressure is building, how events connect, and how well each one is corroborated.

## Ingestion

**Feed**:
A channel through which Reports enter the system: Telegram, RSS, X, or GDELT. A Feed is plumbing, not a publisher.
_Avoid_: Source (when meaning the pipe), channel, provider

**Source**:
The organisation or person that published a Report, such as BBC, Reuters, `rnintel`, or `@OSINTdefender`. An organisation's website, X account, and Telegram channel are one Source, and the same Source reaching us through several Feeds is still one Source.
_Avoid_: Feed, outlet, publisher

**Report**:
A single item published by one Source and received through one Feed: a news story, a Telegram post, a tweet. A Report belongs to at most one Event; it belongs to none when it is not geopolitical or cannot be placed.
_Avoid_: Article, item, message, post

## Events

**Event**:
A single occurrence at one place and time, such as one strike, one interception, or one sanctions announcement. Further Reports about the same occurrence corroborate it; they never create a new Event.
_Avoid_: Incident, development, story

**Link**:
A typed relationship between two distinct Events, such as response to, escalation of, or same campaign. Similar wording alone is not a Link, only a hint that one may exist.
_Avoid_: Relationship, similarity, related event

**Chain**:
A sequence of Events connected by Links, such as attack, interception, retaliation.
_Avoid_: Thread, storyline, campaign

**Severity**:
How serious an Event is in itself: casualties, damage, scale. Says nothing about whether the Event is true.
_Avoid_: Priority, impact, strategic importance

**Confidence**:
How strongly we believe an Event happened as reported, grounded in its Corroboration.
_Avoid_: Reliability, credibility, accuracy

## Geography

**Strategic Location**:
A fixed place that matters regardless of current activity: a chokepoint, capital, major base, port, or energy site.
_Avoid_: Hotspot, point of interest

**Theater**:
A specific, named area where Events cluster and are briefed together, such as the Red Sea, Gaza, Donbas, or the Taiwan Strait. An Event outside every Theater is unassigned rather than forced into a broad region.
_Avoid_: Region, zone, area, continent-level groupings like "Middle East"

## Pressure

**Pressure**:
How much is going on in a Theater over a time window, weighing Events by severity and Corroboration.
_Avoid_: Heat, activity, hotspot

**Escalation**:
A rise in a Theater's Pressure compared with an earlier window.
_Avoid_: Spike, surge, flare-up

## Corroboration

**Corroboration**:
The number of distinct Sources whose Reports describe the same Event. Two Reports from the same Source count once, whatever Feeds they came through.
_Avoid_: Source count, feed count
