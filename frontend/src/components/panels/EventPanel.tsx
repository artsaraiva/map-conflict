"use client";

import { GeoEvent, Article, RelatedEvent, EVENT_TYPE_CONFIG, SEVERITY_CONFIG } from "@/lib/types";
import { fetchRelatedEvents } from "@/lib/api";
import { formatTimeAgo, isTelegramChannel, getSourceLabel, getTelegramChannelUrl } from "@/lib/utils";
import { getEmbedInfo, getVideoPlatformLabel, isTelegramLink, isLocalVideo } from "@/lib/media-utils";
import clsx from "clsx";
import { useState, useMemo, useEffect } from "react";

interface EventPanelProps {
  event: GeoEvent | null;
  isLoading: boolean;
  onClose: () => void;
  onEventSelect?: (eventId: number) => void;
}

// ── Article grouping utilities (Jaccard title similarity) ──────────────────

/** Tokenize a title into lowercase words, stripping punctuation */
function tokenize(text: string): Set<string> {
  const cleaned = text.replace(/[^\w\s]/g, " ").toLowerCase();
  return new Set(cleaned.split(/\s+/).filter((t) => t.length > 1));
}

/** Jaccard similarity between two strings, based on word tokens */
function titleSimilarity(a: string, b: string): number {
  const tokensA = tokenize(a);
  const tokensB = tokenize(b);
  if (tokensA.size === 0 || tokensB.size === 0) return 0;

  let intersection = 0;
  for (const t of tokensA) {
    if (tokensB.has(t)) intersection++;
  }
  const union = tokensA.size + tokensB.size - intersection;
  return union === 0 ? 0 : intersection / union;
}

interface ArticleGroup {
  /** Representative article (first added to the group) */
  primary: Article;
  /** All articles in this group (including primary) */
  articles: Article[];
  /** Unique sources across all articles in the group */
  sources: string[];
  /** All unique image URLs across articles */
  images: string[];
  /** Best video URL (prefer local, then embed, then link) */
  videoUrl: string | null;
}

const TITLE_GROUP_THRESHOLD = 0.7;

/** Group articles with >70% title similarity into clusters */
function groupSimilarArticles(articles: Article[]): ArticleGroup[] {
  const groups: ArticleGroup[] = [];

  for (const article of articles) {
    let merged = false;

    for (const group of groups) {
      // Compare against the primary article's title
      if (titleSimilarity(article.title, group.primary.title) >= TITLE_GROUP_THRESHOLD) {
        group.articles.push(article);
        if (article.source && !group.sources.includes(article.source)) {
          group.sources.push(article.source);
        }
        if (article.image_url && !group.images.includes(article.image_url)) {
          group.images.push(article.image_url);
        }
        // Prefer local video > embeddable > telegram link
        if (article.video_url) {
          if (!group.videoUrl || (isLocalVideo(article.video_url) && !isLocalVideo(group.videoUrl))) {
            group.videoUrl = article.video_url;
          }
        }
        merged = true;
        break;
      }
    }

    if (!merged) {
      groups.push({
        primary: article,
        articles: [article],
        sources: [article.source],
        images: article.image_url ? [article.image_url] : [],
        videoUrl: article.video_url || null,
      });
    }
  }

  return groups;
}

/** Telegram paper-plane icon */
function TelegramIcon({ size = 12, className = "" }: { size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M9.78 18.65l.28-4.23 7.68-6.92c.34-.31-.07-.46-.52-.19L7.74 13.3 3.64 12c-.88-.25-.89-.86.2-1.3l15.97-6.16c.73-.33 1.43.18 1.15 1.3l-2.72 12.81c-.19.91-.74 1.13-1.5.71L12.6 16.3l-1.99 1.93c-.23.23-.42.42-.83.42z" />
    </svg>
  );
}

/** Source badge — Telegram sources get a distinct look */
function SourceBadge({ source }: { source: string }) {
  const isTg = isTelegramChannel(source);
  const label = getSourceLabel(source);
  const channelUrl = getTelegramChannelUrl(source);

  const inner = (
    <span
      className={clsx(
        "inline-flex items-center gap-1 font-medium uppercase tracking-[0.18em]",
        isTg ? "text-[#29a9eb]" : "text-[#a8b6bb]"
      )}
    >
      {isTg && <TelegramIcon size={11} />}
      {label}
    </span>
  );

  if (channelUrl) {
    return (
      <a
        href={channelUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="hover:brightness-125 transition-all"
      >
        {inner}
      </a>
    );
  }
  return inner;
}

/** Full-width hero image with gradient overlay */
function HeroImage({ src, alt }: { src: string; alt: string }) {
  const [error, setError] = useState(false);
  if (error) return null;

  return (
    <div className="relative w-full overflow-hidden rounded-xl border border-[#263740]">
      <img
        src={src}
        alt={alt}
        className="h-48 w-full object-cover"
        onError={() => setError(true)}
        loading="lazy"
      />
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-[#0a1218]/70 via-transparent to-[#0a1218]/20" />
    </div>
  );
}

/** Embeddable video iframe */
function VideoEmbed({ url }: { url: string }) {
  const info = getEmbedInfo(url);
  if (!info) return null;

  return (
    <div className={clsx("w-full overflow-hidden rounded-xl border border-[#263740]", info.aspectRatio)}>
      <iframe
        src={info.embedUrl}
        className="h-full w-full"
        allow={info.allow}
        allowFullScreen
        loading="lazy"
        title="Embedded video"
      />
    </div>
  );
}

/** Inline video player for locally-downloaded Telegram videos */
function TelegramVideo({ src, poster }: { src: string; poster?: string }) {
  return (
    <div className="relative w-full overflow-hidden rounded-xl border border-[#263740] bg-[#0a1218]">
      <video
        src={src}
        poster={poster}
        controls
        preload="metadata"
        className="h-auto max-h-72 w-full object-contain"
        playsInline
      />
      {/* Telegram badge overlay */}
      <div className="absolute top-2 right-2 flex items-center gap-1 rounded-md bg-[#0a1218]/80 px-1.5 py-0.5 backdrop-blur-sm pointer-events-none">
        <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor" className="text-[#29a9eb]">
          <path d="M9.78 18.65l.28-4.23 7.68-6.92c.34-.31-.07-.46-.52-.19L7.74 13.3 3.64 12c-.88-.25-.89-.86.2-1.3l15.97-6.16c.73-.33 1.43.18 1.15 1.3l-2.72 12.81c-.19.91-.74 1.13-1.5.71L12.6 16.3l-1.99 1.93c-.23.23-.42.42-.83.42z" />
        </svg>
        <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor" className="text-[#29a9eb]/70">
          <polygon points="5 3 19 12 5 21 5 3" />
        </svg>
        <span className="text-[9px] uppercase tracking-wider text-[#29a9eb]">Video</span>
      </div>
    </div>
  );
}

/** Horizontal media gallery strip for events with multiple images */
function MediaGallery({ articles, onImageError }: { articles: Article[]; onImageError: (id: number) => void }) {
  const mediaArticles = articles.filter((a) => a.image_url);
  if (mediaArticles.length < 2) return null;

  return (
    <div>
      <h3 className="mb-2 text-[11px] font-medium uppercase tracking-[0.24em] text-[#86a1aa]">
        Media ({mediaArticles.length})
      </h3>
      <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
        {mediaArticles.map((article) => (
          <a
            key={article.id}
            href={article.url}
            target="_blank"
            rel="noopener noreferrer"
            className="group relative flex-shrink-0 overflow-hidden rounded-lg border border-[#263740] transition-all hover:border-[#42525a]"
          >
            <img
              src={article.image_url!}
              alt={article.title}
              className="h-20 w-28 object-cover transition-transform group-hover:scale-105"
              onError={() => onImageError(article.id)}
              loading="lazy"
            />
            <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-[#0a1218]/50 to-transparent" />
            <div className="absolute bottom-0 left-0 right-0 p-1">
              <span className={clsx(
                "text-[9px] uppercase tracking-wider line-clamp-1",
                article.feed === "telegram" ? "text-[#29a9eb]" : "text-[#c8d4d6]"
              )}>
                {article.feed === "telegram" && "TG "}{getSourceLabel(article.source)}
              </span>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}

/** Article card with large image and optional video embed */
function ArticleCard({ article }: { article: Article }) {
  const [imgError, setImgError] = useState(false);
  const hasLocalVideo = article.video_url ? isLocalVideo(article.video_url) : false;
  const videoEmbed = article.video_url && !hasLocalVideo ? getEmbedInfo(article.video_url) : null;
  const videoPlatform = article.video_url ? getVideoPlatformLabel(article.video_url) : null;

  return (
    <div className="group rounded-2xl border border-[#263740] bg-[#111a21]/76 overflow-hidden transition-all hover:border-[#42525a] hover:bg-[#15222a]">
      {/* Local video player — takes priority over image when present */}
      {hasLocalVideo && (
        <TelegramVideo
          src={article.video_url!}
          poster={article.image_url || undefined}
        />
      )}

      {/* Article image — show only when no local video */}
      {!hasLocalVideo && article.image_url && !imgError && (
        <div className="relative overflow-hidden">
          <img
            src={article.image_url}
            alt=""
            className="h-36 w-full object-cover transition-transform group-hover:scale-[1.02]"
            onError={() => setImgError(true)}
            loading="lazy"
          />
          <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-[#111a21]/50 to-transparent" />
          {/* Video badge overlay */}
          {videoPlatform && (
            <div className="absolute top-2 right-2 flex items-center gap-1 rounded-md bg-[#0a1218]/80 px-1.5 py-0.5 backdrop-blur-sm">
              <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor" className="text-[#ff5b4d]">
                <polygon points="5 3 19 12 5 21 5 3" />
              </svg>
              <span className="text-[9px] uppercase tracking-wider text-[#c8d4d6]">
                {videoPlatform}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Video embed (if embeddable URL, no image, and no local video) */}
      {videoEmbed && !article.image_url && !hasLocalVideo && (
        <VideoEmbed url={article.video_url!} />
      )}

      {/* Telegram video link (not embeddable, not local — show external link) */}
      {!videoEmbed && !hasLocalVideo && article.video_url && isTelegramLink(article.video_url) && (
        <a
          href={article.video_url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 mx-3 mt-2 px-3 py-2 rounded-lg border border-[#29a9eb]/30 bg-[#29a9eb]/8 text-[#29a9eb] hover:bg-[#29a9eb]/15 transition-all"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
            <path d="M9.78 18.65l.28-4.23 7.68-6.92c.34-.31-.07-.46-.52-.19L7.74 13.3 3.64 12c-.88-.25-.89-.86.2-1.3l15.97-6.16c.73-.33 1.43.18 1.15 1.3l-2.72 12.81c-.19.91-.74 1.13-1.5.71L12.6 16.3l-1.99 1.93c-.23.23-.42.42-.83.42z" />
          </svg>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" className="text-[#29a9eb]/70">
            <polygon points="5 3 19 12 5 21 5 3" />
          </svg>
          <span className="text-[11px] uppercase tracking-wider font-medium">Watch on Telegram</span>
        </a>
      )}

      <a
        href={article.url}
        target="_blank"
        rel="noopener noreferrer"
        className="block p-3"
      >
        <div className="text-sm font-medium leading-snug text-[#ecede6] transition-colors group-hover:text-[#75d1ff]">
          {article.title}
        </div>
        <div className="mt-2 flex items-center gap-2 text-xs text-[#788b91]">
          <SourceBadge source={article.source} />
          {article.published_at && (
            <>
              <span>|</span>
              <span>{formatTimeAgo(article.published_at)}</span>
            </>
          )}
          {videoPlatform && !article.image_url && (
            <>
              <span>|</span>
              <span className="flex items-center gap-1 text-[#ff8d80]">
                <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor">
                  <polygon points="5 3 19 12 5 21 5 3" />
                </svg>
                {videoPlatform}
              </span>
            </>
          )}
        </div>
        {article.summary && (
          <p className="mt-2 line-clamp-3 text-xs leading-relaxed text-[#7b8f95]">
            {article.summary}
          </p>
        )}
      </a>

      {/* Inline video embed below content for articles WITH images */}
      {videoEmbed && article.image_url && !hasLocalVideo && (
        <div className="px-3 pb-3">
          <VideoEmbed url={article.video_url!} />
        </div>
      )}

      {/* Telegram video link below content for articles WITH images (no local video) */}
      {!videoEmbed && !hasLocalVideo && article.video_url && isTelegramLink(article.video_url) && article.image_url && (
        <div className="px-3 pb-3">
          <a
            href={article.video_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 px-3 py-2 rounded-lg border border-[#29a9eb]/30 bg-[#29a9eb]/8 text-[#29a9eb] hover:bg-[#29a9eb]/15 transition-all"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
              <path d="M9.78 18.65l.28-4.23 7.68-6.92c.34-.31-.07-.46-.52-.19L7.74 13.3 3.64 12c-.88-.25-.89-.86.2-1.3l15.97-6.16c.73-.33 1.43.18 1.15 1.3l-2.72 12.81c-.19.91-.74 1.13-1.5.71L12.6 16.3l-1.99 1.93c-.23.23-.42.42-.83.42z" />
            </svg>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" className="text-[#29a9eb]/70">
              <polygon points="5 3 19 12 5 21 5 3" />
            </svg>
            <span className="text-[11px] uppercase tracking-wider font-medium">Watch on Telegram</span>
          </a>
        </div>
      )}
    </div>
  );
}

/** Grouped article card — combines near-duplicate articles from multiple sources */
function GroupedArticleCard({ group, heroImageUrl }: { group: ArticleGroup; heroImageUrl?: string }) {
  const [imgError, setImgError] = useState(false);
  const article = group.primary;
  const hasLocalVid = group.videoUrl ? isLocalVideo(group.videoUrl) : false;
  const videoEmbed = group.videoUrl && !hasLocalVid ? getEmbedInfo(group.videoUrl) : null;
  const cardImg = group.images[0] || null;
  // Skip the card image if it's the same as the hero image already shown above
  const showCardImage = cardImg && cardImg !== heroImageUrl;

  return (
    <div className="group rounded-2xl border border-[#263740] bg-[#111a21]/76 overflow-hidden transition-all hover:border-[#42525a] hover:bg-[#15222a]">
      {/* Local video player — only if different from hero */}
      {hasLocalVid && (
        <TelegramVideo
          src={group.videoUrl!}
          poster={cardImg || undefined}
        />
      )}

      {/* Image — only when different from hero */}
      {!hasLocalVid && showCardImage && !imgError && (
        <div className="relative overflow-hidden">
          <img
            src={cardImg!}
            alt=""
            className="h-36 w-full object-cover transition-transform group-hover:scale-[1.02]"
            onError={() => setImgError(true)}
            loading="lazy"
          />
          <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-[#111a21]/50 to-transparent" />
        </div>
      )}

      {/* Video embed (non-local, no card image) */}
      {videoEmbed && !showCardImage && !hasLocalVid && (
        <VideoEmbed url={group.videoUrl!} />
      )}

      <div className="p-3 flex items-center gap-3">
        {/* Source badges + timestamp */}
        <div className="flex-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-[#788b91]">
          {group.sources.map((source, i) => (
            <span key={source} className="flex items-center gap-1">
              {i > 0 && <span className="text-[#3a4a52]">/</span>}
              <SourceBadge source={source} />
            </span>
          ))}
          {article.published_at && (
            <>
              <span className="text-[#3a4a52]">|</span>
              <span>{formatTimeAgo(article.published_at)}</span>
            </>
          )}
        </div>

        {/* Link to original post */}
        <a
          href={article.url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex-shrink-0 rounded-lg p-1.5 text-[#5d7078] hover:text-[#86a1aa] hover:bg-[#1e2b31] transition-all"
          title="Open original post"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
            <polyline points="15 3 21 3 21 9" />
            <line x1="10" y1="14" x2="21" y2="3" />
          </svg>
        </a>
      </div>

      {/* Additional source links when grouped */}
      {group.articles.length > 1 && (
        <div className="px-3 pb-3 flex flex-wrap gap-1.5">
          {group.articles.slice(1).map((a) => (
            <a
              key={a.id}
              href={a.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-[10px] uppercase tracking-wider text-[#5d7078] hover:text-[#86a1aa] transition-colors"
            >
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                <polyline points="15 3 21 3 21 9" />
                <line x1="10" y1="14" x2="21" y2="3" />
              </svg>
              {getSourceLabel(a.source)}
            </a>
          ))}
        </div>
      )}

      {/* Inline video embed below for cards with unique images */}
      {videoEmbed && showCardImage && !hasLocalVid && (
        <div className="px-3 pb-3">
          <VideoEmbed url={group.videoUrl!} />
        </div>
      )}
    </div>
  );
}

export default function EventPanel({
  event,
  isLoading,
  onClose,
  onEventSelect,
}: EventPanelProps) {
  const [galleryErrors, setGalleryErrors] = useState<Set<number>>(new Set());
  const [relatedEvents, setRelatedEvents] = useState<RelatedEvent[]>([]);

  // Group similar articles for deduped display — must be before early return
  const articleGroups = useMemo(
    () => (event?.articles ? groupSimilarArticles(event.articles) : []),
    [event?.articles]
  );

  // Fetch related events whenever the selected event changes
  useEffect(() => {
    if (!event) {
      setRelatedEvents([]);
      return;
    }
    fetchRelatedEvents(event.id).then(setRelatedEvents).catch(() => setRelatedEvents([]));
  }, [event?.id]);

  if (!event && !isLoading) return null;

  const typeConfig = event ? EVENT_TYPE_CONFIG[event.event_type] : null;
  const severityConfig = event ? SEVERITY_CONFIG[event.severity] : null;

  // Find the first article with an image to use as the event's hero image
  const heroImage = event?.articles?.find((a) => a.image_url)?.image_url;
  // Check if any article has an embeddable video for hero treatment
  const heroVideo = event?.articles?.find(
    (a) => a.video_url && getEmbedInfo(a.video_url)
  );
  // Check if any article has a locally-downloaded video for hero treatment
  const heroLocalVideo = event?.articles?.find(
    (a) => a.video_url && isLocalVideo(a.video_url)
  );

  // Filter gallery articles (remove ones with broken images)
  const galleryArticles =
    event?.articles?.filter((a) => a.image_url && !galleryErrors.has(a.id)) ?? [];

  const handleGalleryImageError = (articleId: number) => {
    setGalleryErrors((prev) => new Set(prev).add(articleId));
  };

  return (
    <div className="absolute top-0 right-0 z-50 h-full w-[420px] overflow-y-auto border-l border-[#314149]/75 bg-[linear-gradient(180deg,rgba(8,15,20,0.96),rgba(8,14,18,0.86))] shadow-2xl backdrop-blur-md">
      <div className="sticky top-0 border-b border-[#2a3a42] bg-[linear-gradient(180deg,rgba(8,15,20,0.96),rgba(8,15,20,0.9))] p-4 backdrop-blur-md">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            {isLoading ? (
              <div className="h-6 w-48 rounded bg-[#34444b] animate-pulse" />
            ) : (
              <>
                <div className="mb-1 text-[10px] uppercase tracking-[0.34em] text-[#7f9ba2]">
                  Incident Brief
                </div>
                <h2 className="text-lg font-semibold leading-tight text-[#f2ece0]">
                  {event?.title}
                </h2>
              </>
            )}
          </div>
          <button
            onClick={onClose}
            className="flex-shrink-0 rounded-lg p-1.5 text-[#88989d] transition-colors hover:bg-[#1e2b31] hover:text-[#f0eadb]"
            aria-label="Close panel"
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>

        {event && typeConfig && severityConfig && (
          <div className="mt-3 flex items-center gap-2">
            <span
              className="rounded-full px-2.5 py-1 text-xs font-medium"
              style={{
                backgroundColor: `${typeConfig.color}1a`,
                color: typeConfig.color,
                border: `1px solid ${typeConfig.color}55`,
              }}
            >
              {typeConfig.label}
            </span>
            <span
              className={clsx(
                "rounded-full px-2.5 py-1 text-xs font-medium",
                event.severity === "critical" &&
                  "border border-[#8b433d] bg-[#321816] text-[#ff8d80]",
                event.severity === "high" &&
                  "border border-[#85603a] bg-[#312314] text-[#ffca7f]",
                event.severity === "medium" &&
                  "border border-[#49646b] bg-[#17242b] text-[#9fc1cb]",
                event.severity === "low" &&
                  "border border-[#39645a] bg-[#13241e] text-[#8ed7bb]"
              )}
            >
              {severityConfig.label} Severity
            </span>
          </div>
        )}
      </div>

      <div className="space-y-5 p-4">
        {isLoading ? (
          <div className="space-y-3">
            <div className="h-44 w-full rounded-xl bg-[#34444b] animate-pulse" />
            <div className="h-4 w-full rounded bg-[#34444b] animate-pulse" />
            <div className="h-4 w-3/4 rounded bg-[#34444b] animate-pulse" />
            <div className="h-4 w-5/6 rounded bg-[#34444b] animate-pulse" />
          </div>
        ) : event ? (
          <>
            {/* ─── Hero media: local video > video embed > image ─── */}
            {heroLocalVideo ? (
              <div className="space-y-2">
                <TelegramVideo
                  src={heroLocalVideo.video_url!}
                  poster={heroLocalVideo.image_url || heroImage || undefined}
                />
                <div className="text-[10px] uppercase tracking-wider text-[#5d7078]">
                  Via <span className={heroLocalVideo.feed === "telegram" ? "text-[#29a9eb]" : ""}>
                    {getSourceLabel(heroLocalVideo.source)}
                  </span>
                </div>
              </div>
            ) : heroVideo ? (
              <div className="space-y-2">
                <VideoEmbed url={heroVideo.video_url!} />
              <div className="text-[10px] uppercase tracking-wider text-[#5d7078]">
                  Via <span className={heroVideo.feed === "telegram" ? "text-[#29a9eb]" : ""}>
                    {getSourceLabel(heroVideo.source)}
                  </span>
                </div>
              </div>
            ) : heroImage ? (
              <HeroImage src={heroImage} alt={event.title} />
            ) : null}

            <div className="flex items-center gap-4 text-sm text-[#9ab0b4]">
              <div className="flex items-center gap-1.5">
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
                  <circle cx="12" cy="10" r="3" />
                </svg>
                {event.location_name}
              </div>
              {event.countries && (
                <div className="flex items-center gap-1.5">
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                  >
                    <circle cx="12" cy="12" r="10" />
                    <path d="M2 12h20M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
                  </svg>
                  {event.countries}
                </div>
              )}
            </div>

            {event.summary && (
              <div className="rounded-2xl border border-[#273840] bg-[#0f1820]/85 p-4">
                <h3 className="mb-2 text-[11px] font-medium uppercase tracking-[0.24em] text-[#86a1aa]">
                  Situation Summary
                </h3>
                <p className="text-sm leading-relaxed text-[#d3dddc]">
                  {event.summary}
                </p>
              </div>
            )}

            <div className="text-xs text-[#6f858a]">
              {event.latitude.toFixed(4)}, {event.longitude.toFixed(4)}
            </div>

            {/* ─── Media gallery strip ─── */}
            {galleryArticles.length >= 2 && (
              <MediaGallery
                articles={galleryArticles}
                onImageError={handleGalleryImageError}
              />
            )}

            {/* ─── Sources / grouped article cards ─── */}
            {event.articles && event.articles.length > 0 && (
              <div>
                <h3 className="mb-3 text-[11px] font-medium uppercase tracking-[0.24em] text-[#86a1aa]">
                  Sources ({event.articles.length})
                  {articleGroups.length < event.articles.length && (
                    <span className="ml-1 text-[#5d7078]">
                      &middot; {articleGroups.length} {articleGroups.length === 1 ? "story" : "stories"}
                    </span>
                  )}
                </h3>
                <div className="space-y-3">
                  {articleGroups.map((group) => (
                    <GroupedArticleCard key={group.primary.id} group={group} heroImageUrl={heroImage || undefined} />
                  ))}
                </div>
              </div>
            )}

            {/* ─── Related events ─── */}
            {relatedEvents.length > 0 && (
              <div>
                <h3 className="mb-2 text-[11px] font-medium uppercase tracking-[0.24em] text-[#86a1aa]">
                  Related Events ({relatedEvents.length})
                </h3>
                <div className="space-y-1.5">
                  {relatedEvents.map((rel) => {
                    const tc = EVENT_TYPE_CONFIG[rel.event_type];
                    return (
                      <button
                        key={rel.id}
                        onClick={() => onEventSelect?.(rel.id)}
                        className="w-full rounded-xl border border-[#263740] bg-[#0f1820]/70 px-3 py-2.5 text-left transition-all hover:border-[#3a5260] hover:bg-[#14202a]"
                      >
                        <div className="flex items-start gap-2.5">
                          <div
                            className="mt-1 h-2 w-2 flex-shrink-0 rounded-full"
                            style={{ backgroundColor: tc?.color ?? "#8e97ab" }}
                          />
                          <div className="flex-1 min-w-0">
                            <div className="line-clamp-2 text-[13px] font-medium leading-snug text-[#dde4e0]">
                              {rel.title}
                            </div>
                            <div className="mt-1 flex items-center gap-2 text-[11px] text-[#6a7e84]">
                              <span style={{ color: tc?.color ?? "#8e97ab" }}>{tc?.label ?? rel.event_type}</span>
                              <span>·</span>
                              <span>{rel.location_name}</span>
                              {rel.theater && (
                                <>
                                  <span>·</span>
                                  <span className="text-[#4d6068]">{rel.theater}</span>
                                </>
                              )}
                              {rel.similarity_score != null && (
                                <>
                                  <span>·</span>
                                  <span className="text-[#4d6068]">{Math.round(rel.similarity_score * 100)}% match</span>
                                </>
                              )}
                            </div>
                          </div>
                          <span className="flex-shrink-0 text-[10px] text-[#4d6068]">
                            {formatTimeAgo(rel.created_at)}
                          </span>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            <div className="border-t border-[#203039] pt-2 text-xs text-[#6d8187]">
              Event tracked since{" "}
              {new Date(event.created_at).toLocaleDateString("en-US", {
                month: "long",
                day: "numeric",
                year: "numeric",
                hour: "2-digit",
                minute: "2-digit",
              })}
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}
