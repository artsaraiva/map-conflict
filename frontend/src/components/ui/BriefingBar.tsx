"use client";

import { useMemo } from "react";
import {
  EventMapPoint,
  EVENT_TYPE_CONFIG,
  SEVERITY_CONFIG,
} from "@/lib/types";

interface NewsTicker {
  events: EventMapPoint[];
}

export default function BriefingBar({ events }: NewsTicker) {
  const tickerItems = useMemo(() => {
    // Sort by created_at descending, take top 20
    const sorted = [...events]
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      .slice(0, 20);

    return sorted.map((event) => {
      const typeConfig = EVENT_TYPE_CONFIG[event.event_type];
      const severityConfig = SEVERITY_CONFIG[event.severity];
      return {
        id: event.id,
        severity: severityConfig?.label?.toUpperCase() ?? "MEDIUM",
        severityRaw: event.severity,
        location: event.location_name,
        title: event.title,
        color: typeConfig?.color ?? "#8e97ab",
      };
    });
  }, [events]);

  if (tickerItems.length === 0) return null;

  // Build the scrolling text — duplicated for seamless loop
  const tickerContent = tickerItems
    .map(
      (item) =>
        `<span class="ticker-severity" style="color:${
          item.severityRaw === "critical"
            ? "#ff5b4d"
            : item.severityRaw === "high"
            ? "#ffcf7f"
            : "#9cb0b5"
        }">${item.severity}</span> <span class="ticker-location">${item.location}</span> <span class="ticker-dash">&mdash;</span> <span class="ticker-title">${item.title}</span>`
    )
    .join('<span class="ticker-bullet">&bull;</span>');

  return (
    <section className="absolute bottom-0 left-0 right-0 z-40">
      <div className="news-ticker-bar">
        {/* Live indicator */}
        <div className="news-ticker-label">
          <span className="news-ticker-dot" />
          <span>LIVE</span>
        </div>

        {/* Scrolling ticker */}
        <div className="news-ticker-track">
          <div
            className="news-ticker-scroll"
            dangerouslySetInnerHTML={{
              __html: tickerContent + '<span class="ticker-bullet">&bull;</span>' + tickerContent,
            }}
          />
        </div>
      </div>
    </section>
  );
}
