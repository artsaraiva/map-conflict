"use client";

import React, { useState } from "react";
import {
  EventMapPoint,
  EventType,
  SeverityLevel,
  MapFilters,
  DEFAULT_FILTERS,
  EVENT_TYPE_CONFIG,
  SEVERITY_CONFIG,
  TIME_RANGE_OPTIONS,
  ALL_EVENT_TYPES,
  ALL_SEVERITIES,
} from "@/lib/types";
import { formatTimeAgo, isTelegramSource, getSourceLabel } from "@/lib/utils";
import clsx from "clsx";

/** Thumbnail image with error handling — hides itself on load failure */
function EventThumbnail({ src, alt }: { src: string; alt: string }) {
  const [error, setError] = useState(false);
  if (error) return null;

  return (
    <div className="relative w-full overflow-hidden rounded-lg border border-[#263740]">
      <img
        src={src}
        alt={alt}
        className="h-[120px] w-full object-cover"
        onError={() => setError(true)}
        loading="lazy"
      />
      {/* Gradient overlay for readability */}
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-[#0a1218]/60 to-transparent" />
    </div>
  );
}

interface EventListProps {
  events: EventMapPoint[];
  selectedEventId: number | null;
  onEventSelect: (eventId: number) => void;
  isOpen: boolean;
  onToggle: () => void;
  filters: MapFilters;
  onFiltersChange: (filters: MapFilters) => void;
}

function hasActiveFilters(filters: MapFilters): boolean {
  return (
    filters.eventTypes.length > 0 ||
    filters.severities.length > 0 ||
    filters.sinceHours !== DEFAULT_FILTERS.sinceHours
  );
}

function toggleInArray<T>(arr: T[], item: T): T[] {
  return arr.includes(item) ? arr.filter((x) => x !== item) : [...arr, item];
}

export default function EventList({
  events,
  selectedEventId,
  onEventSelect,
  isOpen,
  onToggle,
  filters,
  onFiltersChange,
}: EventListProps) {
  const [isFilterOpen, setIsFilterOpen] = useState(false);

  // Sort by severity (critical first) then by date
  const sortedEvents = [...events].sort((a, b) => {
    const severityOrder = { critical: 0, high: 1, medium: 2, low: 3 };
    const aSev = severityOrder[a.severity] ?? 4;
    const bSev = severityOrder[b.severity] ?? 4;
    if (aSev !== bSev) return aSev - bSev;
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });

  const toggleEventType = (type: EventType) => {
    onFiltersChange({
      ...filters,
      eventTypes: toggleInArray(filters.eventTypes, type),
    });
  };

  const toggleSeverity = (sev: SeverityLevel) => {
    onFiltersChange({
      ...filters,
      severities: toggleInArray(filters.severities, sev),
    });
  };

  const setSinceHours = (hours: number) => {
    onFiltersChange({ ...filters, sinceHours: hours });
  };

  const clearFilters = () => {
    onFiltersChange(DEFAULT_FILTERS);
  };

  const filtersActive = hasActiveFilters(filters);

  return (
    <>
      <button
        onClick={onToggle}
        className={clsx(
          "absolute top-[92px] z-40 rounded-xl border border-[#3a4b52] bg-[#111920]/92 p-2.5 text-[#aab7bb] backdrop-blur-md transition-all hover:border-[#5c6970] hover:text-[#eef1e9]",
          isOpen ? "left-[346px]" : "left-4"
        )}
        aria-label={isOpen ? "Close event list" : "Open event list"}
      >
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          {isOpen ? (
            <path d="M15 18l-6-6 6-6" />
          ) : (
            <>
              <path d="M4 6h16M4 12h16M4 18h16" />
            </>
          )}
        </svg>
      </button>

      <div
        className={clsx(
          "absolute top-16 left-0 bottom-0 z-30 flex w-[336px] flex-col overflow-hidden border-r border-[#314149]/70 bg-[linear-gradient(180deg,rgba(8,15,20,0.96),rgba(10,16,20,0.88))] backdrop-blur-md",
          "transform transition-transform duration-300 ease-out",
          isOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {/* ─── Header ─── */}
        <div className="border-b border-[#283840] px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-[10px] uppercase tracking-[0.32em] text-[#7f9aa3]">
                Event Feed
              </div>
              <h2 className="mt-1 text-sm font-semibold uppercase tracking-[0.18em] text-[#f0eadb]">
                Active Theaters
              </h2>
            </div>
            <div className="flex items-center gap-2">
              {filtersActive && (
                <button
                  onClick={clearFilters}
                  className="text-[10px] uppercase tracking-wider text-[#ff9e5d] hover:text-[#ffb97e] transition-colors"
                >
                  Clear
                </button>
              )}
              <button
                onClick={() => setIsFilterOpen(!isFilterOpen)}
                className={clsx(
                  "rounded-lg border p-1.5 transition-all",
                  isFilterOpen || filtersActive
                    ? "border-[#5a7a88] bg-[#1a2830] text-[#a8d0dd]"
                    : "border-[#35444b] bg-[#121c22] text-[#94a6aa] hover:border-[#4a5c64] hover:text-[#c8d4d6]"
                )}
                aria-label="Toggle filters"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
                </svg>
              </button>
              <span className="rounded-full border border-[#35444b] bg-[#121c22] px-2.5 py-1 text-[11px] text-[#94a6aa]">
                {events.length}
              </span>
            </div>
          </div>
        </div>

        {/* ─── Filter Panel (collapsible) ─── */}
        <div
          className={clsx(
            "overflow-hidden border-b border-[#283840] transition-all duration-300 ease-out",
            isFilterOpen ? "max-h-[400px] opacity-100" : "max-h-0 opacity-0"
          )}
        >
          <div className="px-4 py-3 space-y-3">
            {/* Time range */}
            <div>
              <div className="text-[9px] uppercase tracking-[0.28em] text-[#5d7078] mb-1.5">
                Time Range
              </div>
              <div className="flex flex-wrap gap-1">
                {TIME_RANGE_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    onClick={() => setSinceHours(opt.value)}
                    className={clsx(
                      "rounded-md px-2 py-0.5 text-[11px] uppercase tracking-wider transition-all",
                      filters.sinceHours === opt.value
                        ? "bg-[#263a44] text-[#d0e4ea] border border-[#4a6a76]"
                        : "bg-[#121c22] text-[#6a7e84] border border-[#253038] hover:border-[#3a4e56] hover:text-[#94a6aa]"
                    )}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Severity chips */}
            <div>
              <div className="text-[9px] uppercase tracking-[0.28em] text-[#5d7078] mb-1.5">
                Severity
              </div>
              <div className="flex flex-wrap gap-1">
                {ALL_SEVERITIES.map((sev) => {
                  const isActive = filters.severities.includes(sev);
                  const config = SEVERITY_CONFIG[sev];
                  return (
                    <button
                      key={sev}
                      onClick={() => toggleSeverity(sev)}
                      className={clsx(
                        "rounded-md px-2 py-0.5 text-[11px] uppercase tracking-wider transition-all border",
                        isActive
                          ? "bg-[#263a44] text-[#d0e4ea] border-[#4a6a76]"
                          : "bg-[#121c22] text-[#6a7e84] border-[#253038] hover:border-[#3a4e56] hover:text-[#94a6aa]"
                      )}
                    >
                      {config.label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Event type chips */}
            <div>
              <div className="text-[9px] uppercase tracking-[0.28em] text-[#5d7078] mb-1.5">
                Event Type
              </div>
              <div className="flex flex-wrap gap-1">
                {ALL_EVENT_TYPES.map((type) => {
                  const isActive = filters.eventTypes.includes(type);
                  const config = EVENT_TYPE_CONFIG[type];
                  return (
                    <button
                      key={type}
                      onClick={() => toggleEventType(type)}
                      className={clsx(
                        "rounded-md px-2 py-0.5 text-[11px] tracking-wider transition-all border",
                        isActive
                          ? "border-opacity-60"
                          : "bg-[#121c22] border-[#253038] hover:border-[#3a4e56]"
                      )}
                      style={
                        isActive
                          ? {
                              backgroundColor: `${config.color}18`,
                              borderColor: `${config.color}60`,
                              color: config.color,
                            }
                          : { color: "#6a7e84" }
                      }
                    >
                      {config.label}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </div>

        {/* ─── Event list ─── */}
        <div className="flex-1 overflow-y-auto">
          {sortedEvents.length === 0 ? (
            <div className="p-4 text-center text-sm text-[#77888d]">
              {filtersActive
                ? "No events match the current filters."
                : "No events found. Try triggering the pipeline or adjusting the time range."}
            </div>
          ) : (
            <div className="divide-y divide-[#18242b]">
              {sortedEvents.map((event) => {
                const typeConfig = EVENT_TYPE_CONFIG[event.event_type];
                const severityConfig = SEVERITY_CONFIG[event.severity];
                const isSelected = event.id === selectedEventId;
                const hasImage = !!event.image_url;

                return (
                  <button
                    key={event.id}
                    onClick={() => onEventSelect(event.id)}
                    className={clsx(
                      "w-full border-l-2 text-left transition-all",
                      "hover:bg-[#132028]/68",
                      isSelected && "bg-[#16232b]/92",
                      !isSelected && "border-l-2 border-transparent",
                      hasImage ? "p-3" : "p-3.5"
                    )}
                    style={
                      isSelected
                        ? { borderLeftColor: typeConfig?.color || "#6b7280" }
                        : undefined
                    }
                  >
                    {/* Image preview (if available) */}
                    {hasImage && (
                      <div className="mb-2.5">
                        <EventThumbnail
                          src={event.image_url!}
                          alt={event.title}
                        />
                      </div>
                    )}

                    <div className="flex items-start gap-3">
                      <div
                        className="mt-1 h-3 w-3 flex-shrink-0 rounded-full shadow-[0_0_14px_currentColor]"
                        style={{ backgroundColor: typeConfig?.color, color: typeConfig?.color }}
                      />

                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2">
                          <div className="line-clamp-2 text-sm font-medium leading-snug text-[#ebeee6]">
                            {event.title}
                          </div>
                          <span className="flex-shrink-0 text-[10px] uppercase tracking-wider text-[#5d7078]">
                            {formatTimeAgo(event.created_at)}
                          </span>
                        </div>
                        <div className="flex items-center gap-2 mt-1.5">
                          <span
                            className="text-[11px] uppercase tracking-[0.18em]"
                            style={{ color: typeConfig?.color }}
                          >
                            {typeConfig?.label}
                          </span>
                          <span className="text-xs text-[#4d5a60]">|</span>
                          <span className="text-[11px] text-[#82949a]">
                            {severityConfig?.label}
                          </span>
                        </div>
                        <div className="mt-1 flex items-center gap-2 text-xs text-[#708186]">
                          <span>{event.location_name}</span>
                          {event.article_count > 0 && (
                            <>
                              <span className="text-[#49565b]">|</span>
                              <span className="flex items-center gap-1.5">
                                {(event.sources ?? []).some(isTelegramSource) && (
                                  <svg width="11" height="11" viewBox="0 0 24 24" fill="currentColor" className="text-[#29a9eb]">
                                    <path d="M9.78 18.65l.28-4.23 7.68-6.92c.34-.31-.07-.46-.52-.19L7.74 13.3 3.64 12c-.88-.25-.89-.86.2-1.3l15.97-6.16c.73-.33 1.43.18 1.15 1.3l-2.72 12.81c-.19.91-.74 1.13-1.5.71L12.6 16.3l-1.99 1.93c-.23.23-.42.42-.83.42z" />
                                  </svg>
                                )}
                                {(event.sources ?? []).map((s) => (
                                  <span
                                    key={s}
                                    className={clsx(
                                      "text-[10px] uppercase tracking-wider",
                                      isTelegramSource(s) ? "text-[#29a9eb]" : "text-[#708186]"
                                    )}
                                  >
                                    {getSourceLabel(s)}
                                  </span>
                                )).reduce<React.ReactNode[]>((acc, el, i) => {
                                  if (i > 0) acc.push(<span key={`sep-${i}`} className="text-[#49565b]">/</span>);
                                  acc.push(el);
                                  return acc;
                                }, [])}
                              </span>
                            </>
                          )}
                          {/* Media indicator icon */}
                          {hasImage && (
                            <>
                              <span className="text-[#49565b]">|</span>
                              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-[#5d7078]">
                                <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                                <circle cx="8.5" cy="8.5" r="1.5" />
                                <polyline points="21 15 16 10 5 21" />
                              </svg>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
