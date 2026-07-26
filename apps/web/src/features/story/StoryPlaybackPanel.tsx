"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties, type ReactNode } from "react";
import Map, { NavigationControl } from "react-map-gl/maplibre";
import { ScatterplotLayer } from "@deck.gl/layers";
import "maplibre-gl/dist/maplibre-gl.css";

import { BENGALURU_CENTER, MAP_STYLE, SEVERITY_COLOR } from "@/features/map/constants";
import {
  fetchJourney,
  fetchStoryChapters,
  fetchStoryEvents,
  fetchStoryFrames,
  runDetective,
  type DetectiveBrief,
  type DensityCell,
  type StoryChapter,
  type StoryEvent,
  type StoryFrame,
  type StoryPoint,
} from "@/features/story/api";
import { DeckGLOverlay } from "@/widgets/map-viewport/deck-overlay";
import { ApiError } from "@/shared/api/client";

const SPEEDS = [0.5, 1, 2, 4] as const;

function isoDaysAgo(n: number) {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() - n);
  return d.toISOString().slice(0, 10);
}

function stageColor(stage: string): [number, number, number, number] {
  switch (stage) {
    case "critical":
      return [192, 57, 43, 90];
    case "emerging_hotspot":
      return [230, 126, 34, 75];
    case "growing":
      return [241, 196, 15, 60];
    case "small_cluster":
      return [52, 152, 219, 50];
    case "easing":
      return [26, 188, 156, 55];
    default:
      return [149, 165, 166, 35];
  }
}

export function StoryPlaybackPanel() {
  const [frames, setFrames] = useState<StoryFrame[]>([]);
  const [chapters, setChapters] = useState<StoryChapter[]>([]);
  const [events, setEvents] = useState<StoryEvent[]>([]);
  const [offenseCodes, setOffenseCodes] = useState<string[]>([]);
  const [offense, setOffense] = useState<string>("");
  const [compareWeekend, setCompareWeekend] = useState(false);
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState<(typeof SPEEDS)[number]>(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeChapter, setActiveChapter] = useState<StoryChapter | null>(null);
  const [detective, setDetective] = useState<DetectiveBrief | null>(null);
  const [detectLoading, setDetectLoading] = useState(false);
  const [journey, setJourney] = useState<Awaited<ReturnType<typeof fetchJourney>>["data"] | null>(null);
  const [viewState, setViewState] = useState({
    longitude: BENGALURU_CENTER.longitude,
    latitude: BENGALURU_CENTER.latitude,
    zoom: BENGALURU_CENTER.zoom,
    pitch: 0,
    bearing: 0,
  });

  const playRef = useRef<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setPlaying(false);
    try {
      const from = isoDaysAgo(90);
      const to = isoDaysAgo(0);
      const params = { from, to, offense_code: offense || undefined };
      const [fr, ch, ev] = await Promise.all([
        fetchStoryFrames(params),
        fetchStoryChapters(params),
        fetchStoryEvents({ from, to }),
      ]);
      setFrames(fr.data.frames);
      setChapters(ch.data);
      setEvents(ev.data);
      setOffenseCodes(fr.data.range.offense_codes);
      setIndex(0);
      setActiveChapter(null);
      setDetective(null);
      setJourney(null);
    } catch (e) {
      setError(
        e instanceof ApiError && e.status === 401
          ? "Sign in required — open /login with seeded admin credentials."
          : e instanceof Error
            ? e.message
            : "Failed to load story",
      );
      setFrames([]);
    } finally {
      setLoading(false);
    }
  }, [offense]);

  useEffect(() => {
    void load();
  }, [load]);

  // Accumulate points up to current index
  const { points, density, frame } = useMemo(() => {
    if (!frames.length) return { points: [] as StoryPoint[], density: [] as DensityCell[], frame: null };
    const i = Math.min(index, frames.length - 1);
    const pts: StoryPoint[] = [];
    for (let k = 0; k <= i; k++) pts.push(...frames[k].new_points);
    return { points: pts, density: frames[i].density_cells, frame: frames[i] };
  }, [frames, index]);

  // Highlight chapter when cursor enters its window
  useEffect(() => {
    if (!frame || !chapters.length) return;
    const hit = [...chapters].reverse().find((c) => c.t_start <= frame.t && frame.t <= c.t_end);
    if (hit) setActiveChapter(hit);
  }, [frame, chapters]);

  // Playback ticker
  useEffect(() => {
    if (!playing || frames.length === 0) {
      if (playRef.current) window.clearInterval(playRef.current);
      playRef.current = null;
      return;
    }
    const ms = 450 / speed;
    playRef.current = window.setInterval(() => {
      setIndex((prev) => {
        if (prev >= frames.length - 1) {
          setPlaying(false);
          return prev;
        }
        return prev + 1;
      });
    }, ms);
    return () => {
      if (playRef.current) window.clearInterval(playRef.current);
    };
  }, [playing, speed, frames.length]);

  const layers = useMemo(() => {
    const densityLayer = new ScatterplotLayer({
      id: "story-density",
      data: density.map((d) => ({ ...d, position: [d.lon, d.lat] as [number, number] })),
      stroked: false,
      filled: true,
      radiusUnits: "meters",
      getPosition: (d: { position: [number, number] }) => d.position,
      getRadius: (d: DensityCell) => 400 + d.intensity * 900,
      getFillColor: (d: DensityCell) => stageColor(d.stage),
    });

    let visiblePoints = points;
    if (compareWeekend && frame) {
      // lite period compare: dim non-weekend points when toggle on
      const weekendish = new Set(
        frames
          .filter((f) => {
            const day = new Date(f.t + "T12:00:00Z").getUTCDay();
            return day === 0 || day === 6;
          })
          .flatMap((f) => f.new_points.map((p) => p.id)),
      );
      visiblePoints = points.filter((p) => weekendish.has(p.id));
    }

    const pointLayer = new ScatterplotLayer({
      id: "story-points",
      data: visiblePoints.map((p) => ({
        ...p,
        position: [p.lon, p.lat] as [number, number],
      })),
      pickable: true,
      opacity: 0.9,
      stroked: true,
      filled: true,
      radiusUnits: "pixels",
      getPosition: (d: { position: [number, number] }) => d.position,
      getRadius: 6,
      getFillColor: (d: StoryPoint) => {
        const c = SEVERITY_COLOR[d.severity] ?? [180, 180, 180];
        return [c[0], c[1], c[2], 220];
      },
      getLineColor: [255, 255, 255, 80],
      lineWidthMinPixels: 1,
      onClick: (info) => {
        const id = (info.object as StoryPoint | undefined)?.id;
        if (!id) return;
        void (async () => {
          try {
            const res = await fetchJourney(id);
            setJourney(res.data);
          } catch {
            setJourney(null);
          }
        })();
      },
    });

    return [densityLayer, pointLayer];
  }, [points, density, compareWeekend, frame, frames]);

  async function investigate() {
    if (!frame) return;
    setPlaying(false);
    setDetectLoading(true);
    setDetective(null);
    try {
      const res = await runDetective({
        cursor_at: frame.t,
        window_days: 7,
        offense_code: offense || null,
      });
      setDetective(res.data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Detective mode failed");
    } finally {
      setDetectLoading(false);
    }
  }

  const eventOnCursor = events.find((e) => e.t === frame?.t);

  return (
    <div style={{ display: "grid", gridTemplateRows: "auto 1fr auto", gap: 10, height: "calc(100vh - 3rem)", minHeight: 620 }}>
      <header style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 22 }}>Crime Story Playback</h1>
          <p style={{ margin: "4px 0 0", color: "var(--cl-muted)", fontSize: 13 }}>
            Rewind the city — watch how hotspots form, and investigate any moment.
          </p>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          <label style={{ fontSize: 12, color: "var(--cl-muted)" }}>
            Pattern replay{" "}
            <select
              value={offense}
              onChange={(e) => setOffense(e.target.value)}
              style={selectStyle}
            >
              <option value="">All offenses</option>
              {offenseCodes.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </label>
          <label style={{ fontSize: 12, display: "flex", gap: 6, alignItems: "center" }}>
            <input type="checkbox" checked={compareWeekend} onChange={(e) => setCompareWeekend(e.target.checked)} />
            Weekend-only compare
          </label>
        </div>
      </header>

      {error ? <div style={{ color: "#ff8e8e", fontSize: 13 }}>{error}</div> : null}

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1fr) 300px", gap: 10, minHeight: 0 }}>
        <div style={{ position: "relative", borderRadius: 12, overflow: "hidden", border: "1px solid var(--cl-border)" }}>
          {loading ? (
            <div style={{ padding: 24, color: "var(--cl-muted)" }}>Loading story frames…</div>
          ) : (
            <Map
              {...viewState}
              onMove={(e) => setViewState(e.viewState)}
              mapStyle={MAP_STYLE}
              style={{ width: "100%", height: "100%" }}
            >
              <NavigationControl position="top-right" />
              <DeckGLOverlay layers={layers} />
            </Map>
          )}
          <div style={legendStyle}>
            <div>Density stages: individual → cluster → hotspot → easing</div>
            <div>Click a point for Crime Journey</div>
          </div>
          {activeChapter && frame && activeChapter.t_start <= frame.t && frame.t <= activeChapter.t_end ? (
            <div style={chapterToast}>
              <div style={{ fontSize: 10, letterSpacing: "0.08em", textTransform: "uppercase", color: "#f0c674" }}>
                Observed chapter
              </div>
              <strong>{activeChapter.title}</strong>
              <p style={{ margin: "6px 0 0", fontSize: 12, lineHeight: 1.45 }}>{activeChapter.narrative}</p>
            </div>
          ) : null}
        </div>

        <aside style={{ display: "grid", gap: 10, overflow: "auto", minHeight: 0 }}>
          <Panel title="AI Detective Mode">
            <button type="button" onClick={() => void investigate()} disabled={!frame || detectLoading} style={primaryBtn}>
              {detectLoading ? "Investigating…" : "Investigate This Moment"}
            </button>
            {detective ? (
              <div style={{ marginTop: 10, display: "grid", gap: 8 }}>
                <div style={{ fontWeight: 600, fontSize: 14 }}>{detective.headline}</div>
                <div style={{ fontSize: 11, color: "var(--cl-muted)" }}>
                  {detective.window_from} → {detective.window_to} · {Math.round(detective.confidence * 100)}%
                </div>
                {detective.findings.map((f) => (
                  <div key={f.question} style={cardStyle}>
                    <div style={{ fontSize: 12, fontWeight: 600 }}>{f.question}</div>
                    <p style={{ margin: "4px 0 0", fontSize: 12, lineHeight: 1.45 }}>{f.answer}</p>
                  </div>
                ))}
                <ul style={{ margin: 0, paddingLeft: 16, fontSize: 12 }}>
                  {detective.suggested_actions.map((a) => (
                    <li key={a}>{a}</li>
                  ))}
                </ul>
                {detective.simulation_preset_id ? (
                  <Link href="/simulation" style={{ color: "var(--cl-accent)", fontSize: 12 }}>
                    Open Simulator →
                  </Link>
                ) : null}
                <p style={{ fontSize: 11, color: "#f0c674", margin: 0 }}>{detective.disclaimer}</p>
              </div>
            ) : (
              <p style={{ fontSize: 12, color: "var(--cl-muted)", marginTop: 8 }}>
                Pause on any date and investigate the surrounding window.
              </p>
            )}
          </Panel>

          <Panel title="Timeline events">
            <div style={{ display: "grid", gap: 6 }}>
              {events.map((e) => (
                <button
                  key={e.id}
                  type="button"
                  onClick={() => {
                    const i = frames.findIndex((f) => f.t === e.t);
                    if (i >= 0) {
                      setPlaying(false);
                      setIndex(i);
                    }
                  }}
                  style={{
                    ...cardStyle,
                    textAlign: "left",
                    cursor: "pointer",
                    borderColor: eventOnCursor?.id === e.id ? "var(--cl-accent)" : "var(--cl-border)",
                  }}
                >
                  <div style={{ fontSize: 11, color: "var(--cl-muted)" }}>{e.t} · {e.kind}</div>
                  <div style={{ fontWeight: 600, fontSize: 13 }}>{e.label}</div>
                  <div style={{ fontSize: 11, color: "var(--cl-muted)" }}>{e.detail}</div>
                </button>
              ))}
            </div>
          </Panel>

          {journey ? (
            <Panel title="Crime Journey">
              <div style={{ fontWeight: 600, fontSize: 13 }}>{journey.title}</div>
              <div style={{ fontSize: 11, color: "var(--cl-muted)", marginBottom: 8 }}>
                {journey.offense_code} · {journey.nearby_similar} similar nearby
              </div>
              <ol style={{ margin: 0, paddingLeft: 18, fontSize: 12, display: "grid", gap: 6 }}>
                {journey.steps.map((s) => (
                  <li key={s.key}>
                    <strong>{s.label}</strong> — {s.detail}
                  </li>
                ))}
              </ol>
            </Panel>
          ) : null}
        </aside>
      </div>

      {/* Playback controller */}
      <div style={playerStyle}>
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <button type="button" style={ctrlBtn} onClick={() => setIndex((i) => Math.max(0, i - 1))} title="Step back">
            ⏮
          </button>
          <button
            type="button"
            style={ctrlBtn}
            onClick={() => setPlaying((p) => !p)}
            disabled={!frames.length}
          >
            {playing ? "⏸ Pause" : "▶ Play"}
          </button>
          <button
            type="button"
            style={ctrlBtn}
            onClick={() => setIndex((i) => Math.min(frames.length - 1, i + 1))}
            title="Step forward"
          >
            ⏭
          </button>
          <select
            value={speed}
            onChange={(e) => setSpeed(Number(e.target.value) as (typeof SPEEDS)[number])}
            style={selectStyle}
          >
            {SPEEDS.map((s) => (
              <option key={s} value={s}>
                {s}×
              </option>
            ))}
          </select>
          <span style={{ fontSize: 13, minWidth: 200 }}>
            {frame ? (
              <>
                <strong>{frame.t}</strong> · {frame.cumulative_count} cumulative · +{frame.new_count} today
              </>
            ) : (
              "—"
            )}
          </span>
          {eventOnCursor ? (
            <span style={{ fontSize: 12, color: "#f0c674" }}>Marker: {eventOnCursor.label}</span>
          ) : null}
        </div>
        <input
          type="range"
          min={0}
          max={Math.max(0, frames.length - 1)}
          value={index}
          onChange={(e) => {
            setPlaying(false);
            setIndex(Number(e.target.value));
          }}
          style={{ width: "100%", marginTop: 8 }}
        />
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "var(--cl-muted)" }}>
          <span>{frames[0]?.t ?? ""}</span>
          <span>{chapters.length} narrative chapters · {events.length} event markers</span>
          <span>{frames[frames.length - 1]?.t ?? ""}</span>
        </div>
      </div>
    </div>
  );
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section style={{ border: "1px solid var(--cl-border)", borderRadius: 12, padding: 12, background: "rgba(18,26,43,0.75)" }}>
      <h3 style={{ margin: "0 0 10px", fontSize: 11, letterSpacing: "0.08em", textTransform: "uppercase", color: "var(--cl-muted)" }}>
        {title}
      </h3>
      {children}
    </section>
  );
}

const selectStyle: CSSProperties = {
  padding: "6px 8px",
  borderRadius: 8,
  border: "1px solid var(--cl-border)",
  background: "var(--cl-surface)",
  color: "var(--cl-text)",
  marginLeft: 6,
};

const playerStyle: CSSProperties = {
  border: "1px solid var(--cl-border)",
  borderRadius: 12,
  padding: "12px 14px",
  background: "rgba(12, 18, 32, 0.92)",
};

const ctrlBtn: CSSProperties = {
  background: "rgba(61,139,253,0.15)",
  border: "1px solid var(--cl-border)",
  color: "var(--cl-text)",
  borderRadius: 8,
  padding: "8px 12px",
  cursor: "pointer",
  fontSize: 13,
};

const primaryBtn: CSSProperties = {
  width: "100%",
  background: "var(--cl-accent)",
  color: "#fff",
  border: 0,
  borderRadius: 8,
  padding: "10px 12px",
  fontWeight: 600,
  cursor: "pointer",
};

const cardStyle: CSSProperties = {
  border: "1px solid var(--cl-border)",
  borderRadius: 8,
  padding: "8px 10px",
  background: "rgba(12,18,32,0.55)",
};

const legendStyle: CSSProperties = {
  position: "absolute",
  left: 10,
  bottom: 10,
  background: "rgba(12,18,32,0.88)",
  border: "1px solid var(--cl-border)",
  borderRadius: 8,
  padding: "8px 10px",
  fontSize: 11,
  color: "var(--cl-muted)",
};

const chapterToast: CSSProperties = {
  position: "absolute",
  left: 10,
  top: 10,
  right: 56,
  maxWidth: 420,
  background: "rgba(12,18,32,0.92)",
  border: "1px solid #5a4a20",
  borderRadius: 10,
  padding: "10px 12px",
  fontSize: 13,
};
