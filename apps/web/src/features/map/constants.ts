export type MapLayerMode = "points" | "heatmap" | "both";

export type SeverityFilter = "all" | "low" | "medium" | "high" | "critical";

export const BENGALURU_CENTER = {
  longitude: 77.5946,
  latitude: 12.9716,
  zoom: 11.5,
} as const;

export const MAP_STYLE =
  process.env.NEXT_PUBLIC_MAP_STYLE_URL ??
  "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";

export const SEVERITY_COLOR: Record<string, [number, number, number]> = {
  low: [90, 200, 250],
  medium: [255, 204, 0],
  high: [255, 149, 0],
  critical: [255, 69, 58],
};
