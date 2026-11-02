"use client";

import { useState, useCallback, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import dynamic from "next/dynamic";
import { fetchMapPoints, fetchEvent, fetchPressure, fetchStrategicLocations, fetchTheaters } from "@/lib/api";
import { GeoEvent, MapFilters, MapBounds, DEFAULT_FILTERS } from "@/lib/types";
import { timeRange, visibleEvents } from "@/lib/map-view";
import EventPanel from "@/components/panels/EventPanel";
import EventList from "@/components/panels/EventList";
import Header from "@/components/ui/Header";
import BriefingBar from "@/components/ui/BriefingBar";
import LegendPanel from "@/components/ui/LegendPanel";
import TimelineSlider from "@/components/ui/TimelineSlider";

// Dynamic import for map (no SSR since MapLibre needs the DOM)
const GeoMap = dynamic(() => import("@/components/map/GeoMap"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex items-center justify-center bg-gray-950">
      <div className="text-gray-500 text-sm">Loading map...</div>
    </div>
  ),
});

export default function Home() {
  const [selectedEventId, setSelectedEventId] = useState<number | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<GeoEvent | null>(null);
  const [isEventLoading, setIsEventLoading] = useState(false);
  const [isListOpen, setIsListOpen] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [filters, setFilters] = useState<MapFilters>(DEFAULT_FILTERS);
  const [mapBounds, setMapBounds] = useState<MapBounds | undefined>();
  const [timelineCursor, setTimelineCursor] = useState<Date | null>(null);

  // Fetch map points with filters + viewport bounds
  const {
    data: mapPoints = [],
    dataUpdatedAt,
    refetch: refetchPoints,
  } = useQuery({
    queryKey: ["map-points", filters, mapBounds],
    queryFn: () => fetchMapPoints(filters, mapBounds),
  });

  // The current time moves forward each time map data loads, so the timeline reaches new Events
  const [pageLoadedAt] = useState(() => new Date());
  const now = useMemo(
    () => (dataUpdatedAt ? new Date(dataUpdatedAt) : pageLoadedAt),
    [dataUpdatedAt, pageLoadedAt]
  );
  const range = useMemo(() => timeRange(mapPoints, now), [mapPoints, now]);

  // Fetch curated strategic locations once
  const { data: strategicLocations } = useQuery({
    queryKey: ["strategic-locations"],
    queryFn: fetchStrategicLocations,
    staleTime: Infinity,
  });

  // Fetch the Theater names once, for the Theater filter
  const { data: theaters = [] } = useQuery({
    queryKey: ["theaters"],
    queryFn: fetchTheaters,
    staleTime: Infinity,
  });

  // Pressure per Theater; refetches every minute like the map points (the client default)
  const { data: pressure, refetch: refetchPressure } = useQuery({
    queryKey: ["pressure"],
    queryFn: fetchPressure,
  });

  // Clicking a Theater on the map selects its chip in the Theater filter
  const handleTheaterSelect = useCallback((theater: string) => {
    setFilters((current) =>
      current.theaters.includes(theater)
        ? current
        : { ...current, theaters: [...current.theaters, theater] }
    );
  }, []);

  // Apply timeline cursor filter client-side — avoids extra API round-trips
  const visiblePoints = useMemo(
    () => visibleEvents(mapPoints, timelineCursor),
    [mapPoints, timelineCursor]
  );

  // Handle event click
  const handleEventClick = useCallback(
    async (eventId: number) => {
      setSelectedEventId(eventId);
      setIsEventLoading(true);
      try {
        const event = await fetchEvent(eventId);
        setSelectedEvent(event);
      } catch (err) {
        console.error("Failed to fetch event:", err);
      } finally {
        setIsEventLoading(false);
      }
    },
    []
  );

  // Handle close panel
  const handleClosePanel = useCallback(() => {
    setSelectedEventId(null);
    setSelectedEvent(null);
  }, []);

  // Refetch the map; the worker runs the Feeds on its own schedule
  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true);
    try {
      await Promise.all([refetchPoints(), refetchPressure()]);
    } finally {
      setIsRefreshing(false);
    }
  }, [refetchPoints, refetchPressure]);

  return (
    <main className="relative h-screen w-screen overflow-hidden bg-[#081116]">
      <Header
        eventCount={visiblePoints.length}
        onRefresh={handleRefresh}
        isRefreshing={isRefreshing}
      />

      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_10%,rgba(96,137,150,0.18),transparent_30%),radial-gradient(circle_at_80%_18%,rgba(255,105,74,0.14),transparent_24%),linear-gradient(180deg,rgba(4,10,14,0.12),rgba(5,10,14,0.58))]" />

      <div className="absolute inset-0 pt-16">
        <GeoMap
          events={visiblePoints}
          onEventClick={handleEventClick}
          selectedEventId={selectedEventId}
          onBoundsChange={setMapBounds}
          strategicLocations={strategicLocations}
          pressure={pressure}
          onTheaterSelect={handleTheaterSelect}
        />
      </div>

      <LegendPanel />
      <BriefingBar events={visiblePoints} />

      <TimelineSlider
        range={range}
        cursor={timelineCursor}
        onCursorChange={setTimelineCursor}
      />

      <div className="pt-16">
        <EventList
          events={visiblePoints}
          selectedEventId={selectedEventId}
          onEventSelect={handleEventClick}
          isOpen={isListOpen}
          onToggle={() => setIsListOpen(!isListOpen)}
          filters={filters}
          onFiltersChange={setFilters}
          theaters={theaters}
        />
      </div>

      <div className="pt-16">
        <EventPanel
          event={selectedEvent}
          isLoading={isEventLoading}
          onClose={handleClosePanel}
          onEventSelect={handleEventClick}
        />
      </div>
    </main>
  );
}
