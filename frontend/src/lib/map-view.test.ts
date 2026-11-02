import { describe, expect, it } from "vitest";
import { densityCells, timeRange, visibleEvents } from "@/lib/map-view";
import { SEVERITY_CONFIG } from "@/lib/types";

const event = (id: number, created_at: string) => ({ id, created_at });

const events = [
  event(1, "2026-11-01T10:00:00Z"),
  event(2, "2026-11-01T12:00:00Z"),
  event(3, "2026-11-01T14:00:00Z"),
];

describe("visible Events", () => {
  it("shows every Event in Live, when there is no cursor", () => {
    expect(visibleEvents(events, null).map((e) => e.id)).toEqual([1, 2, 3]);
  });

  it("shows only Events at or before the cursor", () => {
    const cursor = new Date("2026-11-01T13:00:00Z");
    expect(visibleEvents(events, cursor).map((e) => e.id)).toEqual([1, 2]);
  });

  it("shows an Event created exactly at the cursor", () => {
    const cursor = new Date("2026-11-01T12:00:00Z");
    expect(visibleEvents(events, cursor).map((e) => e.id)).toEqual([1, 2]);
  });
});

describe("time range", () => {
  it("runs from the oldest Event to now", () => {
    const now = new Date("2026-11-02T09:00:00Z");
    const shuffled = [events[2], events[0], events[1]];
    expect(timeRange(shuffled, now)).toEqual({
      start: new Date("2026-11-01T10:00:00Z"),
      end: now,
    });
  });

  it("ends at the new now when now moves", () => {
    const later = new Date("2026-11-02T10:30:00Z");
    expect(timeRange(events, later)).toEqual({
      start: new Date("2026-11-01T10:00:00Z"),
      end: later,
    });
  });

  it("covers the 72 hours before now when there are no Events", () => {
    const now = new Date("2026-11-04T12:00:00Z");
    expect(timeRange([], now)).toEqual({
      start: new Date("2026-11-01T12:00:00Z"),
      end: now,
    });
  });
});

const placed = (
  over: Partial<{
    latitude: number;
    longitude: number;
    event_type: "conflict" | "sanctions" | "military_movement";
    severity: "low" | "medium" | "high" | "critical";
    source_count: number | null;
    article_count: number;
  }> = {},
) => ({
  latitude: 48.1,
  longitude: 37.9,
  event_type: "conflict" as const,
  severity: "high" as const,
  source_count: 1,
  article_count: 1,
  ...over,
});

const shadeOf = (e: ReturnType<typeof placed>) => densityCells([e])[0].intensity;

describe("density cells", () => {
  it("puts two Events in the same cell and family into one cell", () => {
    const cells = densityCells([placed(), placed({ latitude: 48.2, longitude: 38.1 })]);
    expect(cells).toHaveLength(1);
    expect(cells[0].count).toBe(2);
  });

  it("keeps Events in different families in separate cells", () => {
    const cells = densityCells([placed(), placed({ event_type: "sanctions" })]);
    expect(cells).toHaveLength(2);
  });

  it("shades a cell more when its Event has more Sources, up to the cap", () => {
    expect(shadeOf(placed({ source_count: 3 }))).toBeGreaterThan(shadeOf(placed({ source_count: 1 })));
    expect(shadeOf(placed({ source_count: 20 }))).toBeCloseTo(shadeOf(placed({ source_count: 4 })));
    expect(shadeOf(placed({ severity: "high", source_count: 20 }))).toBeCloseTo(0.82 + 0.18);
  });

  it("does not change shading with Report count", () => {
    expect(shadeOf(placed({ article_count: 30 }))).toBe(shadeOf(placed({ article_count: 1 })));
  });

  it("shades a null Source count like a count of 1", () => {
    expect(shadeOf(placed({ source_count: null }))).toBe(shadeOf(placed({ source_count: 1 })));
  });
});

describe("Severity rank", () => {
  it("orders critical > high > medium > low", () => {
    const rank = (s: keyof typeof SEVERITY_CONFIG) => SEVERITY_CONFIG[s].rank;
    expect(rank("critical")).toBeGreaterThan(rank("high"));
    expect(rank("high")).toBeGreaterThan(rank("medium"));
    expect(rank("medium")).toBeGreaterThan(rank("low"));
  });
});
