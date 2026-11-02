import { describe, expect, it } from "vitest";
import { timeRange, visibleEvents } from "@/lib/map-view";

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
