"use client";

import { useEffect, useMemo, useRef, useCallback } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import {
  EventMapPoint,
  EVENT_TYPE_CONFIG,
  SEVERITY_CONFIG,
  getEventVisualFamily,
  getSeverityWeight,
} from "@/lib/types";
import {
  AnimatedVehicle,
  createAnimatedVehicles,
  advanceAllVehicles,
  vehiclesToGeoJSON,
  vehicleTrailsToGeoJSON,
} from "@/lib/map-vehicles";
import {
  createPlaneSprite,
  createBoatSprite,
  createEventTypeIcons,
} from "@/lib/map-sprites";

interface GeoMapProps {
  events: EventMapPoint[];
  onEventClick: (eventId: number) => void;
  selectedEventId: number | null;
}

type HotspotFeature = GeoJSON.Feature<
  GeoJSON.Point,
  Record<string, number | string>
>;

const zoomBreakpoints = {
  globalMax: 3.4,
  regionalMax: 6.8,
};

// ─── Throttle constants ───
// Vehicle GeoJSON setData() is the most expensive call — limit to ~20fps
const VEHICLE_UPDATE_INTERVAL = 3; // update every 3rd frame
// Pulse/hotspot paint property updates — limit to ~30fps
const PAINT_UPDATE_INTERVAL = 2; // update every 2nd frame

// ─── Main animation loop (runs outside React lifecycle) ───

function startMainAnimation(
  m: maplibregl.Map,
  vehicles: AnimatedVehicle[],
  setAnimationFrame: (frame: number) => void
) {
  let phase = 0;
  let frameCount = 0;

  const animate = () => {
    // Skip entirely when browser tab is hidden — no point rendering offscreen
    if (document.hidden) {
      setAnimationFrame(requestAnimationFrame(animate));
      return;
    }

    frameCount++;
    phase = (phase + 0.0135) % 1;

    // ─── Event pulse animation (throttled to ~30fps) ───
    if (frameCount % PAINT_UPDATE_INTERVAL === 0) {
      const pulseOpacity = Math.sin(phase * Math.PI) * 0.36;
      const strokeOpacity = Math.sin(phase * Math.PI) * 0.22;
      const scale = 0.58 + phase * 0.7;

      try {
        if (m.getLayer("event-pulse")) {
          m.setPaintProperty("event-pulse", "circle-opacity", pulseOpacity);
          m.setPaintProperty(
            "event-pulse",
            "circle-stroke-opacity",
            strokeOpacity
          );
          m.setPaintProperty("event-pulse", "circle-radius", [
            "interpolate",
            ["linear"],
            ["zoom"],
            1.5,
            ["*", ["get", "pulseSize"], scale * 0.8],
            6,
            ["*", ["get", "pulseSize"], scale],
            9,
            ["*", ["get", "pulseSize"], scale * 1.08],
          ]);
        }

        if (m.getLayer("hotspot-core")) {
          m.setPaintProperty("hotspot-core", "circle-opacity", [
            "interpolate",
            ["linear"],
            ["zoom"],
            1.5,
            0.22 + Math.sin(phase * Math.PI) * 0.04,
            zoomBreakpoints.regionalMax,
            0.08,
          ]);
        }
      } catch {
        // map removed during animation
      }
    }

    // ─── Vehicle animation (throttled to ~20fps) ───
    // Advance vehicle state every frame to keep movement smooth,
    // but only push GeoJSON to the GPU at the throttled rate
    advanceAllVehicles(vehicles);

    if (frameCount % VEHICLE_UPDATE_INTERVAL === 0) {
      try {
        const vehicleSource = m.getSource(
          "vehicles"
        ) as maplibregl.GeoJSONSource | undefined;
        vehicleSource?.setData(vehiclesToGeoJSON(vehicles));

        const trailSource = m.getSource(
          "vehicle-trails"
        ) as maplibregl.GeoJSONSource | undefined;
        trailSource?.setData(vehicleTrailsToGeoJSON(vehicles));

        // Dynamically scale trail opacity based on zoom level
        if (m.getLayer("vehicle-trail-layer")) {
          const z = m.getZoom();
          const zoomOpacity =
            z <= 1 ? 0.3 : z >= 8 ? 0.55 : 0.3 + (z - 1) * (0.25 / 7);
          m.setPaintProperty("vehicle-trail-layer", "line-opacity", [
            "*",
            ["get", "opacity"],
            zoomOpacity,
          ]);
        }
      } catch {
        // source not ready
      }
    }

    setAnimationFrame(requestAnimationFrame(animate));
  };

  animate();
}

export default function GeoMap({
  events,
  onEventClick,
  selectedEventId,
}: GeoMapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);

  // ─── Stable refs for values needed inside map callbacks ───
  // This prevents the map init useEffect from re-running when
  // these values change, which would tear down and rebuild the entire map.
  const onEventClickRef = useRef(onEventClick);
  onEventClickRef.current = onEventClick;

  const eventGeoJSON = useMemo<GeoJSON.FeatureCollection>(() => {
    return {
      type: "FeatureCollection",
      features: events.map((event) => {
        const typeConfig = EVENT_TYPE_CONFIG[event.event_type];
        const severityConfig = SEVERITY_CONFIG[event.severity];
        const family = getEventVisualFamily(event.event_type);

        return {
          type: "Feature",
          geometry: {
            type: "Point",
            coordinates: [event.longitude, event.latitude],
          },
          properties: {
            id: event.id,
            title: event.title,
            event_type: event.event_type,
            severity: event.severity,
            family,
            location_name: event.location_name,
            article_count: event.article_count,
            color: typeConfig?.color ?? "#8e97ab",
            pulseColor:
              typeConfig?.pulseColor ?? "rgba(142, 151, 171, 0.28)",
            hotspotColor:
              typeConfig?.hotspotColor ?? "rgba(142, 151, 171, 0.16)",
            size: severityConfig?.size ?? 12,
            pulseSize: severityConfig?.pulseSize ?? 30,
            signalOpacity:
              event.severity === "critical"
                ? 1
                : event.severity === "high"
                  ? 0.9
                  : 0.72,
            // Icon image name for the symbol layer
            iconImage: `event-icon-${event.event_type}`,
          },
        } satisfies GeoJSON.Feature;
      }),
    };
  }, [events]);

  const hotspotGeoJSON = useMemo<GeoJSON.FeatureCollection>(() => {
    const grouped = new Map<string, HotspotFeature>();

    for (const event of events) {
      const roundedLat = Math.round(event.latitude * 2) / 2;
      const roundedLng = Math.round(event.longitude * 2) / 2;
      const family = getEventVisualFamily(event.event_type);
      const key = `${roundedLat}:${roundedLng}:${family}`;
      const typeConfig = EVENT_TYPE_CONFIG[event.event_type];
      const severityWeight = getSeverityWeight(event.severity);
      const articleBoost = Math.min(event.article_count * 0.05, 0.18);
      const influence = severityWeight + articleBoost;

      const existing = grouped.get(key);
      if (existing) {
        existing.properties.intensity =
          Number(existing.properties.intensity) + influence;
        existing.properties.count =
          Number(existing.properties.count) + 1;
        existing.properties.radius = Math.min(
          Number(existing.properties.radius) + severityWeight * 10,
          90
        );
        continue;
      }

      grouped.set(key, {
        type: "Feature",
        geometry: {
          type: "Point",
          coordinates: [roundedLng, roundedLat],
        },
        properties: {
          key,
          family,
          count: 1,
          intensity: influence,
          radius: 26 + severityWeight * 32,
          color: typeConfig?.color ?? "#8e97ab",
          hotspotColor:
            typeConfig?.hotspotColor ?? "rgba(142, 151, 171, 0.16)",
        },
      });
    }

    return {
      type: "FeatureCollection",
      features: [...grouped.values()],
    };
  }, [events]);

  // ─── Map initialization (runs ONCE) ───
  // We intentionally use an empty dependency array here. Data updates
  // are handled reactively by the separate useEffects below, and the
  // onEventClick callback is accessed via a stable ref.
  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    let animationFrame: number | null = null;

    const mapTilerKey = process.env.NEXT_PUBLIC_MAPTILER_API_KEY;

    const mapStyle = mapTilerKey
      ? `https://api.maptiler.com/maps/backdrop/style.json?key=${mapTilerKey}`
      : {
          version: 8 as const,
          name: "Operations Grid",
          sources: {
            "osm-tiles": {
              type: "raster" as const,
              tiles: [
                "https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png",
                "https://b.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png",
                "https://c.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png",
              ],
              tileSize: 256,
              attribution:
                '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>',
            },
          },
          layers: [
            {
              id: "osm-tiles-layer",
              type: "raster" as const,
              source: "osm-tiles",
              minzoom: 0,
              maxzoom: 19,
            },
          ],
        };

    map.current = new maplibregl.Map({
      container: mapContainer.current,
      style: mapStyle,
      center: [25, 22],
      zoom: 2.35,
      minZoom: 1.45,
      maxZoom: 15,
      attributionControl: false,
    });

    map.current.addControl(
      new maplibregl.NavigationControl({ showCompass: false }),
      "bottom-right"
    );

    map.current.addControl(
      new maplibregl.AttributionControl({ compact: true }),
      "bottom-left"
    );

    const m = map.current;

    // ─── Generate animated data ───
    const vehicles = createAnimatedVehicles();

    m.on("load", () => {
      // ─── Background fade ───
      m.addLayer({
        id: "background-fade",
        type: "background",
        paint: {
          "background-color": "rgba(3, 10, 14, 0.14)",
        },
      });

      // ─── Event data sources ───
      // Initial data will be set reactively by the useEffects below,
      // but we seed with empty collections so the sources exist immediately.
      m.addSource("events", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });

      m.addSource("hotspots", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });

      // ─── Hotspot layers ───
      m.addLayer({
        id: "hotspot-wash",
        type: "circle",
        source: "hotspots",
        paint: {
          "circle-radius": [
            "interpolate",
            ["linear"],
            ["zoom"],
            1.5,
            ["*", ["get", "radius"], 1.4],
            7,
            ["*", ["get", "radius"], 0.7],
          ],
          "circle-color": ["get", "color"],
          "circle-opacity": [
            "interpolate",
            ["linear"],
            ["zoom"],
            1.5,
            0.18,
            4.5,
            0.12,
            7.5,
            0.03,
          ],
          "circle-blur": 1,
        },
      });

      m.addLayer({
        id: "hotspot-core",
        type: "circle",
        source: "hotspots",
        paint: {
          "circle-radius": [
            "interpolate",
            ["linear"],
            ["zoom"],
            1.5,
            ["*", ["get", "radius"], 0.65],
            5.5,
            ["*", ["get", "radius"], 0.35],
            8.5,
            6,
          ],
          "circle-color": ["get", "color"],
          "circle-opacity": [
            "interpolate",
            ["linear"],
            ["zoom"],
            1.5,
            0.24,
            4.5,
            0.16,
            8,
            0.05,
          ],
          "circle-blur": 0.6,
        },
      });

      // ─── Event circle layers ───
      m.addLayer({
        id: "event-pulse",
        type: "circle",
        source: "events",
        paint: {
          "circle-radius": ["get", "pulseSize"],
          "circle-color": ["get", "pulseColor"],
          "circle-opacity": 0,
          "circle-stroke-width": 1.5,
          "circle-stroke-color": ["get", "color"],
          "circle-stroke-opacity": 0,
        },
      });

      m.addLayer({
        id: "event-glow",
        type: "circle",
        source: "events",
        paint: {
          "circle-radius": ["+", ["get", "size"], 10],
          "circle-color": ["get", "color"],
          "circle-opacity": [
            "interpolate",
            ["linear"],
            ["zoom"],
            1.5,
            0.2,
            4.5,
            0.16,
            8,
            0.08,
          ],
          "circle-blur": 1,
        },
      });

      m.addLayer({
        id: "event-dots",
        type: "circle",
        source: "events",
        paint: {
          "circle-radius": [
            "interpolate",
            ["linear"],
            ["zoom"],
            1.5,
            ["*", ["get", "size"], 0.8],
            5,
            ["get", "size"],
            9,
            ["*", ["get", "size"], 1.2],
          ],
          "circle-color": ["get", "color"],
          "circle-opacity": [
            "interpolate",
            ["linear"],
            ["zoom"],
            1.5,
            ["*", ["get", "signalOpacity"], 0.9],
            4,
            ["*", ["get", "signalOpacity"], 0.92],
            8,
            0.96,
          ],
          "circle-stroke-width": [
            "case",
            ["==", ["get", "severity"], "critical"],
            2.5,
            1.4,
          ],
          "circle-stroke-color": "#f8f3e7",
          "circle-stroke-opacity": [
            "interpolate",
            ["linear"],
            ["zoom"],
            1.5,
            0.7,
            5.5,
            0.4,
            7,
            0.0,
          ],
        },
      });

      // ─── Event-type icon layer (visible at zoom >= 5.5) ───
      const eventIcons = createEventTypeIcons(48);
      for (const [name, imageData] of eventIcons) {
        m.addImage(name, imageData, { pixelRatio: 2 });
      }

      m.addLayer({
        id: "event-icons",
        type: "symbol",
        source: "events",
        minzoom: 5.5,
        layout: {
          "icon-image": ["get", "iconImage"],
          "icon-size": [
            "interpolate",
            ["linear"],
            ["zoom"],
            5.5,
            0.8,
            8,
            1.2,
            12,
            1.5,
          ],
          "icon-allow-overlap": true,
          "icon-ignore-placement": true,
          "icon-anchor": "center",
          "icon-offset": [0, -18],
        },
        paint: {
          "icon-opacity": [
            "interpolate",
            ["linear"],
            ["zoom"],
            5.5,
            0,
            6.5,
            0.9,
            10,
            1,
          ],
        },
      });

      // ─── Vehicle trail layers ───
      m.addSource("vehicle-trails", {
        type: "geojson",
        data: vehicleTrailsToGeoJSON(vehicles),
      });

      m.addLayer({
        id: "vehicle-trail-layer",
        type: "line",
        source: "vehicle-trails",
        paint: {
          "line-color": [
            "match",
            ["get", "type"],
            "plane",
            "rgba(212, 200, 168, 0.35)",
            "boat",
            "rgba(168, 184, 196, 0.35)",
            "rgba(180, 180, 180, 0.35)",
          ],
          "line-width": [
            "interpolate",
            ["linear"],
            ["zoom"],
            1,
            0.8,
            4,
            1.2,
            8,
            1.8,
          ],
          "line-dasharray": [4, 3],
          "line-opacity": ["get", "opacity"],
        },
      });

      // ─── Vehicle icon layers ───
      const planeSprite = createPlaneSprite(28, "#d4c8a8");
      const boatSprite = createBoatSprite(24, "#a8b8c4");
      m.addImage("plane-icon", planeSprite, { pixelRatio: 2 });
      m.addImage("boat-icon", boatSprite, { pixelRatio: 2 });

      m.addSource("vehicles", {
        type: "geojson",
        data: vehiclesToGeoJSON(vehicles),
      });

      m.addLayer({
        id: "vehicle-layer",
        type: "symbol",
        source: "vehicles",
        layout: {
          "icon-image": [
            "match",
            ["get", "type"],
            "plane",
            "plane-icon",
            "boat",
            "boat-icon",
            "plane-icon",
          ],
          "icon-size": [
            "interpolate",
            ["linear"],
            ["zoom"],
            1,
            0.7,
            4,
            1.0,
            8,
            1.4,
          ],
          "icon-rotate": ["get", "bearing"],
          "icon-rotation-alignment": "map",
          "icon-allow-overlap": true,
          "icon-ignore-placement": true,
        },
        paint: {
          "icon-opacity": [
            "interpolate",
            ["linear"],
            ["zoom"],
            1,
            0.6,
            4,
            0.75,
            8,
            0.85,
          ],
        },
      });

      // ─── Interactivity ───
      // Use the ref so we always call the latest callback without
      // needing to tear down and re-add the listener.
      m.on("click", "event-dots", (e) => {
        const feature = e.features?.[0];
        const eventId = feature?.properties?.id;
        if (eventId) {
          onEventClickRef.current(Number(eventId));
        }
      });

      m.on("click", "event-icons", (e) => {
        const feature = e.features?.[0];
        const eventId = feature?.properties?.id;
        if (eventId) {
          onEventClickRef.current(Number(eventId));
        }
      });

      m.on("mouseenter", "event-dots", () => {
        m.getCanvas().style.cursor = "pointer";
      });

      m.on("mouseleave", "event-dots", () => {
        m.getCanvas().style.cursor = "";
      });

      m.on("mouseenter", "event-icons", () => {
        m.getCanvas().style.cursor = "pointer";
      });

      m.on("mouseleave", "event-icons", () => {
        m.getCanvas().style.cursor = "";
      });

      const popup = new maplibregl.Popup({
        closeButton: false,
        closeOnClick: false,
        className: "event-tooltip",
        offset: 18,
      });

      const showTooltip = (e: maplibregl.MapLayerMouseEvent) => {
        const f = e.features?.[0];
        if (!f) return;

        const coords = (
          f.geometry as GeoJSON.Point
        ).coordinates.slice() as [number, number];
        const props = f.properties;
        const typeConfig =
          EVENT_TYPE_CONFIG[
            props?.event_type as keyof typeof EVENT_TYPE_CONFIG
          ];
        const severityConfig =
          SEVERITY_CONFIG[
            props?.severity as keyof typeof SEVERITY_CONFIG
          ];

        popup
          .setLngLat(coords)
          .setHTML(
            `<div class="map-tooltip-card">
              <div class="map-tooltip-title">${props?.title ?? ""}</div>
              <div class="map-tooltip-meta">
                <span style="color:${typeConfig?.color ?? "#9aa8ac"}">${typeConfig?.label ?? props?.event_type}</span>
                <span class="map-tooltip-divider">|</span>
                <span>${severityConfig?.label ?? props?.severity} severity</span>
              </div>
              <div class="map-tooltip-location">${props?.location_name ?? ""}</div>
              <div class="map-tooltip-sources">${props?.article_count ?? 0} source(s)</div>
            </div>`
          )
          .addTo(m);
      };

      m.on("mouseenter", "event-dots", showTooltip);
      m.on("mouseenter", "event-icons", showTooltip);
      m.on("mouseleave", "event-dots", () => popup.remove());
      m.on("mouseleave", "event-icons", () => popup.remove());

      // ─── Start unified animation loop ───
      startMainAnimation(m, vehicles, (frame) => {
        animationFrame = frame;
      });
    });

    return () => {
      if (animationFrame) cancelAnimationFrame(animationFrame);
      m.remove();
      map.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ─── Reactive data updates ───
  // These effects push new data to existing map sources without
  // tearing down the map. They run whenever the derived GeoJSON changes.
  useEffect(() => {
    if (!map.current) return;
    const m = map.current;
    // The source may not exist yet if the map hasn't finished loading.
    // In that case, the 'load' handler will pick up the latest data
    // from the ref-based reactive update on first paint.
    const source = m.getSource("events") as maplibregl.GeoJSONSource | undefined;
    source?.setData(eventGeoJSON);
  }, [eventGeoJSON]);

  useEffect(() => {
    if (!map.current) return;
    const source = map.current.getSource(
      "hotspots"
    ) as maplibregl.GeoJSONSource | undefined;
    source?.setData(hotspotGeoJSON);
  }, [hotspotGeoJSON]);

  return (
    <div ref={mapContainer} className="absolute inset-0 h-full w-full" />
  );
}
