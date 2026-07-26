"use client";

import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { ExplainPanel } from "@/features/explain";

function ExplainInner() {
  const params = useSearchParams();
  const valueId = params.get("value");
  return <ExplainPanel initialValueId={valueId} />;
}

export default function ExplainPage() {
  return (
    <Suspense fallback={<div style={{ color: "var(--cl-muted)" }}>Loading decision engine…</div>}>
      <ExplainInner />
    </Suspense>
  );
}
