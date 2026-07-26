"use client";

import { useRouter, useSearchParams } from "next/navigation";
import type { ReactNode } from "react";

import { ExplainPanel } from "@/features/explain";
import { StoryPlaybackPanel } from "@/features/story";

export type ExplainView = "explain" | "story";

/** Combined Explain + Story hub — Story keeps full playback via tab/link. */
export function ExplainStoryHub() {
  const params = useSearchParams();
  const router = useRouter();
  const view: ExplainView = params.get("view") === "story" ? "story" : "explain";
  const valueId = params.get("value");

  function setView(next: ExplainView) {
    const q = new URLSearchParams();
    if (next === "story") q.set("view", "story");
    if (valueId && next === "explain") q.set("value", valueId);
    const qs = q.toString();
    router.replace(qs ? `/explain?${qs}` : "/explain");
  }

  return (
    <div style={{ display: "grid", gap: 16 }}>
      <div
        role="tablist"
        aria-label="Explain and Story"
        style={{
          display: "inline-flex",
          gap: 6,
          padding: 4,
          borderRadius: 12,
          border: "1px solid var(--cl-border)",
          background: "rgba(18, 26, 43, 0.72)",
          width: "fit-content",
          flexWrap: "wrap",
        }}
      >
        <TabButton active={view === "explain"} onClick={() => setView("explain")}>
          Explain
        </TabButton>
        <TabButton active={view === "story"} onClick={() => setView("story")}>
          Story playback
        </TabButton>
      </div>

      {view === "explain" ? (
        <ExplainPanel initialValueId={valueId} storyHref="/explain?view=story" />
      ) : (
        <StoryPlaybackPanel explainHref="/explain" />
      )}
    </div>
  );
}

function TabButton({
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
      role="tab"
      aria-selected={active}
      onClick={onClick}
      style={{
        border: "none",
        cursor: "pointer",
        borderRadius: 9,
        padding: "8px 14px",
        fontWeight: 700,
        fontSize: 13,
        background: active ? "rgba(61,139,253,0.22)" : "transparent",
        color: active ? "#fff" : "var(--cl-muted)",
        boxShadow: active ? "inset 0 0 0 1px rgba(61,139,253,0.45)" : "none",
      }}
    >
      {children}
    </button>
  );
}
