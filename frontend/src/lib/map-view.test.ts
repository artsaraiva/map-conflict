import { describe, expect, it } from "vitest";
import { expression, latest } from "@maplibre/maplibre-gl-style-spec";
import { densityCells, densityOpacity, pressureShade, timeRange, visibleEvents } from "@/lib/map-view";
import { EventType, SEVERITY_CONFIG, SeverityLevel } from "@/lib/types";

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
    event_type: EventType;
    severity: SeverityLevel;
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

  it("shades unknown Corroboration like one Source", () => {
    expect(shadeOf(placed({ source_count: null }))).toBe(shadeOf(placed({ source_count: 1 })));
  });
});

// Paints a density layer's opacity for a cell the way MapLibre would.
const paintedOpacity = (cells: ReturnType<typeof densityCells>, zoom: number) => {
  const parsed = expression.createPropertyExpression(
    densityOpacity([
      [1.5, 0.2],
      [8, 0.05],
    ]),
    latest.paint_circle["circle-opacity"],
  );
  if (parsed.result !== "success") throw new Error(parsed.value.map((e) => e.message).join("; "));
  return parsed.value.evaluate({ zoom }, { type: "Point", properties: { ...cells[0] } } as never);
};

describe("density opacity", () => {
  it("paints a cell with more Corroboration more strongly", () => {
    const fewer = densityCells([placed({ source_count: 1 })]);
    const more = densityCells([placed({ source_count: 4 })]);
    expect(paintedOpacity(more, 1.5)).toBeGreaterThan(paintedOpacity(fewer, 1.5));
  });

  it("paints one high Event with one Source at about the layer's opacity", () => {
    const typical = densityCells([placed({ severity: "high", source_count: 1 })]);
    expect(paintedOpacity(typical, 1.5)).toBeCloseTo(0.2, 1);
    expect(paintedOpacity(typical, 8)).toBeCloseTo(0.05, 1);
  });

  it("paints a crowded cell at no more than twice the layer's opacity", () => {
    const crowded = densityCells(Array.from({ length: 10 }, () => placed({ severity: "critical", source_count: 9 })));
    expect(paintedOpacity(crowded, 1.5)).toBeCloseTo(0.4);
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

describe("Pressure shade", () => {
  it("gives a Theater at 0 no fill", () => {
    expect(pressureShade(0, 12)).toBe(0);
    expect(pressureShade(0, 0)).toBe(0);
  });

  it("fills the Theater with the most Pressure fully", () => {
    expect(pressureShade(12, 12)).toBe(1);
  });

  it("shades other Theaters relative to the most, keeping the faintest visible", () => {
    expect(pressureShade(6, 12)).toBeCloseTo(0.6);
    expect(pressureShade(0.01, 12)).toBeGreaterThan(0.2);
    expect(pressureShade(3, 12)).toBeLessThan(pressureShade(6, 12));
  });
});
