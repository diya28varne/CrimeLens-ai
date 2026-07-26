import { apiFetch } from "@/shared/api/client";

export type GeoJsonFeatureCollection = {
  type: "FeatureCollection";
  features: Array<{
    type: "Feature";
    geometry: { type: "Point"; coordinates: [number, number] };
    properties: {
      id: string;
      offense_code: string;
      severity: string;
      occurred_at: string;
      station_id: string;
    };
  }>;
};

export async function fetchIncidentsGeoJson(params: {
  bbox?: string;
  lon?: number;
  lat?: number;
  radius_m?: number;
  from?: string;
  to?: string;
  signal?: AbortSignal;
}): Promise<GeoJsonFeatureCollection> {
  const query = new URLSearchParams();
  if (params.bbox) query.set("bbox", params.bbox);
  if (params.lon != null) query.set("lon", String(params.lon));
  if (params.lat != null) query.set("lat", String(params.lat));
  if (params.radius_m != null) query.set("radius_m", String(params.radius_m));
  if (params.from) query.set("from", params.from);
  if (params.to) query.set("to", params.to);
  query.set("limit", "2000");

  return apiFetch<GeoJsonFeatureCollection>(`/spatial/incidents?${query.toString()}`, {
    signal: params.signal,
  });
}
