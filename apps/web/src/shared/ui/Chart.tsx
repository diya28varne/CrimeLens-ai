"use client";

import ReactECharts from "echarts-for-react";
import type { EChartsOption } from "echarts";
import type { CSSProperties } from "react";

type ChartProps = {
  option: EChartsOption | null;
  height?: number | string;
  style?: CSSProperties;
  loading?: boolean;
};

const darkText = "#9aa8c7";

/** Shared dark-theme ECharts wrapper for CrimeLens panels. */
export function Chart({ option, height = 280, style, loading }: ChartProps) {
  if (!option) return null;
  const merged: EChartsOption = {
    backgroundColor: "transparent",
    textStyle: { color: darkText, fontFamily: "Segoe UI, IBM Plex Sans, sans-serif" },
    ...option,
  };

  return (
    <ReactECharts
      option={merged}
      showLoading={loading}
      style={{ height, width: "100%", ...style }}
      opts={{ renderer: "canvas" }}
      notMerge
    />
  );
}
