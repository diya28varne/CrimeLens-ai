"use client";

import dynamic from "next/dynamic";
import {
  startTransition,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
} from "react";
import Map, {
  NavigationControl,
  ScaleControl,
  type MapRef,
} from "react-map-gl/maplibre";
import type { Map as MapLibreMap } from "maplibre-gl";
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
  GLOW_COLOR,
  MAP_STYLE,
  MARKER_RING_COLOR,
  SEVERITY_COLOR,
  type MapLayerMode,
  type MapViewMode,
  type SeverityFilter,
} from "@/features/map/constants";
import { CAMERA_BY_MODE, applyMapDimension } from "@/features/map/earth-map";
import { createDebouncedRunner, normalizeBbox } from "@/features/map/perf";
import { DeckGLOverlay } from "@/widgets/map-viewport/deck-overlay";
import { ApiError } from "@/shared/api/client";

const GoogleHybridCrimeMap = dynamic(
  () =>
    import("@/widgets/map-viewport/GoogleHybridCrimeMap").then((m) => m.GoogleHybridCrimeMap),
  {
    ssr: false,
    loading: () => (
      <div
        style={{
          minHeight: 520,
          display: "grid",
          placeItems: "center",
          border: "1px solid #dadce0",
          borderRadius: 12,
          color: "#5f6368",
          background: "#e8eaed",
        }}
      >
        Loading map…
      </div>
    ),
  },
);

type IncidentPoint = {
  position: [number, number];
  id: string;
  offense_code: string;
  severity: string;
  occurred_at: string;
};

function boundsToBbox(map: MapRef | MapLibreMap): string {
  const b = "getBounds" in map && map.getBounds ? map.getBounds() : null;
  if (!b) return "";
  return `${b.getWest()},${b.getSouth()},${b.getEast()},${b.getNorth()}`;
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

const chromeBtn = (active: boolean): CSSProperties => ({
  background: active ? "#fff" : "#f1f3f4",
  color: active ? "#1a73e8" : "#3c4043",
  border: "1px solid #dadce0",
  borderRadius: 8,
  padding: "8px 12px",
  cursor: "pointer",
  fontSize: 13,
  fontWeight: 600,
  boxShadow: active ? "0 1px 2px rgba(60,64,67,.3)" : "none",
});

function MapLibreSatelliteHybrid({ layerMode, severity }: CrimeMapViewportProps) {
  const [viewMode, setViewMode] = useState<MapViewMode>("2d");
  const [viewState, setViewState] = useState({
    longitude: BENGALURU_CENTER.longitude,
    latitude: BENGALURU_CENTER.latitude,
    zoom: BENGALURU_CENTER.zoom,
    pitch: CAMERA_BY_MODE["2d"].pitch,
    bearing: CAMERA_BY_MODE["2d"].bearing,
  });
  const [mapRef, setMapRef] = useState<MapRef | null>(null);
  const [points, setPoints] = useState<IncidentPoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<IncidentPoint | null>(null);

  const viewModeRef = useRef<MapViewMode>(viewMode);
  const mapInstanceRef = useRef<MapLibreMap | null>(null);
  const lastBboxRef = useRef<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const debounceRef = useRef(createDebouncedRunner(320));
  const moveRafRef = useRef<number>(0);
  const pendingViewRef = useRef(viewState);

  viewModeRef.current = viewMode;
  pendingViewRef.current = viewState;

  const is3d = viewMode === "3d";

  const load = useCallback(async (opts?: { showLoading?: boolean; force?: boolean }) => {
    const map = mapInstanceRef.current ?? mapRef?.getMap() ?? null;
    if (!map) return;

    const rawBbox = boundsToBbox(map);
    if (!rawBbox) return;
    const bbox = normalizeBbox(rawBbox);
    if (!opts?.force && lastBboxRef.current === bbox) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    if (opts?.showLoading) setLoading(true);
    setError(null);
    try {
      const fc = await fetchIncidentsGeoJson({ bbox: rawBbox, signal: controller.signal });
      if (controller.signal.aborted) return;
      lastBboxRef.current = bbox;
      startTransition(() => {
        setPoints(toPoints(fc));
      });
    } catch (err) {
      if (controller.signal.aborted) return;
      if (err instanceof DOMException && err.name === "AbortError") return;
      if (err instanceof ApiError && err.status === 401) {
        setError("Sign in required — open /login with seeded admin credentials.");
      } else {
        setError(err instanceof Error ? err.message : "Failed to load incidents");
      }
      startTransition(() => setPoints([]));
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, [mapRef]);

  const scheduleLoad = useCallback(
    (immediate = false, showLoading = false) => {
      debounceRef.current.run(() => {
        void load({ showLoading, force: immediate });
      }, immediate);
    },
    [load],
  );

  useEffect(() => {
    const debounced = debounceRef.current;
    return () => {
      debounced.cancel();
      abortRef.current?.abort();
    };
  }, []);

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
      const markerProps = {
        data: filtered,
        getPosition: (d: IncidentPoint) => d.position,
        radiusUnits: "pixels" as const,
        billboard: true,
        parameters: { depthTest: false },
      };

      result.push(
        new ScatterplotLayer<IncidentPoint>({
          id: "incident-halo",
          ...markerProps,
          pickable: false,
          stroked: false,
          filled: true,
          getRadius: 18,
          radiusMinPixels: 16,
          radiusMaxPixels: 24,
          getFillColor: GLOW_COLOR,
        }),
      );
      result.push(
        new ScatterplotLayer<IncidentPoint>({
          id: "incident-ring",
          ...markerProps,
          pickable: false,
          stroked: false,
          filled: true,
          getRadius: 11,
          radiusMinPixels: 10,
          radiusMaxPixels: 14,
          getFillColor: MARKER_RING_COLOR,
        }),
      );
      result.push(
        new ScatterplotLayer<IncidentPoint>({
          id: "incident-points",
          ...markerProps,
          pickable: true,
          stroked: true,
          filled: true,
          getRadius: 8,
          radiusMinPixels: 7,
          radiusMaxPixels: 11,
          lineWidthUnits: "pixels",
          lineWidthMinPixels: 2.5,
          getLineWidth: 2.5,
          getFillColor: (d) => SEVERITY_COLOR[d.severity] ?? [30, 136, 229],
          getLineColor: [255, 255, 255, 255],
          onClick: (info: PickingInfo<IncidentPoint>) => {
            if (info.object) setSelected(info.object);
          },
        }),
      );
    }

    return result;
  }, [filtered, layerMode]);

  function applyViewMode(mode: MapViewMode) {
    setViewMode(mode);
    const cam = CAMERA_BY_MODE[mode];
    // Drive camera only through React viewState — avoid map.easeTo/jumpTo while
    // react-map-gl is also syncing (causes MapLibre "already running" crashes).
    setViewState((prev) => {
      const next = {
        ...prev,
        pitch: cam.pitch,
        bearing: cam.bearing,
        zoom: mode === "3d" ? Math.max(prev.zoom, 12.5) : prev.zoom,
      };
      pendingViewRef.current = next;
      return next;
    });
  }

  useEffect(() => {
    if (!mapRef) return;
    const map = mapRef.getMap();
    if (!map) return;

    mapInstanceRef.current = map;

    const onStyleLoad = () => {
      applyMapDimension(map, viewModeRef.current);
    };

    map.on("style.load", onStyleLoad);
    if (map.isStyleLoaded()) {
      applyMapDimension(map, viewModeRef.current);
    }

    return () => {
      map.off("style.load", onStyleLoad);
      if (mapInstanceRef.current === map) mapInstanceRef.current = null;
    };
  }, [mapRef]);

  useEffect(() => {
    const map = mapInstanceRef.current ?? mapRef?.getMap() ?? null;
    if (!map || !map.isStyleLoaded()) return;
    applyMapDimension(map, viewMode);
  }, [viewMode, mapRef]);

  useEffect(() => {
    return () => {
      if (moveRafRef.current) cancelAnimationFrame(moveRafRef.current);
    };
  }, []);

  return (
    <div
      style={{
        position: "relative",
        height: "100%",
        minHeight: 520,
        borderRadius: 12,
        overflow: "hidden",
        border: "1px solid #dadce0",
        background: "#e8eaed",
      }}
    >
      <Map
        ref={setMapRef}
        {...viewState}
        onMove={(evt) => {
          pendingViewRef.current = evt.viewState;
          if (moveRafRef.current) return;
          moveRafRef.current = requestAnimationFrame(() => {
            moveRafRef.current = 0;
            setViewState(pendingViewRef.current);
          });
        }}
        onMoveEnd={(evt) => {
          if (moveRafRef.current) {
            cancelAnimationFrame(moveRafRef.current);
            moveRafRef.current = 0;
          }
          pendingViewRef.current = evt.viewState;
          setViewState(evt.viewState);
          scheduleLoad(false, false);
        }}
        onLoad={(evt) => {
          const map = evt.target;
          mapInstanceRef.current = map;
          applyMapDimension(map, viewModeRef.current);
          scheduleLoad(true, true);
        }}
        mapStyle={MAP_STYLE}
        style={{ width: "100%", height: "100%" }}
        maxPitch={85}
        minZoom={2}
        maxZoom={19}
        dragRotate={is3d}
        touchPitch={is3d}
        pitchWithRotate={is3d}
        reuseMaps={false}
      >
        <NavigationControl position="bottom-right" visualizePitch={is3d} showCompass />
        <ScaleControl position="bottom-left" maxWidth={120} unit="metric" />
        <DeckGLOverlay layers={layers} interleaved />
      </Map>

      <div
        style={{
          position: "absolute",
          left: 12,
          top: 12,
          zIndex: 5,
          display: "flex",
          gap: 8,
          alignItems: "center",
          flexWrap: "wrap",
          background: "#fff",
          borderRadius: 8,
          padding: "8px 10px",
          boxShadow: "0 1px 3px rgba(60,64,67,.3)",
          fontSize: 13,
          color: "#3c4043",
        }}
      >
        <span>{loading ? "Loading…" : `${filtered.length} incidents in view`}</span>
        <div
          style={{
            display: "flex",
            background: "#f1f3f4",
            borderRadius: 8,
            overflow: "hidden",
            border: "1px solid #dadce0",
          }}
          role="group"
          aria-label="Map view mode"
        >
          <button
            type="button"
            style={{ ...chromeBtn(viewMode === "2d"), borderRadius: 0, border: 0, boxShadow: "none" }}
            onClick={() => applyViewMode("2d")}
          >
            2D
          </button>
          <button
            type="button"
            style={{
              ...chromeBtn(viewMode === "3d"),
              borderRadius: 0,
              border: 0,
              borderLeft: "1px solid #dadce0",
              boxShadow: "none",
            }}
            onClick={() => applyViewMode("3d")}
          >
            3D
          </button>
        </div>
        <button
          type="button"
          style={chromeBtn(false)}
          onClick={() => {
            lastBboxRef.current = null;
            scheduleLoad(true, true);
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
            bottom: 36,
            right: 12,
            zIndex: 5,
            background: "#fce8e6",
            border: "1px solid #f28b82",
            color: "#c5221f",
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
            left: 12,
            top: 64,
            width: 280,
            zIndex: 5,
            background: "#fff",
            borderRadius: 8,
            padding: 14,
            boxShadow: "0 1px 3px rgba(60,64,67,.3)",
            fontSize: 13,
            color: "#202124",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
            <strong>{selected.offense_code}</strong>
            <button
              type="button"
              onClick={() => setSelected(null)}
              style={{ background: "transparent", border: 0, color: "#5f6368", cursor: "pointer", fontSize: 16 }}
            >
              ×
            </button>
          </div>
          <p style={{ margin: "8px 0 0", color: "#5f6368" }}>
            Severity: {selected.severity}
            <br />
            Occurred: {new Date(selected.occurred_at).toLocaleString()}
          </p>
        </aside>
      ) : null}
    </div>
  );
}

export function CrimeMapViewport({ layerMode, severity }: CrimeMapViewportProps) {
  const googleKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY?.trim();

  if (googleKey) {
    return <GoogleHybridCrimeMap apiKey={googleKey} layerMode={layerMode} severity={severity} />;
  }

  return <MapLibreSatelliteHybrid layerMode={layerMode} severity={severity} />;
}
