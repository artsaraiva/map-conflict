// API types matching backend schemas

export interface Article {
  id: number;
  url: string;
  title: string;
  source: string;
  feed: string | null;
  summary: string | null;
  published_at: string | null;
  image_url: string | null;
  video_url: string | null;
}

export interface GeoEvent {
  id: number;
  title: string;
  summary: string | null;
  event_type: EventType;
  severity: SeverityLevel;
  location_name: string;
  latitude: number;
  longitude: number;
  countries: string | null;
  created_at: string;
  confidence_score: number | null;
  source_count: number | null;
  theater: string | null;
  articles: Article[];
}

export interface RelatedEvent {
  id: number;
  title: string;
  event_type: EventType;
  severity: SeverityLevel;
  location_name: string;
  latitude: number;
  longitude: number;
  theater: string | null;
  confidence_score: number | null;
  created_at: string;
  relation_type: string;
  similarity_score: number | null;
}

export interface EventMapPoint {
  id: number;
  title: string;
  event_type: EventType;
  severity: SeverityLevel;
  latitude: number;
  longitude: number;
  location_name: string;
  article_count: number;
  image_url: string | null;
  sources: string[];
  created_at: string;
  confidence_score: number | null;
  source_count: number | null;
  theater: string | null;
}

export type EventType =
  | "conflict"
  | "naval_blockade"
  | "diplomatic_tension"
  | "sanctions"
  | "internal_unrest"
  | "military_movement"
  | "trade_dispute"
  | "humanitarian"
  | "other";

export type SeverityLevel = "low" | "medium" | "high" | "critical";

export type EventVisualFamily =
  | "conflict"
  | "strategic"
  | "diplomatic"
  | "economic"
  | "instability"
  | "humanitarian"
  | "neutral";

// Visual config for each event type
export const EVENT_TYPE_CONFIG: Record<
  EventType,
  {
    label: string;
    color: string;
    pulseColor: string;
    icon: string;
    family: EventVisualFamily;
  }
> = {
  conflict: {
    label: "Armed Conflict",
    color: "#ff5b4d",
    pulseColor: "rgba(255, 91, 77, 0.36)",
    icon: "crossed-swords",
    family: "conflict",
  },
  naval_blockade: {
    label: "Naval Pressure",
    color: "#6e8dff",
    pulseColor: "rgba(110, 141, 255, 0.34)",
    icon: "anchor",
    family: "strategic",
  },
  diplomatic_tension: {
    label: "Diplomatic Tension",
    color: "#75d1ff",
    pulseColor: "rgba(117, 209, 255, 0.32)",
    icon: "handshake",
    family: "diplomatic",
  },
  sanctions: {
    label: "Sanctions",
    color: "#f2b34f",
    pulseColor: "rgba(242, 179, 79, 0.34)",
    icon: "ban",
    family: "economic",
  },
  internal_unrest: {
    label: "Internal Unrest",
    color: "#d675ff",
    pulseColor: "rgba(214, 117, 255, 0.34)",
    icon: "megaphone",
    family: "instability",
  },
  military_movement: {
    label: "Military Movement",
    color: "#ff7c44",
    pulseColor: "rgba(255, 124, 68, 0.34)",
    icon: "tank",
    family: "strategic",
  },
  trade_dispute: {
    label: "Trade Dispute",
    color: "#ffcf6a",
    pulseColor: "rgba(255, 207, 106, 0.3)",
    icon: "chart",
    family: "economic",
  },
  humanitarian: {
    label: "Humanitarian",
    color: "#57d7a7",
    pulseColor: "rgba(87, 215, 167, 0.3)",
    icon: "heart",
    family: "humanitarian",
  },
  other: {
    label: "Other",
    color: "#8e97ab",
    pulseColor: "rgba(142, 151, 171, 0.28)",
    icon: "info",
    family: "neutral",
  },
};

// The one Severity table: rank orders Severity (higher is more severe) everywhere.
export const SEVERITY_CONFIG: Record<
  SeverityLevel,
  {
    label: string;
    rank: number;
    weight: number;
    opacity: number;
    briefingColor: string;
    size: number;
    pulseSize: number;
  }
> = {
  low: { label: "Low", rank: 0, weight: 0.34, opacity: 0.72, briefingColor: "#9cb0b5", size: 8, pulseSize: 20 },
  medium: { label: "Medium", rank: 1, weight: 0.58, opacity: 0.72, briefingColor: "#9cb0b5", size: 12, pulseSize: 30 },
  high: { label: "High", rank: 2, weight: 0.82, opacity: 0.9, briefingColor: "#ffcf7f", size: 16, pulseSize: 40 },
  critical: { label: "Critical", rank: 3, weight: 1, opacity: 1, briefingColor: "#ff5b4d", size: 22, pulseSize: 55 },
};

export const VISUAL_FAMILY_CONFIG: Record<
  EventVisualFamily,
  { label: string; color: string; description: string }
> = {
  conflict: {
    label: "Warzone",
    color: "#ff5b4d",
    description: "Active strikes, battles, bombardment",
  },
  strategic: {
    label: "Force Projection",
    color: "#ff9e5d",
    description: "Naval pressure and military movement",
  },
  diplomatic: {
    label: "Diplomatic Signal",
    color: "#75d1ff",
    description: "Talks, crises, and alliance moves",
  },
  economic: {
    label: "Economic Pressure",
    color: "#f2b34f",
    description: "Tariffs, sanctions, embargoes, trade tension",
  },
  instability: {
    label: "Domestic Unrest",
    color: "#d675ff",
    description: "Protests, coups, civil instability",
  },
  humanitarian: {
    label: "Humanitarian",
    color: "#57d7a7",
    description: "Aid, displacement, relief operations",
  },
  neutral: {
    label: "Other",
    color: "#8e97ab",
    description: "General geopolitical activity",
  },
};

// ─── Filter state ───

export interface MapBounds {
  minLng: number;
  minLat: number;
  maxLng: number;
  maxLat: number;
}

export interface MapFilters {
  eventTypes: EventType[];
  severities: SeverityLevel[];
  sinceHours: number;
  theaters: string[];
}

export const DEFAULT_FILTERS: MapFilters = {
  eventTypes: [],   // empty = show all
  severities: [],   // empty = show all
  sinceHours: 72,
  theaters: [],     // empty = show all
};

export const TIME_RANGE_OPTIONS: { label: string; value: number }[] = [
  { label: "6h", value: 6 },
  { label: "12h", value: 12 },
  { label: "24h", value: 24 },
  { label: "48h", value: 48 },
  { label: "72h", value: 72 },
  { label: "7d", value: 168 },
];

export const ALL_EVENT_TYPES: EventType[] = [
  "conflict",
  "military_movement",
  "naval_blockade",
  "diplomatic_tension",
  "sanctions",
  "internal_unrest",
  "trade_dispute",
  "humanitarian",
];

// Most severe first.
export const ALL_SEVERITIES = (Object.keys(SEVERITY_CONFIG) as SeverityLevel[]).sort(
  (a, b) => SEVERITY_CONFIG[b].rank - SEVERITY_CONFIG[a].rank,
);

export function getEventVisualFamily(eventType: EventType): EventVisualFamily {
  return EVENT_TYPE_CONFIG[eventType]?.family ?? "neutral";
}

export function getSeverityWeight(severity: SeverityLevel): number {
  return SEVERITY_CONFIG[severity]?.weight ?? SEVERITY_CONFIG.low.weight;
}

export function severityRank(severity: SeverityLevel): number {
  return SEVERITY_CONFIG[severity]?.rank ?? SEVERITY_CONFIG.low.rank;
}
