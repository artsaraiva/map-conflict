// Map view: what the map and panels show for a set of Events, a time cursor and
// the current time. Pure: no React, MapLibre or DOM, and the clock is always an argument.

import type { ExpressionSpecification } from "maplibre-gl";
import {
  EVENT_TYPE_CONFIG,
  EventMapPoint,
  EventVisualFamily,
  getEventVisualFamily,
  getSeverityWeight,
} from "@/lib/types";

interface Timed {
  created_at: string;
}

/** Events at or before the cursor; every Event when the cursor is null (Live). */
export function visibleEvents<T extends Timed>(events: T[], cursor: Date | null): T[] {
  if (!cursor) return events;
  return events.filter((e) => new Date(e.created_at) <= cursor);
}

export interface TimeRange {
  start: Date;
  end: Date;
}

const EMPTY_RANGE_MS = 72 * 3600 * 1000;

/** The span the timeline covers: from the oldest Event to now, or the 72 hours before now with no Events. */
export function timeRange(events: Timed[], now: Date): TimeRange {
  const oldest = events.reduce(
    (min, e) => Math.min(min, new Date(e.created_at).getTime()),
    events.length ? Infinity : now.getTime() - EMPTY_RANGE_MS,
  );
  return { start: new Date(oldest), end: now };
}

type Placed = Pick<EventMapPoint, "latitude" | "longitude" | "event_type" | "severity" | "source_count">;

/** One 0.5° cell of the density wash for one visual family. */
export interface DensityCell {
  key: string;
  family: EventVisualFamily;
  latitude: number;
  longitude: number;
  count: number;
  intensity: number;
  radius: number;
  color: string;
  densityColor: string;
}

/**
 * Events grouped by 0.5° cell and visual family. Each Event shades its cell by its
 * Severity weight plus its Corroboration (Source count, capped), never its Report count.
 */
export function densityCells(events: Placed[]): DensityCell[] {
  const cells = new Map<string, DensityCell>();

  for (const event of events) {
    const latitude = Math.round(event.latitude * 2) / 2;
    const longitude = Math.round(event.longitude * 2) / 2;
    const family = getEventVisualFamily(event.event_type);
    const key = `${latitude}:${longitude}:${family}`;
    const severityWeight = getSeverityWeight(event.severity);
    const influence = severityWeight + Math.min((event.source_count ?? 1) * 0.05, 0.18);

    const cell = cells.get(key);
    if (cell) {
      cell.intensity += influence;
      cell.count += 1;
      cell.radius = Math.min(cell.radius + severityWeight * 10, 90);
      continue;
    }

    const typeConfig = EVENT_TYPE_CONFIG[event.event_type];
    cells.set(key, {
      key,
      family,
      latitude,
      longitude,
      count: 1,
      intensity: influence,
      radius: 26 + severityWeight * 32,
      color: typeConfig?.color ?? "#8e97ab",
      densityColor: typeConfig?.densityColor ?? "rgba(142, 151, 171, 0.16)",
    });
  }

  return [...cells.values()];
}

// One high Event with one Source paints at a density layer's own opacity.
const TYPICAL_INTENSITY = 0.87;
const MAX_INTENSITY_SCALE = 2;

/**
 * A density layer's opacity by zoom, each stop scaled by its cell's intensity so
 * better-corroborated, more severe cells paint stronger, up to twice the stop.
 */
export function densityOpacity(stops: [zoom: number, opacity: number][]): ExpressionSpecification {
  const scale: ExpressionSpecification = [
    "min",
    ["/", ["get", "intensity"], TYPICAL_INTENSITY],
    MAX_INTENSITY_SCALE,
  ];
  return [
    "interpolate",
    ["linear"],
    ["zoom"],
    ...stops.flatMap(([zoom, opacity]) => [zoom, ["*", opacity, scale]]),
  ] as ExpressionSpecification;
}
