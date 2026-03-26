"use client";

import { useEffect, useMemo, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import Supercluster from "supercluster";
import {
  EventMapPoint,
  EventType,
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

// ─── Event point properties stored in Supercluster ───
interface EventPointProps {
  id: number;
  title: string;
  event_type: EventType;
  severity: string;
  family: string;
  location_name: string;
  article_count: number;
  color: string;
  pulseColor: string;
  hotspotColor: string;
  size: number;
  pulseSize: number;
  signalOpacity: number;
  iconImage: string;
}

// ─── Cluster aggregate properties ───
interface ClusterAggProps {
  // Dominant color for the cluster (from highest-severity event type)
  color: string;
  // Sum of severity weights (used to size the cluster circle)
  totalWeight: number;
  // Highest severity level name
  maxSeverity: string;
}

const zoomBreakpoints = {
  globalMax: 3.4,
  regionalMax: 6.8,
};

// ─── Supercluster config ───
const CLUSTER_RADIUS = 55; // px — cluster merge radius
const CLUSTER_MAX_ZOOM = 12; // stop clustering above this zoom

// ─── Throttle constants ───
const VEHICLE_UPDATE_INTERVAL = 3; // ~20fps
const PAINT_UPDATE_INTERVAL = 2; // ~30fps

// ─── Severity ordering for cluster aggregation ───
const SEVERITY_ORDER: Record<string, number> = {
  low: 0,
  medium: 1,
  high: 2,
  critical: 3,
};

// ─── Main animation loop (runs outside React lifecycle) ───

function startMainAnimation(
  m: maplibregl.Map,
  vehicles: AnimatedVehicle[],
  setAnimationFrame: (frame: number) => void
) {
  let phase = 0;
  let frameCount = 0;

  const animate = () => {
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

  // ─── Stable refs ───
  const onEventClickRef = useRef(onEventClick);
  onEventClickRef.current = onEventClick;

  // ─── Supercluster index ref ───
  const clusterIndex = useRef<Supercluster<EventPointProps, ClusterAggProps> | null>(null);

  // ─── Build supercluster point features from events ───
  const eventPoints = useMemo<Supercluster.PointFeature<EventPointProps>[]>(() => {
    return events.map((event) => {
      const typeConfig = EVENT_TYPE_CONFIG[event.event_type];
      const severityConfig = SEVERITY_CONFIG[event.severity];
      const family = getEventVisualFamily(event.event_type);

      return {
        type: "Feature" as const,
        geometry: {
          type: "Point" as const,
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
          pulseColor: typeConfig?.pulseColor ?? "rgba(142, 151, 171, 0.28)",
          hotspotColor: typeConfig?.hotspotColor ?? "rgba(142, 151, 171, 0.16)",
          size: severityConfig?.size ?? 12,
          pulseSize: severityConfig?.pulseSize ?? 30,
          signalOpacity:
            event.severity === "critical"
              ? 1
              : event.severity === "high"
                ? 0.9
                : 0.72,
          iconImage: `event-icon-${event.event_type}`,
        },
      };
    });
  }, [events]);

  // ─── Rebuild cluster index when points change ───
  useEffect(() => {
    const index = new Supercluster<EventPointProps, ClusterAggProps>({
      radius: CLUSTER_RADIUS,
      maxZoom: CLUSTER_MAX_ZOOM,
      minPoints: 2,
      // Map: extract cluster-relevant props from each point
      map: (props) => ({
        color: props.color,
        totalWeight: getSeverityWeight(props.severity as EventMapPoint["severity"]),
        maxSeverity: props.severity,
      }),
      // Reduce: merge two clusters — keep the higher severity color and sum weights
      reduce: (accumulated, props) => {
        accumulated.totalWeight += props.totalWeight;
        if (
          (SEVERITY_ORDER[props.maxSeverity] ?? 0) >
          (SEVERITY_ORDER[accumulated.maxSeverity] ?? 0)
        ) {
          accumulated.maxSeverity = props.maxSeverity;
          accumulated.color = props.color;
        }
      },
    });
    index.load(eventPoints);
    clusterIndex.current = index;

    // Push initial cluster data to the map if it's ready
    if (map.current) {
      updateClusters(map.current, index);
    }
  }, [eventPoints]);

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
        existing.properties.count = Number(existing.properties.count) + 1;
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
    const vehicles = createAnimatedVehicles();

    m.on("load", () => {
      // ─── Background fade ───
      m.addLayer({
        id: "background-fade",
        type: "background",
        paint: { "background-color": "rgba(3, 10, 14, 0.14)" },
      });

      // ─── Data sources ───
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

      // ─── Cluster layers (rendered for features with cluster: true) ───
      // Outer glow ring
      m.addLayer({
        id: "cluster-glow",
        type: "circle",
        source: "events",
        filter: ["has", "point_count"],
        paint: {
          "circle-radius": [
            "interpolate",
            ["linear"],
            ["get", "point_count"],
            2,
            28,
            10,
            40,
            50,
            55,
          ],
          "circle-color": ["get", "color"],
          "circle-opacity": 0.15,
          "circle-blur": 0.8,
        },
      });

      // Main cluster circle
      m.addLayer({
        id: "cluster-circles",
        type: "circle",
        source: "events",
        filter: ["has", "point_count"],
        paint: {
          "circle-radius": [
            "interpolate",
            ["linear"],
            ["get", "point_count"],
            2,
            18,
            10,
            28,
            50,
            40,
          ],
          "circle-color": ["get", "color"],
          "circle-opacity": 0.85,
          "circle-stroke-width": 2,
          "circle-stroke-color": "rgba(248, 243, 231, 0.5)",
          "circle-stroke-opacity": 0.6,
        },
      });

      // Cluster count label
      m.addLayer({
        id: "cluster-count",
        type: "symbol",
        source: "events",
        filter: ["has", "point_count"],
        layout: {
          "text-field": ["get", "point_count_abbreviated"],
          "text-font": ["Open Sans Bold", "Arial Unicode MS Bold"],
          "text-size": [
            "interpolate",
            ["linear"],
            ["get", "point_count"],
            2,
            12,
            10,
            14,
            50,
            16,
          ],
          "text-allow-overlap": true,
        },
        paint: {
          "text-color": "#f8f3e7",
          "text-halo-color": "rgba(0, 0, 0, 0.6)",
          "text-halo-width": 1.5,
        },
      });

      // ─── Individual event layers (only non-clustered points) ───
      m.addLayer({
        id: "event-pulse",
        type: "circle",
        source: "events",
        filter: ["!", ["has", "point_count"]],
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
        filter: ["!", ["has", "point_count"]],
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
        filter: ["!", ["has", "point_count"]],
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
        filter: ["!", ["has", "point_count"]],
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

      // ─── Interactivity: individual events ───
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

      // ─── Interactivity: cluster click-to-zoom ───
      m.on("click", "cluster-circles", (e) => {
        const feature = e.features?.[0];
        if (!feature || !clusterIndex.current) return;

        const clusterId = feature.properties?.cluster_id;
        if (clusterId == null) return;

        const expansionZoom = clusterIndex.current.getClusterExpansionZoom(
          Number(clusterId)
        );
        const coords = (feature.geometry as GeoJSON.Point).coordinates as [
          number,
          number,
        ];

        m.easeTo({
          center: coords,
          zoom: Math.min(expansionZoom, 14),
          duration: 500,
        });
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
      m.on("mouseenter", "cluster-circles", () => {
        m.getCanvas().style.cursor = "pointer";
      });
      m.on("mouseleave", "cluster-circles", () => {
        m.getCanvas().style.cursor = "";
      });

      // ─── Tooltips ───
      const popup = new maplibregl.Popup({
        closeButton: false,
        closeOnClick: false,
        className: "event-tooltip",
        offset: 18,
      });

      const showEventTooltip = (e: maplibregl.MapLayerMouseEvent) => {
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

      const showClusterTooltip = (e: maplibregl.MapLayerMouseEvent) => {
        const f = e.features?.[0];
        if (!f) return;

        const coords = (
          f.geometry as GeoJSON.Point
        ).coordinates.slice() as [number, number];
        const count = f.properties?.point_count ?? 0;
        const severity = f.properties?.maxSeverity ?? "medium";

        popup
          .setLngLat(coords)
          .setHTML(
            `<div class="map-tooltip-card">
              <div class="map-tooltip-title">${count} events</div>
              <div class="map-tooltip-meta">
                <span>Highest: ${severity} severity</span>
              </div>
              <div class="map-tooltip-sources">Click to zoom in</div>
            </div>`
          )
          .addTo(m);
      };

      m.on("mouseenter", "event-dots", showEventTooltip);
      m.on("mouseenter", "event-icons", showEventTooltip);
      m.on("mouseenter", "cluster-circles", showClusterTooltip);
      m.on("mouseleave", "event-dots", () => popup.remove());
      m.on("mouseleave", "event-icons", () => popup.remove());
      m.on("mouseleave", "cluster-circles", () => popup.remove());

      // ─── Update clusters on viewport change ───
      const onViewportChange = () => {
        if (clusterIndex.current) {
          updateClusters(m, clusterIndex.current);
        }
      };
      m.on("moveend", onViewportChange);
      m.on("zoomend", onViewportChange);

      // Push initial data
      if (clusterIndex.current) {
        updateClusters(m, clusterIndex.current);
      }

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

  // ─── Reactive hotspot updates ───
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

// ─── Helper: query supercluster for current viewport and push to map ───

function updateClusters(
  m: maplibregl.Map,
  index: Supercluster<EventPointProps, ClusterAggProps>
) {
  const source = m.getSource("events") as maplibregl.GeoJSONSource | undefined;
  if (!source) return;

  const bounds = m.getBounds();
  const zoom = Math.floor(m.getZoom());

  const bbox: GeoJSON.BBox = [
    bounds.getWest(),
    bounds.getSouth(),
    bounds.getEast(),
    bounds.getNorth(),
  ];

  const clustersAndPoints = index.getClusters(bbox, zoom);

  source.setData({
    type: "FeatureCollection",
    features: clustersAndPoints as GeoJSON.Feature[],
  });
}
