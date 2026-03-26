# Founder Strategy Memo

## What This Product Is

This product should become a real-time geopolitical pressure map: a system that turns fragmented news into a strategic world view.

It should not feel like a generic newsroom dashboard and it should not try to become a copy of LiveUAmap. The opportunity is to build a product that helps users understand not just what happened, but where pressure is building, how events connect, and which developments matter most.

## Current State

The current codebase is a credible V1 foundation.

- The backend stack is strong: `FastAPI`, `PostgreSQL + PostGIS`, `Celery`, `Redis`.
- The frontend stack is appropriate: `Next.js`, `React`, `MapLibre`.
- The product already has an event pipeline from Telegram ingestion through classification, geocoding, storage, and map display.
- The UI direction is already moving toward a command-center feel rather than a plain map with pins.

The project is not starting from zero. It already has the right core shape.

## Core Problems To Solve Next

### 1. The map is beginning to hit V1 performance limits

The current lag is most likely caused by frontend rendering behavior, especially animated layers and per-frame updates in `frontend/src/components/map/GeoMap.tsx`.

The issue is not that MapLibre is the wrong choice. The issue is that the product needs a more disciplined rendering model:

- fewer expensive updates per frame
- clustering when zoomed out
- viewport-aware querying
- clearer zoom-level behavior

### 2. Telegram alone is not enough

Telegram is useful because it is fast and often closer to the ground than traditional news. But a Telegram-only product will struggle with credibility, coverage, and source balance.

To become a serious geopolitical platform, the product needs multi-source ingestion:

- Telegram for fast signal
- RSS / major outlets for structured confirmation
- X for analyst, journalist, and official account monitoring
- later, structured feeds like GDELT for broader event coverage

### 3. The product still behaves more like an event map than a strategic surface

Today the product can show incidents. The next step is helping users understand:

- where pressure is building
- which regions are escalating
- which events are high-confidence vs noisy
- how incidents relate across time and geography

That is the real product leap.

## What To Learn From LiveUAmap

LiveUAmap is useful as a benchmark for principles, not as a template.

What it does well:

- fast scanning
- clear incident hierarchy
- strong region-based framing
- precise location emphasis
- image-backed immediacy

What this product should do differently:

- focus on global strategic visibility, not just local incident surfacing
- show pressure and escalation, not only isolated pins
- expose confidence and corroboration, not just feed velocity
- connect related developments across theaters
- feel more like an intelligence surface than a breaking-news list

## Product Positioning

The strongest positioning is:

**A live geopolitical command surface that reveals pressure, escalation, and strategic relevance across the world.**

This is more distinctive than calling it a war map, news map, or global alerts map.

It creates room for the product to cover:

- conflict
- diplomacy
- sanctions
- protests
- infrastructure disruption
- humanitarian crises
- military movement

without losing clarity.

## Best Near-Term Differentiators

These are the most important features that can make users prefer this product over simpler alternatives.

### 1. Pressure-first map design

When zoomed out, the user should first see pressure zones, clusters, and strategic hotspots, not thousands of equal-value pins.

This makes the product feel analytical rather than noisy.

### 2. Confidence and corroboration

Each event should eventually carry signals like:

- number of supporting sources
- source mix
- confidence score
- strategic importance score

This is one of the clearest ways to stand apart from generic event maps.

### 3. Strategic location layer

Important places should exist on the map even when no event is active there.

Examples:

- straits and maritime chokepoints
- capitals
- major bases
- ports
- energy infrastructure
- high-risk border zones

This adds context that makes the map feel more like a geopolitical instrument.

### 4. Regional briefings

The product should eventually summarize theaters, not just incidents.

Examples:

- what changed in the Red Sea in the last 24 hours
- where escalation is rising this week
- which regions are seeing military activity vs diplomatic movement

This turns the product into a tool for understanding, not just monitoring.

### 5. Event relationships

Longer term, the product should connect events into chains:

- attack
- interception
- retaliation
- diplomatic response
- market or infrastructure consequence

This is a major strategic differentiator.

## Technical Direction

## Phase 1: Foundation

Priority:

- fix map lag
- add clustering
- add viewport-aware event queries
- simplify or throttle expensive animation updates

Recommended direction:

- stay on `MapLibre`
- add `supercluster`
- keep the product in 2D
- optimize rendering before adding more spectacle

This is the fastest path to a noticeably better product.

## Phase 2: Data and intelligence

Priority:

- add RSS ingestion
- add X ingestion if account access is available
- add confidence and corroboration metadata
- improve deduplication and ranking

Recommended direction:

- create a source-adapter architecture
- normalize all incoming items into one ingestion model
- separate severity from confidence
- add tagging beyond a single event-type field

## Phase 3: Strategic UX

Priority:

- redesign zoom behavior around meaning, not just marker size
- show clusters and pressure when zoomed out
- show incidents and source detail when zoomed in
- highlight strategic locations continuously

Recommended direction:

- keep the map as the primary interface
- make the visual language family-based: conflict, diplomacy, sanctions, unrest, humanitarian, infrastructure
- use styling to support reading, not decoration

## Phase 4: Differentiation

Priority:

- confidence scoring
- strategic hotspots
- theater summaries
- event relationships
- timeline and replay

This is where the product stops being a strong demo and becomes its own category.

## 2D vs 3D

The product should stay in 2D for now.

That is the correct decision for performance, speed of execution, readability, and product clarity.

A 3D globe may look more impressive, but it is not the best near-term tool for fast geopolitical scanning. The strategy-game inspiration behind the product is better served by a strong 2D strategic map than by a premature globe transition.

The right approach is:

- build an excellent 2D strategic map first
- add lightweight animation carefully
- experiment with optional 3D or globe modes later only if they clearly improve comprehension

## Animated Events

Animated events are feasible in a web app, but they should be introduced in layers.

Start with:

- trajectory lines
- impact pulses
- directional arcs

Do not jump immediately to heavy cinematic effects.

The product should feel alive, but never at the cost of clarity or speed.

## Recommended Execution Order

### Realistic version

1. Improve map performance in `frontend/src/components/map/GeoMap.tsx`
2. Add clustering and better zoom-state behavior
3. Add viewport-aware backend map queries
4. Expand ingestion to RSS and then X
5. Add confidence, corroboration, and strategic hotspots
6. Improve theater-level summaries and filtering

### Ambitious version

1. Everything in the realistic version
2. Add semantic event grouping and stronger relationship modeling
3. Add replay / timeline features
4. Add selective animated tactical layers
5. Add optional advanced map modes later

## Final Recommendation

Do not position this product as a better LiveUAmap.

Position it as a more strategic product category:

**the best way to see where the world is heating up, why it matters, and how events connect.**

That direction fits the current codebase, supports the existing design ambition, and creates a clearer path to a product users would actively choose instead of treating as just another map of news pins.
