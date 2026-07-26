"use client";

import Link from "next/link";
import { useEffect, useState, type CSSProperties, type ReactNode } from "react";
import type { EChartsOption } from "echarts";
import { useTranslation } from "react-i18next";

import {
  fetchCurrentPredictions,
  fetchExplanation,
  fetchHotspots,
  fetchModels,
  type Explanation,
  type HotspotFeature,
  type PredictionRun,
  type PredictionValue,
} from "@/features/prediction/api";
import { Chart } from "@/shared/ui/Chart";
import { useAppLocale } from "@/shared/i18n/useAppLocale";

export function PredictionPanel() {
  const { t } = useTranslation("ai");
  const { t: tc } = useTranslation("common");
  const locale = useAppLocale();
  const [run, setRun] = useState<PredictionRun | null>(null);
  const [values, setValues] = useState<PredictionValue[]>([]);
  const [hotspots, setHotspots] = useState<HotspotFeature[]>([]);
  const [hotspotMethod, setHotspotMethod] = useState<string | null>(null);
  const [models, setModels] = useState<
    Array<{ model_code: string; model_version: string; status: string; algorithm: string }>
  >([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [expl, setExpl] = useState<Explanation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const [pred, hs, mods] = await Promise.all([
          fetchCurrentPredictions(),
          fetchHotspots(),
          fetchModels(),
        ]);
        if (cancelled) return;
        setRun(pred.data.run);
        setValues(pred.data.values);
        setHotspots(hs.data.features);
        setHotspotMethod(hs.data.run?.method ?? null);
        setModels(mods.data);
        if (pred.data.values[0]) setSelected(pred.data.values[0].id);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : t("prediction.errorLoad"));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [locale, t]);

  useEffect(() => {
    if (!selected) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await fetchExplanation(selected);
        if (!cancelled) setExpl(res.data);
      } catch {
        if (!cancelled) setExpl(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selected]);

  const riskOption: EChartsOption = {
    tooltip: { trigger: "axis" },
    grid: { left: 120, right: 24, top: 16, bottom: 28 },
    xAxis: {
      type: "value",
      max: 1,
      splitLine: { lineStyle: { color: "#243049" } },
      axisLabel: { color: "#9aa8c7" },
    },
    yAxis: {
      type: "category",
      data: values
        .map((v) => String(v.properties.station_name ?? v.properties.station_code ?? tc("station")))
        .reverse(),
      axisLabel: { color: "#9aa8c7", width: 110, overflow: "truncate" },
    },
    series: [
      {
        type: "bar",
        data: values.map((v) => v.value).reverse(),
        itemStyle: { color: "#ff9500", borderRadius: [0, 4, 4, 0] },
      },
    ],
  };

  const shapOption: EChartsOption | null = expl
    ? {
        tooltip: { trigger: "axis" },
        grid: { left: 120, right: 24, top: 16, bottom: 28 },
        xAxis: {
          type: "value",
          splitLine: { lineStyle: { color: "#243049" } },
          axisLabel: { color: "#9aa8c7" },
        },
        yAxis: {
          type: "category",
          data: expl.local_contributions.map((c) => c.feature).reverse(),
          axisLabel: { color: "#9aa8c7" },
        },
        series: [
          {
            type: "bar",
            data: expl.local_contributions.map((c) => c.contribution).reverse(),
            itemStyle: { color: "#3d8bfd", borderRadius: [0, 4, 4, 0] },
          },
        ],
      }
    : null;

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <header>
        <h1 style={{ margin: 0 }}>{t("prediction.title")}</h1>
        <p style={{ margin: "6px 0 0", color: "var(--cl-muted)", fontSize: 14 }}>
          {t("prediction.subtitle")}
          {run
            ? t("prediction.subtitleRun", {
                model: run.model_code,
                version: run.model_version,
                status: run.status_banner,
              })
            : ""}
        </p>
      </header>

      {error && <Banner>{error}</Banner>}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(160px,1fr))", gap: 12 }}>
        <Stat label={t("prediction.statModel")} value={models[0] ? `${models[0].model_code}` : "—"} />
        <Stat label={t("prediction.statStatus")} value={models[0]?.status ?? "—"} />
        <Stat label={t("prediction.statHotspotMethod")} value={hotspotMethod ?? "—"} />
        <Stat label={t("prediction.statStations")} value={loading ? "…" : String(values.length)} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1.2fr) minmax(0,1fr)", gap: 12 }}>
        <Panel title={t("prediction.stationRisk")}>
          <Chart option={riskOption} height={280} loading={loading} />
          <div style={{ display: "grid", gap: 6, marginTop: 8 }}>
            {values.map((v) => {
              const name = String(v.properties.station_name ?? tc("station"));
              const active = selected === v.id;
              return (
                <button
                  key={v.id}
                  type="button"
                  onClick={() => setSelected(v.id)}
                  style={{
                    ...rowBtn,
                    borderColor: active ? "var(--cl-accent)" : "var(--cl-border)",
                    background: active ? "rgba(61,139,253,0.12)" : "transparent",
                  }}
                >
                  <span>{name}</span>
                  <strong>{v.value.toFixed(3)}</strong>
                </button>
              );
            })}
          </div>
        </Panel>
        <Panel title={t("prediction.shapTitle")}>
          {shapOption ? <Chart option={shapOption} height={240} /> : <Empty text={t("prediction.selectStation")} />}
          {expl?.summary_text && (
            <p style={{ color: "var(--cl-muted)", fontSize: 13, lineHeight: 1.5, marginTop: 8 }}>
              {expl.summary_text}
            </p>
          )}
          {expl && (
            <div style={{ fontSize: 12, color: "var(--cl-muted)", marginTop: 6 }}>
              {t("prediction.shapMeta", {
                base: expl.base_value.toFixed(2),
                output: expl.output_value.toFixed(3),
                version: expl.model_version,
              })}
            </div>
          )}
          {selected ? (
            <Link
              href={`/explain?value=${selected}`}
              style={{
                display: "inline-block",
                marginTop: 12,
                background: "var(--cl-accent)",
                color: "#fff",
                textDecoration: "none",
                borderRadius: 8,
                padding: "8px 12px",
                fontWeight: 600,
                fontSize: 13,
              }}
            >
              {t("prediction.openDecision")}
            </Link>
          ) : null}
        </Panel>
      </div>

      <Panel title={t("prediction.currentHotspots")}>
        <div style={{ display: "grid", gap: 8 }}>
          {hotspots.map((h) => (
            <div key={h.id} style={hotspotRow}>
              <strong>#{h.rank}</strong>
              <span>{String(h.properties.label ?? tc("hotspot"))}</span>
              <span style={{ color: "var(--cl-muted)" }}>
                {t("prediction.hotspotScore", { score: h.score.toFixed(2) })}
              </span>
              <span style={{ color: "var(--cl-muted)" }}>
                {t("prediction.hotspotIncidents", { count: h.incident_count })}
              </span>
            </div>
          ))}
          {!loading && hotspots.length === 0 && <Empty text={t("prediction.noHotspots")} />}
        </div>
      </Panel>
    </div>
  );
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div style={panelStyle}>
      <div style={{ fontWeight: 600, marginBottom: 8 }}>{title}</div>
      {children}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div style={panelStyle}>
      <div style={{ fontSize: 12, color: "var(--cl-muted)" }}>{label}</div>
      <div style={{ fontSize: 18, fontWeight: 700, marginTop: 6 }}>{value}</div>
    </div>
  );
}

function Banner({ children }: { children: ReactNode }) {
  return (
    <div
      style={{
        border: "1px solid #ff453a",
        borderRadius: 10,
        padding: "10px 12px",
        background: "rgba(255,69,58,0.08)",
        fontSize: 14,
      }}
    >
      {children}
    </div>
  );
}

function Empty({ text }: { text: string }) {
  return (
    <div style={{ color: "var(--cl-muted)", fontSize: 13, padding: "1.5rem 0", textAlign: "center" }}>
      {text}
    </div>
  );
}

const panelStyle: CSSProperties = {
  border: "1px solid var(--cl-border)",
  borderRadius: 12,
  background: "rgba(18, 26, 43, 0.72)",
  padding: "14px 16px",
};

const rowBtn: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: 12,
  padding: "8px 10px",
  borderRadius: 8,
  border: "1px solid var(--cl-border)",
  color: "var(--cl-text)",
  cursor: "pointer",
  fontSize: 13,
  textAlign: "left",
};

const hotspotRow: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "40px 1fr auto auto",
  gap: 12,
  alignItems: "center",
  padding: "8px 10px",
  borderRadius: 8,
  background: "rgba(11,18,32,0.45)",
  fontSize: 13,
};
