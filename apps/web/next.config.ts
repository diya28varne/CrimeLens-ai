import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  reactStrictMode: true,
  poweredByHeader: false,
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
