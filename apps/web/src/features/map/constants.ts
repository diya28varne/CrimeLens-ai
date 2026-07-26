export type MapLayerMode = "points" | "heatmap" | "both";

export type SeverityFilter = "all" | "low" | "medium" | "high" | "critical";

export type MapViewMode = "2d" | "3d";

export const BENGALURU_CENTER: {
  longitude: number;
  latitude: number;
  zoom: number;
} = {
  longitude: 77.5946,
  latitude: 12.9716,
  zoom: 13,
};

/** Satellite + roads + place labels (Google Maps hybrid–style fallback). */
export const EARTH_MAP_STYLE = "/map-styles/satellite-hybrid.json";

export const MAP_STYLE =
  process.env.NEXT_PUBLIC_MAP_STYLE_URL &&
  process.env.NEXT_PUBLIC_MAP_STYLE_URL.trim().length > 0
    ? process.env.NEXT_PUBLIC_MAP_STYLE_URL
    : EARTH_MAP_STYLE;

/** High-contrast marker colors for satellite imagery. */
export const SEVERITY_COLOR: Record<string, [number, number, number]> = {
  low: [30, 136, 229],
  medium: [255, 193, 7],
  high: [255, 111, 0],
  critical: [229, 57, 53],
};

export const ARC_COLOR: [number, number, number, number] = [26, 115, 232, 160];
/** Soft white halo behind markers for contrast on dark/light satellite tiles. */
export const GLOW_COLOR: [number, number, number, number] = [255, 255, 255, 200];
export const MARKER_RING_COLOR: [number, number, number, number] = [15, 23, 42, 230];
