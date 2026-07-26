"use client";

import {
  startTransition,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
} from "react";
import {
  APIProvider,
  Map as GoogleMap,
  Marker,
  useMap,
} from "@vis.gl/react-google-maps";

import {
  fetchIncidentsGeoJson,
  type GeoJsonFeatureCollection,
} from "@/features/map/api";
import {
  BENGALURU_CENTER,
  type MapLayerMode,
  type MapViewMode,
  type SeverityFilter,
} from "@/features/map/constants";
import { createDebouncedRunner, normalizeBbox } from "@/features/map/perf";
import { ApiError } from "@/shared/api/client";
import { useTranslation } from "react-i18next";

export type IncidentPoint = {
  position: [number, number];
  id: string;
  offense_code: string;
  severity: string;
  occurred_at: string;
};

function toPoints(fc: GeoJsonFeatureCollection): IncidentPoint[] {
  return fc.features.map((f) => ({
    position: f.geometry.coordinates,
    id: f.properties.id,
    offense_code: f.properties.offense_code,
    severity: f.properties.severity,
    occurred_at: f.properties.occurred_at,
  }));
}

const PIN_CACHE = new Map<string, string>();

function pinDataUrl(severity: string): string {
  const cached = PIN_CACHE.get(severity);
  if (cached) return cached;

  const fill =
    severity === "critical"
      ? "#e53935"
      : severity === "high"
        ? "#ff6f00"
        : severity === "medium"
          ? "#ffc107"
          : "#1e88e5";
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="36" height="48" viewBox="0 0 36 48">
      <ellipse cx="18" cy="46" rx="7" ry="2.5" fill="rgba(0,0,0,0.35)"/>
      <path fill="${fill}" stroke="#ffffff" stroke-width="2.5"
        d="M18 1.5C9.4 1.5 2.5 8.4 2.5 17c0 11.2 15.5 28.5 15.5 28.5S33.5 28.2 33.5 17C33.5 8.4 26.6 1.5 18 1.5z"/>
      <circle cx="18" cy="17" r="6" fill="#ffffff"/>
      <circle cx="18" cy="17" r="3.2" fill="${fill}"/>
    </svg>`;
  const url = `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
  PIN_CACHE.set(severity, url);
  return url;
}

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

type InnerProps = {
  layerMode: MapLayerMode;
  severity: SeverityFilter;
  viewMode: MapViewMode;
  onViewModeChange: (mode: MapViewMode) => void;
};

function GoogleHybridInner({ layerMode, severity, viewMode, onViewModeChange }: InnerProps) {
  const { t } = useTranslation("ai");
  const { t: tc } = useTranslation("common");
  const map = useMap();
  const [points, setPoints] = useState<IncidentPoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<IncidentPoint | null>(null);

  const lastBboxRef = useRef<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const debounceRef = useRef(createDebouncedRunner(320));

  const load = useCallback(
    async (opts?: { showLoading?: boolean; force?: boolean }) => {
      if (!map) return;
      const bounds = map.getBounds();
      if (!bounds) return;
      const ne = bounds.getNorthEast();
      const sw = bounds.getSouthWest();
      const rawBbox = `${sw.lng()},${sw.lat()},${ne.lng()},${ne.lat()}`;
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
        startTransition(() => setPoints(toPoints(fc)));
      } catch (err) {
        if (controller.signal.aborted) return;
        if (err instanceof DOMException && err.name === "AbortError") return;
        if (err instanceof ApiError && err.status === 401) {
          setError(tc("signInRequired"));
        } else {
          setError(err instanceof Error ? err.message : t("map.errorIncidents"));
        }
        startTransition(() => setPoints([]));
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    },
    [map, t, tc],
  );

  const scheduleLoad = useCallback(
    (immediate = false, showLoading = false) => {
      debounceRef.current.run(() => {
        void load({ showLoading, force: immediate });
      }, immediate);
    },
    [load],
  );

  useEffect(() => {
    if (!map) return;
    scheduleLoad(true, true);
    const listener = map.addListener("idle", () => scheduleLoad(false, false));
    return () => {
      listener.remove();
      debounceRef.current.cancel();
      abortRef.current?.abort();
    };
  }, [map, scheduleLoad]);

  useEffect(() => {
    if (!map) return;
    // Apply after the Maps API has settled the current frame.
    const id = window.setTimeout(() => {
      if (viewMode === "3d") {
        map.setOptions({ rotateControl: true });
        map.setTilt(67.5);
        map.setHeading(-28);
      } else {
        map.setTilt(0);
        map.setHeading(0);
        map.setOptions({ rotateControl: false });
      }
    }, 0);
    return () => window.clearTimeout(id);
  }, [map, viewMode]);

  const filtered = useMemo(() => {
    if (severity === "all") return points;
    return points.filter((p) => p.severity === severity);
  }, [points, severity]);

  const showPoints = layerMode === "points" || layerMode === "both";

  return (
    <>
      {showPoints
        ? filtered.map((p) => (
            <Marker
              key={p.id}
              position={{ lat: p.position[1], lng: p.position[0] }}
              title={`${p.offense_code} (${p.severity})`}
              icon={pinDataUrl(p.severity)}
              onClick={() => setSelected(p)}
            />
          ))
        : null}

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
        <span>{loading ? tc("loading") : t("map.incidentsInView", { count: filtered.length })}</span>
        <div
          style={{
            display: "flex",
            background: "#f1f3f4",
            borderRadius: 8,
            overflow: "hidden",
            border: "1px solid #dadce0",
          }}
          role="group"
          aria-label={t("map.viewMode")}
        >
          <button
            type="button"
            style={{ ...chromeBtn(viewMode === "2d"), borderRadius: 0, border: 0, boxShadow: "none" }}
            onClick={() => onViewModeChange("2d")}
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
            onClick={() => onViewModeChange("3d")}
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
          {t("map.refresh")}
        </button>
      </div>

      {error ? (
        <div
          style={{
            position: "absolute",
            left: 12,
            bottom: 24,
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
              style={{
                background: "transparent",
                border: 0,
                color: "#5f6368",
                cursor: "pointer",
                fontSize: 16,
              }}
            >
              {tc("close")}
            </button>
          </div>
          <p style={{ margin: "8px 0 0", color: "#5f6368" }}>
            {t("map.popupSeverity")} {selected.severity}
            <br />
            {t("map.popupOccurred")} {new Date(selected.occurred_at).toLocaleString()}
          </p>
        </aside>
      ) : null}
    </>
  );
}

type Props = {
  apiKey: string;
  layerMode: MapLayerMode;
  severity: SeverityFilter;
};

export function GoogleHybridCrimeMap({ apiKey, layerMode, severity }: Props) {
  const [viewMode, setViewMode] = useState<MapViewMode>("2d");

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
      <APIProvider apiKey={apiKey}>
        <GoogleMap
          defaultCenter={{
            lat: BENGALURU_CENTER.latitude,
            lng: BENGALURU_CENTER.longitude,
          }}
          defaultZoom={13}
          mapTypeId="hybrid"
          gestureHandling="greedy"
          zoomControl
          mapTypeControl
          streetViewControl={false}
          fullscreenControl
          rotateControl={viewMode === "3d"}
          tilt={viewMode === "3d" ? 67.5 : 0}
          heading={viewMode === "3d" ? -28 : 0}
          style={{ width: "100%", height: "100%" }}
          reuseMaps
        >
          <GoogleHybridInner
            layerMode={layerMode}
            severity={severity}
            viewMode={viewMode}
            onViewModeChange={setViewMode}
          />
        </GoogleMap>
      </APIProvider>
    </div>
  );
}
