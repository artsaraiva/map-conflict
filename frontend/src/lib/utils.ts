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

// ─── Source utilities ───
// A Source key is its web address (docs/adr/0001-source-key-is-web-address.md),
// so Telegram channels are the keys under t.me/.

const SOURCE_LABELS: Record<string, string> = {
  "t.me/frontlinereportnews": "Frontline",
  "t.me/bellumactanews": "Bellum Acta",
  "t.me/rnintel": "RN Intel",
  "t.me/tglobaleye": "Global Eye",
  "t.me/tupireport": "Tupi Report",
  "t.me/disclosetv": "Disclose.tv",
};

/** Check if a Source key is a Telegram channel. For "did this Report arrive via Telegram", use `report.feed`. */
export function isTelegramChannel(source: string): boolean {
  return source.startsWith("t.me/");
}

/** Get display label for a Source — curated channels get nice names */
export function getSourceLabel(source: string): string {
  return SOURCE_LABELS[source] ?? source;
}

/** Get the Telegram channel URL for a Source, or null if not a Telegram channel */
export function getTelegramChannelUrl(source: string): string | null {
  return isTelegramChannel(source) ? `https://${source}` : null;
}
