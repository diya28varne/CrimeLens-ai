"use client";

import { Suspense } from "react";

import { ExplainStoryHub } from "@/features/explain/ExplainStoryHub";

export default function ExplainPage() {
  return (
    <Suspense fallback={<div style={{ color: "var(--cl-muted)" }}>Loading…</div>}>
      <ExplainStoryHub />
    </Suspense>
  );
}
