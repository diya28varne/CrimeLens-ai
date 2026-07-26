"use client";

import { useMemo, useState } from "react";
import Map, { NavigationControl } from "react-map-gl/maplibre";
import { ScatterplotLayer } from "@deck.gl/layers";
import "maplibre-gl/dist/maplibre-gl.css";

import { BENGALURU_CENTER, MAP_STYLE } from "@/features/map/constants";
import type { SimulationPoint } from "@/features/simulation/api";
import { DeckGLOverlay } from "@/widgets/map-viewport/deck-overlay";

type Props = {
  points: SimulationPoint[];
  eventZone: {
    label: string;
    lon: number;
    lat: number;
    radius_km: number;
  } | null;
  showMode: "simulated" | "delta";
};

function deltaColor(delta: number): [number, number, number, number] {
  // Color-blind friendly: teal = risk down, orange = risk up
  if (delta > 0.02) return [230, 126, 34, 210];
  if (delta < -0.02) return [26, 188, 156, 210];
  return [149, 165, 166, 180];
}

function riskColor(risk: number): [number, number, number, number] {
  if (risk >= 0.75) return [192, 57, 43, 220];
  if (risk >= 0.55) return [230, 126, 34, 210];
  if (risk >= 0.35) return [241, 196, 15, 200];
  return [52, 152, 219, 190];
}

export function SimulationMap({ points, eventZone, showMode }: Props) {
  const [viewState, setViewState] = useState({
    longitude: BENGALURU_CENTER.longitude,
    latitude: BENGALURU_CENTER.latitude,
    zoom: BENGALURU_CENTER.zoom,
    pitch: 0,
    bearing: 0,
  });

  const layers = useMemo(() => {
    const data = points.map((p) => ({
      ...p,
      position: [p.lon, p.lat] as [number, number],
    }));

    const riskLayer = new ScatterplotLayer({
      id: "sim-risk",
      data,
      pickable: true,
      opacity: 0.85,
      stroked: true,
      filled: true,
      radiusUnits: "pixels",
      getPosition: (d: (typeof data)[number]) => d.position,
      getRadius: (d: (typeof data)[number]) =>
        showMode === "delta" ? 10 + Math.min(18, Math.abs(d.delta) * 80) : 8 + d.simulated_risk * 16,
      getFillColor: (d: (typeof data)[number]) =>
        showMode === "delta" ? deltaColor(d.delta) : riskColor(d.simulated_risk),
      getLineColor: [255, 255, 255, 60],
      lineWidthMinPixels: 1,
      updateTriggers: {
        getRadius: showMode,
        getFillColor: showMode,
      },
    });

    const zoneLayer =
      eventZone != null
        ? new ScatterplotLayer({
            id: "event-zone",
            data: [{ position: [eventZone.lon, eventZone.lat] as [number, number] }],
            stroked: true,
            filled: true,
            radiusUnits: "meters",
            getPosition: (d: { position: [number, number] }) => d.position,
            getRadius: Math.max(800, eventZone.radius_km * 1000),
            getFillColor: [61, 139, 253, 28],
            getLineColor: [61, 139, 253, 160],
            lineWidthMinPixels: 2,
          })
        : null;

    return zoneLayer ? [zoneLayer, riskLayer] : [riskLayer];
  }, [points, eventZone, showMode]);

  return (
    <div style={{ position: "relative", height: "100%", minHeight: 360, borderRadius: 10, overflow: "hidden" }}>
      <Map
        {...viewState}
        onMove={(e) => setViewState(e.viewState)}
        mapStyle={MAP_STYLE}
        style={{ width: "100%", height: "100%" }}
      >
        <NavigationControl position="top-right" />
        <DeckGLOverlay layers={layers} />
      </Map>
      <div
        style={{
          position: "absolute",
          left: 10,
          bottom: 10,
          background: "rgba(12, 18, 32, 0.88)",
          border: "1px solid var(--cl-border)",
          borderRadius: 8,
          padding: "8px 10px",
          fontSize: 11,
          color: "var(--cl-muted)",
          maxWidth: 220,
        }}
      >
        {showMode === "delta" ? (
          <>
            <div style={{ color: "#1abc9c" }}>● Risk down</div>
            <div style={{ color: "#e67e22" }}>● Risk up</div>
            <div>● Stable</div>
          </>
        ) : (
          <>
            <div>Simulated risk intensity</div>
            <div>Blue → amber → red</div>
          </>
        )}
        {eventZone ? <div style={{ marginTop: 4 }}>Zone: {eventZone.label}</div> : null}
      </div>
    </div>
  );
}
