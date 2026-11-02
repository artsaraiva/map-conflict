// Map view: what the map and panels show for a set of Events, a time cursor and
// the current time. Pure: no React, MapLibre or DOM, and the clock is always an argument.

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
