"use client";

import dynamic from "next/dynamic";
import { useState, type CSSProperties } from "react";
import { useTranslation } from "react-i18next";

import type { MapLayerMode, SeverityFilter } from "@/features/map/constants";

const CrimeMapViewport = dynamic(
  () =>
    import("@/widgets/map-viewport/CrimeMapViewport").then((m) => m.CrimeMapViewport),
  {
    ssr: false,
    loading: () => (
      <div
        style={{
          minHeight: 520,
          display: "grid",
          placeItems: "center",
          border: "1px solid var(--cl-border)",
          borderRadius: 12,
          color: "var(--cl-muted)",
        }}
      >
        …
      </div>
    ),
  },
);

export function CrimeMapPanel() {
  const { t } = useTranslation("ai");
  const [layerMode, setLayerMode] = useState<MapLayerMode>("both");
  const [severity, setSeverity] = useState<SeverityFilter>("all");

  return (
    <div style={{ display: "grid", gap: 12, height: "calc(100vh - 3rem)" }}>
      <header style={{ display: "flex", flexWrap: "wrap", gap: 12, alignItems: "end" }}>
        <div style={{ flex: 1, minWidth: 220 }}>
          <h1 style={{ margin: 0 }}>{t("map.title")}</h1>
          <p style={{ margin: "6px 0 0", color: "var(--cl-muted)", fontSize: 14 }}>
            {t("map.subtitle")}
          </p>
        </div>
        <label style={{ display: "grid", gap: 4, fontSize: 12, color: "var(--cl-muted)" }}>
          {t("map.layers")}
          <select
            value={layerMode}
            onChange={(e) => setLayerMode(e.target.value as MapLayerMode)}
            style={selectStyle}
          >
            <option value="both">{t("map.points")} + {t("map.heatmap")}</option>
            <option value="points">{t("map.points")}</option>
            <option value="heatmap">{t("map.heatmap")}</option>
          </select>
        </label>
        <label style={{ display: "grid", gap: 4, fontSize: 12, color: "var(--cl-muted)" }}>
          {t("map.filters")}
          <select
            value={severity}
            onChange={(e) => setSeverity(e.target.value as SeverityFilter)}
            style={selectStyle}
          >
            <option value="all">All</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
        </label>
      </header>

      <div style={{ flex: 1, minHeight: 0 }}>
        <CrimeMapViewport layerMode={layerMode} severity={severity} />
      </div>

      <footer style={{ display: "flex", gap: 14, flexWrap: "wrap", fontSize: 12, color: "var(--cl-muted)" }}>
        <LegendSwatch color="rgb(30, 136, 229)" label={t("map.legend") + ": Low"} />
        <LegendSwatch color="rgb(255, 193, 7)" label="Medium" />
        <LegendSwatch color="rgb(255, 111, 0)" label="High" />
        <LegendSwatch color="rgb(229, 57, 53)" label="Critical" />
      </footer>
    </div>
  );
}

function LegendSwatch({ color, label }: { color: string; label: string }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
      <span style={{ width: 10, height: 10, borderRadius: 999, background: color }} />
      {label}
    </span>
  );
}

const selectStyle: CSSProperties = {
  background: "var(--cl-surface)",
  color: "var(--cl-text)",
  border: "1px solid var(--cl-border)",
  borderRadius: 8,
  padding: "8px 10px",
  minWidth: 160,
};
