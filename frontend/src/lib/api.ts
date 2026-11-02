import { EventMapPoint, GeoEvent, EventLink, MapFilters, MapBounds } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** Resolve relative media paths (e.g. /media/telegram/...) to absolute backend URLs */
function resolveMediaUrl(url: string | null): string | null {
  if (!url) return null;
  if (url.startsWith("/media/")) return `${API_URL}${url}`;
  return url;
}

/** Resolve media URLs in an EventMapPoint */
function resolveMapPoint(point: EventMapPoint): EventMapPoint {
  return { ...point, image_url: resolveMediaUrl(point.image_url) };
}

/** Resolve media URLs in a full GeoEvent (including nested articles) */
function resolveGeoEvent(event: GeoEvent): GeoEvent {
  return {
    ...event,
    articles: event.articles.map((a) => ({
      ...a,
      image_url: resolveMediaUrl(a.image_url),
      video_url: resolveMediaUrl(a.video_url),
    })),
  };
}

export async function fetchMapPoints(
  filters?: Partial<MapFilters>,
  bounds?: MapBounds,
): Promise<EventMapPoint[]> {
  const params = new URLSearchParams();
  const sinceHours = filters?.sinceHours ?? 72;
  params.set("since_hours", sinceHours.toString());

  if (filters?.eventTypes && filters.eventTypes.length > 0) {
    params.set("event_type", filters.eventTypes.join(","));
  }
  if (filters?.severities && filters.severities.length > 0) {
    params.set("severity", filters.severities.join(","));
  }
  if (filters?.theaters && filters.theaters.length > 0) {
    params.set("theater", filters.theaters.join(","));
  }
  if (bounds) {
    params.set("min_lat", bounds.minLat.toString());
    params.set("max_lat", bounds.maxLat.toString());
    params.set("min_lng", bounds.minLng.toString());
    params.set("max_lng", bounds.maxLng.toString());
  }

  const res = await fetch(
    `${API_URL}/api/events/map-points?${params}`
  );
  if (!res.ok) throw new Error("Failed to fetch map points");
  const data: EventMapPoint[] = await res.json();
  return data.map(resolveMapPoint);
}

export async function fetchStrategicLocations(): Promise<GeoJSON.FeatureCollection> {
  const res = await fetch(`${API_URL}/api/strategic-locations`);
  if (!res.ok) throw new Error("Failed to fetch Strategic Locations");
  return res.json();
}

export async function fetchTheaters(): Promise<string[]> {
  const res = await fetch(`${API_URL}/api/theaters`);
  if (!res.ok) throw new Error("Failed to fetch theaters");
  return res.json();
}

export async function fetchEvent(eventId: number): Promise<GeoEvent> {
  const res = await fetch(`${API_URL}/api/events/${eventId}`);
  if (!res.ok) throw new Error("Failed to fetch event");
  const data: GeoEvent = await res.json();
  return resolveGeoEvent(data);
}

export async function fetchEventLinks(eventId: number): Promise<EventLink[]> {
  const res = await fetch(`${API_URL}/api/events/${eventId}/links`);
  if (!res.ok) return [];
  return res.json();
}
