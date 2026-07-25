"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Map, { NavigationControl, type MapRef, type ViewStateChangeEvent } from "react-map-gl/maplibre";
import { HeatmapLayer } from "@deck.gl/aggregation-layers";
import { ScatterplotLayer } from "@deck.gl/layers";
import type { PickingInfo } from "@deck.gl/core";
import "maplibre-gl/dist/maplibre-gl.css";

import {
  fetchIncidentsGeoJson,
  type GeoJsonFeatureCollection,
} from "@/features/map/api";
import {
  BENGALURU_CENTER,
  MAP_STYLE,
  SEVERITY_COLOR,
  type MapLayerMode,
  type SeverityFilter,
} from "@/features/map/constants";
import { DeckGLOverlay } from "@/widgets/map-viewport/deck-overlay";
import { ApiError } from "@/shared/api/client";

type IncidentPoint = {
  position: [number, number];
  id: string;
  offense_code: string;
  severity: string;
  occurred_at: string;
};

function boundsToBbox(map: MapRef): string {
  const b = map.getBounds();
  const west = b.getWest();
  const south = b.getSouth();
  const east = b.getEast();
  const north = b.getNorth();
  return `${west},${south},${east},${north}`;
}

function toPoints(fc: GeoJsonFeatureCollection): IncidentPoint[] {
  return fc.features.map((f) => ({
    position: f.geometry.coordinates,
    id: f.properties.id,
    offense_code: f.properties.offense_code,
    severity: f.properties.severity,
    occurred_at: f.properties.occurred_at,
  }));
}

type CrimeMapViewportProps = {
  layerMode: MapLayerMode;
  severity: SeverityFilter;
};

export function CrimeMapViewport({ layerMode, severity }: CrimeMapViewportProps) {
  const [viewState, setViewState] = useState<{
    longitude: number;
    latitude: number;
    zoom: number;
    pitch: number;
    bearing: number;
  }>({
    longitude: BENGALURU_CENTER.longitude,
    latitude: BENGALURU_CENTER.latitude,
    zoom: BENGALURU_CENTER.zoom,
    pitch: 0,
    bearing: 0,
  });
  const [mapRef, setMapRef] = useState<MapRef | null>(null);
  const [points, setPoints] = useState<IncidentPoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<IncidentPoint | null>(null);

  const load = useCallback(async () => {
    if (!mapRef) return;
    setLoading(true);
    setError(null);
    try {
      const bbox = boundsToBbox(mapRef);
      const fc = await fetchIncidentsGeoJson({ bbox });
      setPoints(toPoints(fc));
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError("Sign in required — open /login with seeded admin credentials.");
      } else {
        setError(err instanceof Error ? err.message : "Failed to load incidents");
      }
      setPoints([]);
    } finally {
      setLoading(false);
    }
  }, [mapRef]);

  useEffect(() => {
    void load();
  }, [load]);

  const filtered = useMemo(() => {
    if (severity === "all") return points;
    return points.filter((p) => p.severity === severity);
  }, [points, severity]);

  const layers = useMemo(() => {
    const result = [];
    if (layerMode === "heatmap" || layerMode === "both") {
      result.push(
        new HeatmapLayer<IncidentPoint>({
          id: "incident-heatmap",
          data: filtered,
          getPosition: (d) => d.position,
          getWeight: (d) =>
            d.severity === "critical" ? 4 : d.severity === "high" ? 3 : d.severity === "medium" ? 2 : 1,
          radiusPixels: 40,
          intensity: 1,
          threshold: 0.05,
        }),
      );
    }
    if (layerMode === "points" || layerMode === "both") {
      result.push(
        new ScatterplotLayer<IncidentPoint>({
          id: "incident-points",
          data: filtered,
          pickable: true,
          opacity: 0.9,
          stroked: true,
          filled: true,
          radiusScale: 1,
          radiusMinPixels: 5,
          radiusMaxPixels: 14,
          lineWidthMinPixels: 1,
          getPosition: (d) => d.position,
          getFillColor: (d) => SEVERITY_COLOR[d.severity] ?? [200, 200, 200],
          getLineColor: [12, 18, 32],
          onClick: (info: PickingInfo<IncidentPoint>) => {
            if (info.object) setSelected(info.object);
          },
        }),
      );
    }
    return result;
  }, [filtered, layerMode]);

  function onMoveEnd(evt: ViewStateChangeEvent) {
    setViewState(evt.viewState);
    // debounce via microtask after map settles
    window.setTimeout(() => {
      void load();
    }, 250);
  }

  return (
    <div style={{ position: "relative", height: "100%", minHeight: 520, borderRadius: 12, overflow: "hidden", border: "1px solid var(--cl-border)" }}>
      <Map
        ref={setMapRef}
        {...viewState}
        onMove={(evt) => setViewState(evt.viewState)}
        onMoveEnd={onMoveEnd}
        mapStyle={MAP_STYLE}
        style={{ width: "100%", height: "100%" }}
      >
        <NavigationControl position="top-right" />
        <DeckGLOverlay layers={layers} interleaved />
      </Map>

      <div
        style={{
          position: "absolute",
          left: 12,
          top: 12,
          display: "flex",
          gap: 8,
          alignItems: "center",
          background: "rgba(11, 18, 32, 0.88)",
          border: "1px solid var(--cl-border)",
          borderRadius: 8,
          padding: "8px 10px",
          fontSize: 12,
        }}
      >
        <span style={{ color: "var(--cl-muted)" }}>
          {loading ? "Loading…" : `${filtered.length} incidents in view`}
        </span>
        <button
          type="button"
          onClick={() => void load()}
          style={{
            background: "transparent",
            color: "var(--cl-accent)",
            border: "1px solid var(--cl-border)",
            borderRadius: 6,
            padding: "4px 8px",
            cursor: "pointer",
          }}
        >
          Refresh
        </button>
      </div>

      {error ? (
        <div
          style={{
            position: "absolute",
            left: 12,
            bottom: 12,
            right: 12,
            background: "rgba(80, 20, 20, 0.92)",
            border: "1px solid #ff8e8e",
            color: "#ffd7d7",
            borderRadius: 8,
            padding: "10px 12px",
            fontSize: 13,
          }}
        >
          {error}
        </div>
      ) : null}

      {selected ? (
        <aside
          style={{
            position: "absolute",
            right: 12,
            top: 56,
            width: 260,
            background: "rgba(18, 26, 43, 0.95)",
            border: "1px solid var(--cl-border)",
            borderRadius: 10,
            padding: 12,
            fontSize: 13,
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
            <strong>{selected.offense_code}</strong>
            <button
              type="button"
              onClick={() => setSelected(null)}
              style={{ background: "transparent", border: 0, color: "var(--cl-muted)", cursor: "pointer" }}
            >
              Close
            </button>
          </div>
          <p style={{ margin: "8px 0 0", color: "var(--cl-muted)" }}>
            Severity: {selected.severity}
            <br />
            Occurred: {new Date(selected.occurred_at).toLocaleString()}
          </p>
        </aside>
      ) : null}
    </div>
  );
}
