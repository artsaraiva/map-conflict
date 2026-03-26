/**
 * Shared utility functions used across frontend components.
 */

/** Format a date string as a relative "X ago" string */
export function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();

  if (diffMs < 0) return "just now";

  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;

  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;

  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 7) return `${diffDays}d ago`;

  const diffWeeks = Math.floor(diffDays / 7);
  return `${diffWeeks}w ago`;
}

// ─── Telegram source utilities ───

const TELEGRAM_SOURCES: Record<string, { label: string; channel: string }> = {
  "tg-frontline": { label: "Frontline", channel: "FrontlineReportNews" },
  "tg-bellumacta": { label: "Bellum Acta", channel: "BellumActaNews" },
  "tg-rnintel": { label: "RN Intel", channel: "rnintel" },
  "tg-globaleye": { label: "Global Eye", channel: "tglobaleye" },
  "tg-tupireport": { label: "Tupi Report", channel: "tupireport" },
  "tg-disclosetv": { label: "Disclose.tv", channel: "disclosetv" },
};

/** Check if a source slug is a Telegram source */
export function isTelegramSource(source: string): boolean {
  return source.startsWith("tg-");
}

/** Get display label for a source — Telegram channels get nice names */
export function getSourceLabel(source: string): string {
  return TELEGRAM_SOURCES[source]?.label ?? source;
}

/** Get the Telegram channel URL for a source, or null if not a Telegram source */
export function getTelegramChannelUrl(source: string): string | null {
  const tg = TELEGRAM_SOURCES[source];
  return tg ? `https://t.me/${tg.channel}` : null;
}
