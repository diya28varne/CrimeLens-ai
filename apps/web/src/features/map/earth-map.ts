import type { Map as MapLibreMap } from "maplibre-gl";

import type { MapViewMode } from "@/features/map/constants";

/** Camera presets — 3D uses a clear pitched perspective. */
export const CAMERA_BY_MODE: Record<
  MapViewMode,
  { pitch: number; bearing: number }
> = {
  "2d": { pitch: 0, bearing: 0 },
  "3d": { pitch: 60, bearing: -24 },
};

/** @deprecated Use CAMERA_BY_MODE["3d"] */
export const EARTH_CAMERA = {
  pitch: CAMERA_BY_MODE["3d"].pitch,
  bearing: CAMERA_BY_MODE["3d"].bearing,
  zoom: 13,
} as const;

export const TERRAIN_SOURCE_ID = "terrain-dem";
export const TERRAIN_EXAGGERATION_3D = 1.6;

export type ArcDatum = {
  sourcePosition: [number, number];
  targetPosition: [number, number];
  severity: string;
};

const SEVERITY_RANK: Record<string, number> = {
  critical: 4,
  high: 3,
  medium: 2,
  low: 1,
};

/** Sharpen satellite + label overlays for clearer imagery. */
export function enableEarthView(map: MapLibreMap): void {
  try {
    if (map.getLayer("satellite")) {
      map.setPaintProperty("satellite", "raster-opacity", 1);
      map.setPaintProperty("satellite", "raster-contrast", 0.12);
      map.setPaintProperty("satellite", "raster-saturation", 0.08);
      map.setPaintProperty("satellite", "raster-brightness-min", 0.05);
      map.setPaintProperty("satellite", "raster-brightness-max", 1);
    }
    if (map.getLayer("roads-overlay")) {
      map.setPaintProperty("roads-overlay", "raster-opacity", 1);
    }
    if (map.getLayer("places-overlay")) {
      map.setPaintProperty("places-overlay", "raster-opacity", 1);
    }
  } catch {
    // ignore paint tweaks if style differs
  }
}

function applyDimensionNow(map: MapLibreMap, mode: MapViewMode): void {
  enableEarthView(map);
  const is3d = mode === "3d";

  try {
    if (map.getLayer("hillshade")) {
      map.setLayoutProperty("hillshade", "visibility", is3d ? "visible" : "none");
    }
  } catch {
    // ignore
  }

  try {
    if (is3d && map.getSource(TERRAIN_SOURCE_ID)) {
      map.setTerrain({
        source: TERRAIN_SOURCE_ID,
        exaggeration: TERRAIN_EXAGGERATION_3D,
      });
    } else {
      map.setTerrain(null);
    }
  } catch {
    // Terrain optional
  }
}

/**
 * Apply terrain/hillshade safely outside MapLibre's current render pass.
 */
export function applyMapDimension(map: MapLibreMap, mode: MapViewMode): void {
  const run = () => {
    try {
      applyDimensionNow(map, mode);
    } catch {
      // ignore
    }
  };

  // Defer so we never nest into an active MapLibre render/task queue.
  if (typeof window !== "undefined") {
    window.setTimeout(run, 0);
  } else {
    run();
  }
}

export function disableEarthTerrain(map: MapLibreMap): void {
  try {
    map.setTerrain(null);
  } catch {
    // ignore
  }
}

/**
 * Build glowing link arcs between nearby higher-severity incidents.
 */
export function buildIncidentArcs<T extends { position: [number, number]; severity: string }>(
  points: T[],
  maxArcs = 28,
): ArcDatum[] {
  if (points.length < 2) return [];

  const ranked = [...points].sort(
    (a, b) => (SEVERITY_RANK[b.severity] ?? 0) - (SEVERITY_RANK[a.severity] ?? 0),
  );
  const hubs = ranked.slice(0, Math.min(10, ranked.length));
  const arcs: ArcDatum[] = [];
  const seen = new Set<string>();

  for (const hub of hubs) {
    const neighbors = ranked
      .filter((p) => p !== hub)
      .map((p) => ({
        point: p,
        dist:
          (p.position[0] - hub.position[0]) ** 2 + (p.position[1] - hub.position[1]) ** 2,
      }))
      .sort((a, b) => a.dist - b.dist)
      .slice(0, 3);

    for (const { point } of neighbors) {
      const key = [hub.position.join(","), point.position.join(",")].sort().join("|");
      if (seen.has(key)) continue;
      seen.add(key);
      arcs.push({
        sourcePosition: hub.position,
        targetPosition: point.position,
        severity: hub.severity,
      });
      if (arcs.length >= maxArcs) return arcs;
    }
  }

  return arcs;
}
