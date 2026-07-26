import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // standalone only for Docker image builds — Vercel breaks with output:standalone
  ...(process.env.DOCKER_BUILD === "1" ? { output: "standalone" as const } : {}),
  reactStrictMode: true,
  poweredByHeader: false,
  experimental: {
    optimizePackageImports: [
      "echarts",
      "echarts-for-react",
      "i18next",
      "react-i18next",
      "@deck.gl/layers",
      "@deck.gl/aggregation-layers",
      "@deck.gl/core",
    ],
  },
  transpilePackages: [
    "maplibre-gl",
    "react-map-gl",
    "@deck.gl/core",
    "@deck.gl/react",
    "@deck.gl/layers",
    "@deck.gl/aggregation-layers",
    "@deck.gl/mapbox",
    "echarts",
    "echarts-for-react",
  ],
};

export default nextConfig;
