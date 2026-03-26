/**
 * Synthetic vehicle routes for animated planes and boats on the map.
 * Routes are realistic great-circle approximations between major cities/ports.
 *
 * Animation model:
 * - One-way travel (no ping-pong)
 * - Each vehicle leaves a dashed trail line that fades behind it
 * - When reaching route end, the vehicle is deactivated
 * - After a random cooldown, a new inactive route is spawned
 * - Only a subset of routes are active at any time (configurable max)
 * - Vehicle speed is normalized by route distance so long routes take longer
 */

export interface VehicleRoute {
  id: string;
  type: "plane" | "boat";
  /** Waypoints as [lng, lat] pairs */
  coordinates: [number, number][];
  /** Speed multiplier relative to others of the same type (1.0 = normal) */
  speed: number;
}

export interface AnimatedVehicle {
  route: VehicleRoute;
  /** Progress along the route (0..1) */
  progress: number;
  /** Whether this vehicle is currently visible on the map */
  active: boolean;
  /** Frame count until this vehicle spawns (0 = ready now) */
  spawnDelay: number;
  /** Pre-computed total route distance in degrees (for speed normalization) */
  routeDistance: number;
  /** Trail fade-out progress (0 = fully visible, 1 = fully faded). -1 = not fading */
  trailFade: number;
}

/** Configuration for the vehicle pool */
const POOL_CONFIG = {
  /** Maximum number of vehicles visible at once */
  maxActive: 7,
  /** Number of vehicles to show immediately on load */
  initialSpawn: 3,
  /** Min/max frames between staggered spawns on load (60fps) */
  staggerMinFrames: 180, // ~3 seconds
  staggerMaxFrames: 360, // ~6 seconds
  /** Min/max frames before a completed vehicle's route is re-eligible */
  cooldownMinFrames: 300, // ~5 seconds
  cooldownMaxFrames: 1200, // ~20 seconds
  /** Frames for trail to fade out after vehicle completes route (~2 seconds) */
  trailFadeFrames: 120,
};

// ─── Flight Routes ───

const flightRoutes: VehicleRoute[] = [
  {
    id: "flight-nyc-london",
    type: "plane",
    coordinates: [
      [-74.0, 40.7], // New York
      [-60.0, 47.0], // Nova Scotia
      [-40.0, 52.0], // Mid-Atlantic (great circle)
      [-20.0, 53.0], // Approaching Ireland
      [-0.13, 51.5], // London
    ],
    speed: 1.0,
  },
  {
    id: "flight-dubai-singapore",
    type: "plane",
    coordinates: [
      [55.3, 25.3], // Dubai
      [65.0, 21.0], // Over Arabian Sea
      [72.0, 16.0], // Off west coast of India
      [80.0, 10.0], // Sri Lanka
      [92.0, 5.0], // Over Bay of Bengal
      [103.8, 1.35], // Singapore
    ],
    speed: 0.9,
  },
  {
    id: "flight-tokyo-la",
    type: "plane",
    coordinates: [
      [139.7, 35.7], // Tokyo
      [150.0, 40.0], // East of Japan
      [165.0, 45.0], // North Pacific (great circle goes north)
      [180.0, 48.0], // Date line
      [195.0, 48.0], // Aleutian area (360-165)
      [215.0, 45.0], // Gulf of Alaska (360-145)
      [230.0, 40.0], // Off Oregon coast (360-130)
      [241.8, 33.9], // Los Angeles (360-118.2)
    ],
    speed: 0.95,
  },
  {
    id: "flight-moscow-beijing",
    type: "plane",
    coordinates: [
      [37.6, 55.8], // Moscow
      [50.0, 54.0], // Over Urals
      [68.0, 52.0], // Over Kazakhstan
      [80.0, 50.0], // Central Asia
      [95.0, 47.0], // Southern Siberia
      [108.0, 43.0], // Mongolia
      [116.4, 39.9], // Beijing
    ],
    speed: 0.85,
  },
  {
    id: "flight-saopaulo-johannesburg",
    type: "plane",
    coordinates: [
      [-46.6, -23.5], // São Paulo
      [-40.0, -22.0], // Off Brazilian coast
      [-30.0, -20.0], // Mid-South-Atlantic
      [-18.0, -18.0], // Approaching Africa
      [-5.0, -15.0], // Off West Africa
      [8.0, -12.0], // Gulf of Guinea
      [16.0, -18.0], // Over Angola
      [28.0, -26.2], // Johannesburg
    ],
    speed: 0.9,
  },
  {
    id: "flight-cairo-istanbul",
    type: "plane",
    coordinates: [
      [31.2, 30.0], // Cairo
      [31.5, 32.0], // Over Sinai
      [32.0, 34.5], // Over Eastern Mediterranean
      [30.5, 37.5], // Southern Turkey
      [29.0, 41.0], // Istanbul
    ],
    speed: 0.7,
  },
  {
    id: "flight-paris-delhi",
    type: "plane",
    coordinates: [
      [2.35, 48.9], // Paris
      [10.0, 47.0], // Over Alps
      [20.0, 44.0], // Over Balkans
      [32.0, 40.0], // Over Turkey
      [44.0, 36.0], // Over Iraq
      [56.0, 32.0], // Over Iran
      [66.0, 30.0], // Over Pakistan
      [77.2, 28.6], // Delhi
    ],
    speed: 0.9,
  },
  {
    id: "flight-sydney-tokyo",
    type: "plane",
    coordinates: [
      [151.2, -33.9], // Sydney
      [150.0, -25.0], // Over Queensland
      [148.0, -15.0], // North Queensland
      [143.0, -5.0], // Papua New Guinea
      [138.0, 5.0], // Near Palau
      [137.0, 15.0], // Philippine Sea
      [138.0, 25.0], // Approaching Japan
      [139.7, 35.7], // Tokyo
    ],
    speed: 0.95,
  },
  {
    id: "flight-dc-frankfurt",
    type: "plane",
    coordinates: [
      [-77.0, 38.9], // Washington DC
      [-65.0, 43.0], // Off New England
      [-50.0, 48.0], // North Atlantic
      [-35.0, 51.0], // Mid-Atlantic (great circle)
      [-20.0, 52.0], // Approaching Ireland
      [-5.0, 51.5], // Over Ireland
      [8.7, 50.1], // Frankfurt
    ],
    speed: 1.0,
  },
  {
    id: "flight-ankara-riyadh",
    type: "plane",
    coordinates: [
      [32.9, 39.9], // Ankara
      [35.0, 37.0], // Southern Turkey
      [38.0, 34.0], // Over Syria/Iraq border
      [42.0, 30.0], // Northern Arabia
      [46.7, 24.7], // Riyadh
    ],
    speed: 0.7,
  },
  // ─── New Americas Routes ───
  {
    id: "flight-miami-bogota",
    type: "plane",
    coordinates: [
      [-80.2, 25.8], // Miami
      [-79.5, 22.0], // Over Cuba
      [-78.0, 18.0], // Over Jamaica
      [-76.5, 14.0], // Over Caribbean Sea
      [-75.0, 10.0], // Off Colombian coast
      [-74.1, 4.7], // Bogotá
    ],
    speed: 0.75,
  },
  {
    id: "flight-nyc-saopaulo",
    type: "plane",
    coordinates: [
      [-74.0, 40.7], // New York
      [-72.0, 35.0], // Off Carolinas
      [-68.0, 28.0], // Over Bahamas area
      [-62.0, 18.0], // Eastern Caribbean
      [-55.0, 5.0], // Off northern Brazil
      [-48.0, -5.0], // Over Recife
      [-46.6, -23.5], // São Paulo
    ],
    speed: 0.95,
  },
  {
    id: "flight-la-mexicocity",
    type: "plane",
    coordinates: [
      [-118.2, 33.9], // Los Angeles
      [-115.0, 31.0], // Over Tijuana/border
      [-110.0, 27.0], // Over Baja California
      [-105.0, 23.0], // Over Guadalajara
      [-99.1, 19.4], // Mexico City
    ],
    speed: 0.7,
  },
  {
    id: "flight-buenosaires-lima",
    type: "plane",
    coordinates: [
      [-58.4, -34.6], // Buenos Aires
      [-60.0, -30.0], // Over Córdoba
      [-62.0, -24.0], // Northern Argentina
      [-65.0, -18.0], // Over Bolivia
      [-70.0, -15.0], // Southern Peru
      [-77.0, -12.0], // Lima
    ],
    speed: 0.8,
  },
];

// ─── Shipping Routes ───

const shippingRoutes: VehicleRoute[] = [
  {
    id: "ship-hormuz-patrol",
    type: "boat",
    coordinates: [
      [56.3, 26.6], // Strait of Hormuz entrance
      [57.0, 25.8], // Mid-strait
      [56.0, 25.0], // Gulf of Oman
      [57.5, 24.0], // South patrol point
    ],
    speed: 0.3,
  },
  {
    id: "ship-south-china-sea",
    type: "boat",
    coordinates: [
      [104.0, 1.3], // Singapore Strait
      [106.0, 3.5], // South China Sea entry
      [108.0, 6.0], // South China Sea
      [111.0, 8.5], // Spratly approach
      [114.0, 10.0], // Spratly area
      [117.0, 14.5], // Near Scarborough Shoal
      [119.0, 18.5], // West of Luzon, South China Sea
    ],
    speed: 0.25,
  },
  {
    id: "ship-mediterranean",
    type: "boat",
    coordinates: [
      [-5.3, 35.9], // Gibraltar
      [0.0, 37.0], // Alboran Sea
      [3.0, 37.0], // Algerian coast
      [8.0, 37.5], // Sardinia
      [14.0, 36.0], // Near Malta
      [20.0, 35.5], // South of Greece
      [25.0, 35.0], // Crete
      [30.0, 34.5], // East Med
      [33.0, 34.5], // South of Cyprus, open water
    ],
    speed: 0.28,
  },
  {
    id: "ship-red-sea",
    type: "boat",
    coordinates: [
      [43.1, 12.5], // Bab el-Mandeb
      [41.5, 14.0], // Southern Red Sea
      [40.0, 16.0], // Central Red Sea
      [38.5, 18.5], // Mid Red Sea
      [37.0, 20.0], // Northern Red Sea
      [36.2, 23.5], // Upper Red Sea, center channel
      [34.0, 27.0], // Near Suez approach
    ],
    speed: 0.22,
  },
  {
    id: "ship-cape-route",
    type: "boat",
    coordinates: [
      [18.4, -33.9], // Cape Town
      [20.0, -34.8], // Cape of Good Hope
      [25.0, -35.0], // South of Cape Agulhas
      [30.0, -32.0], // East coast South Africa
      [36.0, -28.0], // Mozambique Channel approach
      [41.0, -21.0], // Mozambique Channel, center
      [48.0, -16.0], // Madagascar east
      [53.0, -12.0], // Open Indian Ocean
      [57.0, -10.0], // Approaching Seychelles
    ],
    speed: 0.2,
  },
  {
    id: "ship-baltic-patrol",
    type: "boat",
    coordinates: [
      [12.0, 55.5], // Near Copenhagen
      [14.0, 55.8], // Southern Baltic
      [15.0, 56.5], // Off Bornholm
      [17.0, 56.8], // Central Baltic
      [19.0, 57.0], // Near Gotland
      [20.5, 58.0], // Northern Baltic
      [21.0, 58.5], // Open Baltic, west of Finland
      [24.5, 59.4], // Near Tallinn
    ],
    speed: 0.26,
  },
  // ─── New Atlantic Boat Routes ───
  {
    id: "ship-north-atlantic",
    type: "boat",
    coordinates: [
      [-76.3, 36.8], // Norfolk, VA
      [-72.0, 37.5], // Off Virginia coast
      [-65.0, 38.0], // Open Atlantic
      [-55.0, 38.5], // Mid-Atlantic
      [-45.0, 37.5], // Central Atlantic
      [-35.0, 37.0], // Azores approach
      [-25.0, 36.5], // Past Azores
      [-15.0, 36.5], // Approaching Iberia
      [-5.3, 35.9], // Strait of Gibraltar
    ],
    speed: 0.2,
  },
  {
    id: "ship-south-atlantic",
    type: "boat",
    coordinates: [
      [-46.3, -23.9], // Santos, Brazil
      [-42.0, -22.0], // Off Rio de Janeiro
      [-35.0, -18.0], // Off Recife
      [-25.0, -14.0], // Mid-South-Atlantic
      [-15.0, -10.0], // Approaching equatorial
      [-5.0, -7.0], // Central Atlantic
      [5.0, -6.0], // Gulf of Guinea approach
      [13.2, -8.8], // Luanda, Angola
    ],
    speed: 0.2,
  },
  {
    id: "ship-caribbean-northsea",
    type: "boat",
    coordinates: [
      [-79.6, 9.4], // Panama Canal Atlantic side, Colon harbor
      [-76.0, 12.0], // Caribbean Sea
      [-70.0, 15.0], // Central Caribbean
      [-65.0, 20.0], // Near Puerto Rico
      [-62.0, 28.0], // Bermuda approach
      [-55.0, 35.0], // Open North Atlantic
      [-45.0, 40.0], // Mid-Atlantic
      [-30.0, 44.0], // North Atlantic
      [-15.0, 48.0], // Approaching English Channel
      [-5.0, 49.5], // English Channel entrance
      [1.0, 51.0], // Dover Strait
      [4.0, 51.9], // Rotterdam
    ],
    speed: 0.18,
  },
];

// ─── Geo Utilities ───

/** Calculate the great-circle distance between two [lng, lat] points in degrees */
function haversineDistance(
  a: [number, number],
  b: [number, number]
): number {
  const toRad = (d: number) => (d * Math.PI) / 180;
  const lat1 = toRad(a[1]);
  const lat2 = toRad(b[1]);
  const dLat = toRad(b[1] - a[1]);
  const dLng = toRad(b[0] - a[0]);

  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
  // Return in "degrees" equivalent (not km) — we just need relative distances
  return (2 * Math.atan2(Math.sqrt(h), Math.sqrt(1 - h)) * 180) / Math.PI;
}

/** Compute total route distance (sum of segment haversine distances) */
function computeRouteDistance(coordinates: [number, number][]): number {
  let total = 0;
  for (let i = 1; i < coordinates.length; i++) {
    total += haversineDistance(coordinates[i - 1], coordinates[i]);
  }
  return total;
}

/** Interpolate between two [lng, lat] points */
function interpolate(
  a: [number, number],
  b: [number, number],
  t: number
): [number, number] {
  return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];
}

/** Calculate bearing between two points (degrees, 0 = north, CW) */
export function calcBearing(
  start: [number, number],
  end: [number, number]
): number {
  const startLat = (start[1] * Math.PI) / 180;
  const startLng = (start[0] * Math.PI) / 180;
  const endLat = (end[1] * Math.PI) / 180;
  const endLng = (end[0] * Math.PI) / 180;

  const dLng = endLng - startLng;
  const y = Math.sin(dLng) * Math.cos(endLat);
  const x =
    Math.cos(startLat) * Math.sin(endLat) -
    Math.sin(startLat) * Math.cos(endLat) * Math.cos(dLng);

  return ((Math.atan2(y, x) * 180) / Math.PI + 360) % 360;
}

function randInt(min: number, max: number): number {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

// ─── Initialization ───

/**
 * Create the full pool of vehicles. All start inactive except a small initial set.
 * Vehicles are assigned staggered spawn delays so they appear gradually.
 */
export function createAnimatedVehicles(): AnimatedVehicle[] {
  const allRoutes = [...flightRoutes, ...shippingRoutes];

  // Shuffle to randomize which routes appear first
  const shuffled = allRoutes
    .map((r) => ({ route: r, sort: Math.random() }))
    .sort((a, b) => a.sort - b.sort)
    .map((r) => r.route);

  return shuffled.map((route, index) => {
    const routeDistance = computeRouteDistance(route.coordinates);
    const isInitial = index < POOL_CONFIG.initialSpawn;

    return {
      route,
      progress: 0,
      active: isInitial,
      spawnDelay: isInitial
        ? index *
          randInt(
            POOL_CONFIG.staggerMinFrames / 2,
            POOL_CONFIG.staggerMaxFrames / 2
          )
        : randInt(
            POOL_CONFIG.cooldownMinFrames,
            POOL_CONFIG.cooldownMaxFrames
          ),
      routeDistance,
      trailFade: -1,
    };
  });
}

/** Get the current position and bearing of a vehicle along its route */
export function getVehiclePosition(vehicle: AnimatedVehicle): {
  coordinates: [number, number];
  bearing: number;
} {
  const coords = vehicle.route.coordinates;
  const totalSegments = coords.length - 1;

  if (totalSegments <= 0) {
    return { coordinates: coords[0], bearing: 0 };
  }

  const progressAlongRoute = vehicle.progress * totalSegments;
  const segIndex = Math.min(
    Math.floor(progressAlongRoute),
    totalSegments - 1
  );
  const segT = progressAlongRoute - segIndex;

  const a = coords[segIndex];
  const b = coords[Math.min(segIndex + 1, coords.length - 1)];

  const position = interpolate(a, b, segT);
  const bearing = calcBearing(a, b);

  return { coordinates: position, bearing };
}

/**
 * Advance all vehicles by one tick. Handles:
 * - Speed normalized by route distance (longer routes move slower in progress)
 * - Deactivating vehicles that complete their route
 * - Counting down spawn delays for inactive vehicles
 * - Spawning new vehicles when under the active cap
 */
export function advanceAllVehicles(vehicles: AnimatedVehicle[]): void {
  // Base speed constants (progress per frame at 60fps)
  // These are "degrees per frame" effectively, divided by route distance
  const PLANE_BASE_SPEED = 0.048; // degrees per frame (reduced 40% from 0.08)
  const BOAT_BASE_SPEED = 0.0132; // degrees per frame (increased 10% from 0.012)

  let activeCount = 0;

  for (const vehicle of vehicles) {
    if (vehicle.active && vehicle.spawnDelay <= 0) {
      activeCount++;

      // Speed = base_speed_per_degree / total_route_distance * route_speed_multiplier
      // This means a 100-degree route takes 10x longer than a 10-degree route
      const baseSpeed =
        vehicle.route.type === "plane" ? PLANE_BASE_SPEED : BOAT_BASE_SPEED;
      const normalizedSpeed =
        (baseSpeed / Math.max(vehicle.routeDistance, 1)) * vehicle.route.speed;

      vehicle.progress += normalizedSpeed;

      // Vehicle finished its route — start trail fade
      if (vehicle.progress >= 1) {
        vehicle.active = false;
        vehicle.progress = 1; // keep at 1 so trail shows full route
        vehicle.trailFade = 0; // start fade-out (0 = just started)
        activeCount--;
      }
    } else if (vehicle.active && vehicle.spawnDelay > 0) {
      // Counting down to initial appearance
      vehicle.spawnDelay--;
      if (vehicle.spawnDelay <= 0) {
        activeCount++;
      }
    } else if (!vehicle.active) {
      if (vehicle.trailFade >= 0 && vehicle.trailFade < 1) {
        // Trail is fading out
        vehicle.trailFade += 1 / POOL_CONFIG.trailFadeFrames;
        if (vehicle.trailFade >= 1) {
          // Fade complete — enter cooldown
          vehicle.trailFade = -1;
          vehicle.progress = 0;
          vehicle.spawnDelay = randInt(
            POOL_CONFIG.cooldownMinFrames,
            POOL_CONFIG.cooldownMaxFrames
          );
        }
      } else {
        // Inactive vehicle counting down cooldown
        vehicle.spawnDelay--;
      }
    }
  }

  // Spawn inactive vehicles that are ready, up to the active cap
  for (const vehicle of vehicles) {
    if (activeCount >= POOL_CONFIG.maxActive) break;

    if (!vehicle.active && vehicle.trailFade < 0 && vehicle.spawnDelay <= 0) {
      vehicle.active = true;
      vehicle.progress = 0;
      vehicle.trailFade = -1;
      activeCount++;
    }
  }
}

/**
 * Get the trail line for a vehicle — a LineString from route start
 * up to the vehicle's current position.
 */
export function getVehicleTrail(vehicle: AnimatedVehicle): [number, number][] {
  const coords = vehicle.route.coordinates;
  const totalSegments = coords.length - 1;

  if (totalSegments <= 0 || vehicle.progress <= 0) {
    return [];
  }

  const trail: [number, number][] = [];
  const progressAlongRoute = vehicle.progress * totalSegments;
  const currentSegIndex = Math.min(
    Math.floor(progressAlongRoute),
    totalSegments - 1
  );
  const segT = progressAlongRoute - currentSegIndex;

  // Add all completed waypoints
  for (let i = 0; i <= currentSegIndex; i++) {
    trail.push(coords[i]);
  }

  // Add current interpolated position
  const a = coords[currentSegIndex];
  const b = coords[Math.min(currentSegIndex + 1, coords.length - 1)];
  trail.push(interpolate(a, b, segT));

  return trail;
}

// ─── GeoJSON Builders ───

/** Build a GeoJSON FeatureCollection of vehicle icon positions (active only) */
export function vehiclesToGeoJSON(
  vehicles: AnimatedVehicle[]
): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: vehicles
      .filter((v) => v.active && v.spawnDelay <= 0 && v.progress > 0)
      .map((vehicle) => {
        const { coordinates, bearing } = getVehiclePosition(vehicle);
        return {
          type: "Feature" as const,
          properties: {
            id: vehicle.route.id,
            type: vehicle.route.type,
            bearing,
          },
          geometry: {
            type: "Point" as const,
            coordinates,
          },
        };
      }),
  };
}

/** Build a GeoJSON FeatureCollection of vehicle trail lines (active + fading) */
export function vehicleTrailsToGeoJSON(
  vehicles: AnimatedVehicle[]
): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: vehicles
      .filter((v) => {
        // Include active vehicles with visible progress
        if (v.active && v.spawnDelay <= 0 && v.progress > 0) return true;
        // Include fading trails (vehicle finished but trail still visible)
        if (!v.active && v.trailFade >= 0 && v.trailFade < 1) return true;
        return false;
      })
      .map((vehicle) => {
        const trail = getVehicleTrail(vehicle);
        if (trail.length < 2) return null;

        // Compute opacity: 1.0 for active, decaying for fading
        const opacity = vehicle.trailFade >= 0
          ? Math.max(0, 1 - vehicle.trailFade)
          : 1.0;

        return {
          type: "Feature" as const,
          properties: {
            id: vehicle.route.id,
            type: vehicle.route.type,
            progress: vehicle.progress,
            opacity,
          },
          geometry: {
            type: "LineString" as const,
            coordinates: trail,
          },
        };
      })
      .filter(Boolean) as GeoJSON.Feature[],
  };
}
