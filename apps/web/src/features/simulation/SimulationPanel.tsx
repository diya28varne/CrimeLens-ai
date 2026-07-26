"use client";

import { useCallback, useEffect, useState, type CSSProperties, type ReactNode } from "react";

import {
  DEFAULT_CONTROLS,
  fetchScenarios,
  runSimulation,
  type ScenarioControls,
  type ScenarioPreset,
  type SimulationRun,
} from "@/features/simulation/api";
import { SimulationMap } from "@/features/simulation/SimulationMap";
import { ApiError } from "@/shared/api/client";

export function SimulationPanel() {
  const [presets, setPresets] = useState<ScenarioPreset[]>([]);
  const [controls, setControls] = useState<ScenarioControls>(DEFAULT_CONTROLS);
  const [activePreset, setActivePreset] = useState<string | null>(null);
  const [result, setResult] = useState<SimulationRun | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mapMode, setMapMode] = useState<"simulated" | "delta">("delta");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetchScenarios();
        if (!cancelled) setPresets(res.data);
      } catch (e) {
        if (!cancelled) {
          setError(
            e instanceof ApiError && e.status === 401
              ? "Sign in required — open /login with seeded admin credentials."
              : e instanceof Error
                ? e.message
                : "Failed to load scenarios",
          );
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const execute = useCallback(async (next: ScenarioControls, presetId: string | null) => {
    setLoading(true);
    setError(null);
    try {
      const res = await runSimulation({
        preset_id: presetId,
        controls: next,
      });
      setResult(res.data);
    } catch (e) {
      setError(
        e instanceof ApiError && e.status === 401
          ? "Sign in required — open /login with seeded admin credentials."
          : e instanceof Error
            ? e.message
            : "Simulation failed",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial + debounced re-run when controls change
  useEffect(() => {
    const t = window.setTimeout(() => {
      void execute(controls, activePreset);
    }, 400);
    return () => window.clearTimeout(t);
  }, [controls, activePreset, execute]);

  function loadPreset(preset: ScenarioPreset) {
    setActivePreset(preset.id);
    setControls(preset.controls);
  }

  function patchControl<K extends keyof ScenarioControls>(key: K, value: ScenarioControls[K]) {
    setActivePreset((prev) => prev); // keep preset id; API labels as modified when changed
    setControls((c) => ({ ...c, [key]: value }));
  }

  const briefing = result?.briefing;

  return (
    <div style={{ display: "grid", gap: 12, height: "calc(100vh - 3rem)", minHeight: 640 }}>
      <header style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 22 }}>Decision Simulation Center</h1>
          <p style={{ margin: "4px 0 0", color: "var(--cl-muted)", fontSize: 13 }}>
            Digital Twin — test operational what-ifs before you deploy.
          </p>
        </div>
        <div
          style={{
            alignSelf: "center",
            fontSize: 12,
            color: "#f0c674",
            border: "1px solid #5a4a20",
            background: "rgba(90, 74, 32, 0.35)",
            borderRadius: 8,
            padding: "8px 10px",
            maxWidth: 420,
          }}
        >
          {result?.disclaimer ??
            "Estimates from a decision model — not guarantees. Use for planning support only."}
        </div>
      </header>

      {error ? (
        <div style={{ color: "#ff8e8e", fontSize: 13 }}>{error}</div>
      ) : null}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(240px, 280px) minmax(0, 1fr) minmax(240px, 300px)",
          gridTemplateRows: "1fr auto",
          gap: 12,
          minHeight: 0,
          flex: 1,
        }}
      >
        {/* Left — Scenario Builder */}
        <Panel title="Scenario Builder" style={{ gridRow: "1 / 2", overflow: "auto" }}>
          <div style={{ marginBottom: 12 }}>
            <div style={sectionLabel}>Scenario Library</div>
            <div style={{ display: "grid", gap: 6 }}>
              {presets.map((p) => {
                const active = activePreset === p.id;
                return (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => loadPreset(p)}
                    style={{
                      textAlign: "left",
                      padding: "8px 10px",
                      borderRadius: 8,
                      border: active ? "1px solid var(--cl-accent)" : "1px solid var(--cl-border)",
                      background: active ? "rgba(61, 139, 253, 0.15)" : "transparent",
                      color: "var(--cl-text)",
                      cursor: "pointer",
                    }}
                  >
                    <div style={{ fontWeight: 600, fontSize: 13 }}>{p.name}</div>
                    <div style={{ fontSize: 11, color: "var(--cl-muted)", marginTop: 2 }}>{p.description}</div>
                  </button>
                );
              })}
            </div>
          </div>

          <div style={sectionLabel}>Levers</div>
          <Slider
            label={`Patrol units (${controls.patrol_delta_pct > 0 ? "+" : ""}${controls.patrol_delta_pct}%)`}
            value={controls.patrol_delta_pct}
            min={-50}
            max={50}
            onChange={(v) => patchControl("patrol_delta_pct", v)}
          />
          <Slider
            label={`CCTV coverage (${controls.cctv_delta_pct > 0 ? "+" : ""}${controls.cctv_delta_pct}%)`}
            value={controls.cctv_delta_pct}
            min={-50}
            max={50}
            onChange={(v) => patchControl("cctv_delta_pct", v)}
          />

          <label style={fieldStyle}>
            <span>Time of day</span>
            <select
              value={controls.time_of_day}
              onChange={(e) => patchControl("time_of_day", e.target.value as ScenarioControls["time_of_day"])}
              style={inputStyle}
            >
              <option value="morning">Morning</option>
              <option value="afternoon">Afternoon</option>
              <option value="evening">Evening</option>
              <option value="night">Night</option>
            </select>
          </label>

          <label style={fieldStyle}>
            <span>Day type</span>
            <select
              value={controls.day_type}
              onChange={(e) => patchControl("day_type", e.target.value as ScenarioControls["day_type"])}
              style={inputStyle}
            >
              <option value="weekday">Weekday</option>
              <option value="weekend">Weekend</option>
              <option value="holiday">Holiday</option>
            </select>
          </label>

          <label style={fieldStyle}>
            <span>Focus zone</span>
            <select
              value={controls.event_zone}
              onChange={(e) => patchControl("event_zone", e.target.value as ScenarioControls["event_zone"])}
              style={inputStyle}
            >
              <option value="central">Central Business District</option>
              <option value="metro_corridor_a">Metro Corridor A</option>
              <option value="east">East Bengaluru</option>
              <option value="west">West Bengaluru</option>
              <option value="north">North Bengaluru</option>
              <option value="south">South Bengaluru</option>
            </select>
          </label>

          <Toggle
            label="Public event / disruption"
            checked={controls.public_event}
            onChange={(v) => patchControl("public_event", v)}
          />
          <Toggle
            label="Heavy rainfall stress"
            checked={controls.weather_stress}
            onChange={(v) => patchControl("weather_stress", v)}
          />
        </Panel>

        {/* Center — Map */}
        <Panel
          title={
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
              <span>City risk map {loading ? "· updating…" : ""}</span>
              <div style={{ display: "flex", gap: 6 }}>
                <ModeChip active={mapMode === "delta"} onClick={() => setMapMode("delta")}>
                  Delta
                </ModeChip>
                <ModeChip active={mapMode === "simulated"} onClick={() => setMapMode("simulated")}>
                  Simulated
                </ModeChip>
              </div>
            </div>
          }
          style={{ gridRow: "1 / 2", minHeight: 0, display: "flex", flexDirection: "column" }}
          bodyStyle={{ flex: 1, minHeight: 0, padding: 0 }}
        >
          <SimulationMap
            points={result?.points ?? []}
            eventZone={result?.event_zone ?? null}
            showMode={mapMode}
          />
        </Panel>

        {/* Right — Briefing */}
        <Panel title="AI prediction summary" style={{ gridRow: "1 / 2", overflow: "auto" }}>
          <div style={sectionLabel}>Current scenario</div>
          <div style={{ fontWeight: 600, marginBottom: 4 }}>{briefing?.scenario_label ?? "—"}</div>
          <div style={{ fontSize: 13, color: "var(--cl-muted)", marginBottom: 12 }}>
            City risk band: <strong style={{ color: "var(--cl-text)" }}>{briefing?.current_risk_band ?? "—"}</strong>
          </div>

          <div style={sectionLabel}>Predicted change</div>
          <ul style={listStyle}>
            {(briefing?.predicted_changes ?? ["Run a scenario to see projected shifts."]).map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>

          <div style={sectionLabel}>Suggested actions</div>
          <ul style={listStyle}>
            {(briefing?.suggested_actions ?? []).map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>

          <div style={sectionLabel}>Confidence</div>
          <div style={{ fontSize: 28, fontWeight: 700, letterSpacing: "-0.02em" }}>
            {briefing ? `${Math.round(briefing.confidence * 100)}%` : "—"}
          </div>
          <p style={{ fontSize: 11, color: "var(--cl-muted)", marginTop: 8 }}>
            Intelligence briefing style — grounded in current prediction / hotspot runs plus scenario levers.
          </p>
        </Panel>

        {/* Bottom — Comparison */}
        <Panel title="Current vs simulated" style={{ gridColumn: "1 / -1" }}>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))",
              gap: 10,
            }}
          >
            {(result?.comparison ?? []).map((m) => {
              const diff = m.simulated - m.baseline;
              const good =
                m.higher_is_better == null
                  ? null
                  : m.higher_is_better
                    ? diff > 0
                    : diff < 0;
              return (
                <div
                  key={m.key}
                  style={{
                    border: "1px solid var(--cl-border)",
                    borderRadius: 8,
                    padding: "10px 12px",
                    background: "rgba(18, 26, 43, 0.55)",
                  }}
                >
                  <div style={{ fontSize: 11, color: "var(--cl-muted)", marginBottom: 6 }}>{m.label}</div>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 8, fontSize: 13 }}>
                    <span>
                      Now{" "}
                      <strong>{formatMetric(m.baseline, m.unit)}</strong>
                    </span>
                    <span>
                      Sim{" "}
                      <strong>{formatMetric(m.simulated, m.unit)}</strong>
                    </span>
                  </div>
                  <div
                    style={{
                      marginTop: 6,
                      fontSize: 12,
                      color: good == null ? "var(--cl-muted)" : good ? "#1abc9c" : "#e67e22",
                    }}
                  >
                    Δ {diff >= 0 ? "+" : ""}
                    {formatMetric(diff, m.unit)}
                  </div>
                </div>
              );
            })}
            {!result ? (
              <div style={{ color: "var(--cl-muted)", fontSize: 13 }}>Comparison metrics appear after the first run.</div>
            ) : null}
          </div>
        </Panel>
      </div>
    </div>
  );
}

function formatMetric(v: number, unit: string) {
  if (unit === "count") return String(Math.round(v));
  if (unit === "score") return v.toFixed(3);
  return v.toFixed(1);
}

function Panel({
  title,
  children,
  style,
  bodyStyle,
}: {
  title: ReactNode;
  children: ReactNode;
  style?: CSSProperties;
  bodyStyle?: CSSProperties;
}) {
  return (
    <section
      style={{
        border: "1px solid var(--cl-border)",
        borderRadius: 12,
        background: "rgba(18, 26, 43, 0.72)",
        display: "flex",
        flexDirection: "column",
        minHeight: 0,
        ...style,
      }}
    >
      <div
        style={{
          padding: "10px 12px",
          borderBottom: "1px solid var(--cl-border)",
          fontWeight: 600,
          fontSize: 13,
        }}
      >
        {title}
      </div>
      <div style={{ padding: 12, ...bodyStyle }}>{children}</div>
    </section>
  );
}

function Slider({
  label,
  value,
  min,
  max,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  onChange: (v: number) => void;
}) {
  return (
    <label style={{ display: "grid", gap: 4, marginBottom: 10 }}>
      <span style={{ fontSize: 12 }}>{label}</span>
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        style={{ width: "100%" }}
      />
    </label>
  );
}

function Toggle({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        gap: 8,
        marginBottom: 8,
        fontSize: 13,
      }}
    >
      <span>{label}</span>
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
    </label>
  );
}

function ModeChip({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        fontSize: 11,
        padding: "4px 8px",
        borderRadius: 6,
        border: active ? "1px solid var(--cl-accent)" : "1px solid var(--cl-border)",
        background: active ? "rgba(61, 139, 253, 0.2)" : "transparent",
        color: "var(--cl-text)",
        cursor: "pointer",
      }}
    >
      {children}
    </button>
  );
}

const sectionLabel: CSSProperties = {
  fontSize: 11,
  letterSpacing: "0.08em",
  textTransform: "uppercase",
  color: "var(--cl-muted)",
  marginBottom: 6,
};

const fieldStyle: CSSProperties = {
  display: "grid",
  gap: 4,
  marginBottom: 10,
  fontSize: 12,
};

const inputStyle: CSSProperties = {
  padding: 8,
  borderRadius: 8,
  border: "1px solid var(--cl-border)",
  background: "var(--cl-surface)",
  color: "var(--cl-text)",
};

const listStyle: CSSProperties = {
  margin: "0 0 14px",
  paddingLeft: 18,
  fontSize: 13,
  color: "var(--cl-text)",
  lineHeight: 1.45,
};
