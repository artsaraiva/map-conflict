/**
 * Utilities for detecting and embedding video/media content from URLs.
 * Supports YouTube, Vimeo, and Twitter/X embeds.
 */

export interface EmbedInfo {
  /** The embed-ready URL for an iframe */
  embedUrl: string;
  /** Platform name for display */
  platform: "youtube" | "vimeo" | "twitter";
  /** Recommended aspect ratio class */
  aspectRatio: string;
  /** iframe allow attributes */
  allow: string;
}

/**
 * Detect if a URL is an embeddable video and return embed info.
 * Returns null if the URL is not a recognized embeddable platform.
 */
export function getEmbedInfo(url: string): EmbedInfo | null {
  if (!url) return null;

  // ─── YouTube ───
  // Handles: youtube.com/watch?v=ID, youtu.be/ID, youtube.com/embed/ID
  const ytMatch = url.match(
    /(?:youtube\.com\/(?:watch\?v=|embed\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})/
  );
  if (ytMatch) {
    return {
      embedUrl: `https://www.youtube.com/embed/${ytMatch[1]}?rel=0&modestbranding=1`,
      platform: "youtube",
      aspectRatio: "aspect-video", // 16:9
      allow:
        "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture",
    };
  }

  // ─── Vimeo ───
  // Handles: vimeo.com/ID, player.vimeo.com/video/ID
  const vimeoMatch = url.match(
    /(?:vimeo\.com\/|player\.vimeo\.com\/video\/)(\d+)/
  );
  if (vimeoMatch) {
    return {
      embedUrl: `https://player.vimeo.com/video/${vimeoMatch[1]}?dnt=1`,
      platform: "vimeo",
      aspectRatio: "aspect-video",
      allow: "autoplay; fullscreen; picture-in-picture",
    };
  }

  // ─── Twitter/X ───
  // Handles: twitter.com/user/status/ID, x.com/user/status/ID
  const twitterMatch = url.match(
    /(?:twitter\.com|x\.com)\/\w+\/status\/(\d+)/
  );
  if (twitterMatch) {
    return {
      embedUrl: `https://platform.twitter.com/embed/Tweet.html?id=${twitterMatch[1]}&theme=dark`,
      platform: "twitter",
      aspectRatio: "aspect-[4/5]", // tweets are taller
      allow: "",
    };
  }

  return null;
}

/**
 * Check if a URL points to a recognized embeddable platform.
 */
export function isEmbeddable(url: string): boolean {
  return getEmbedInfo(url) !== null;
}

/**
 * Check if a URL is a Telegram post link.
 */
export function isTelegramLink(url: string): boolean {
  return /^https?:\/\/t\.me\//i.test(url);
}

/**
 * Check if a video URL points to a locally-served video file (downloaded .mp4).
 * These are served from /media/telegram/*.mp4 via the backend's StaticFiles mount.
 */
export function isLocalVideo(url: string): boolean {
  if (!url) return false;
  // Matches both relative paths (/media/telegram/...) and full backend URLs
  return /\/media\/telegram\/[^/]+\.mp4(\?|$)/i.test(url);
}

/**
 * Get a platform display label for a video URL.
 * Returns a label even for non-embeddable platforms (e.g. Telegram).
 */
export function getVideoPlatformLabel(url: string): string | null {
  if (!url) return null;

  const info = getEmbedInfo(url);
  if (info) {
    switch (info.platform) {
      case "youtube":
        return "YouTube";
      case "vimeo":
        return "Vimeo";
      case "twitter":
        return "X / Twitter";
    }
  }

  if (isTelegramLink(url)) return "Telegram";
  if (isLocalVideo(url)) return "Telegram";

  return null;
}
