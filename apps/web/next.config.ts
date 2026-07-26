import type { NextConfig } from "next";

function resolveProxyTarget(): string | null {
  const explicit = (process.env.CRIMELENS_API_PROXY_TARGET ?? "").trim().replace(/\/$/, "");
  if (explicit) {
    // Never proxy Vercel → localhost (causes "Failed to fetch" / broken login).
    if (process.env.VERCEL && /localhost|127\.0\.0\.1/i.test(explicit)) {
      return null;
    }
    return explicit;
  }
  // Local/dev: Docker API. On Vercel with no remote API: skip rewrite so
  // Next.js demo auth routes under /api/v1/auth/* can handle open login.
  if (process.env.VERCEL) {
    return null;
  }
  return "http://127.0.0.1:8000";
}

const nextConfig: NextConfig = {
  // standalone only for Docker image builds — Vercel breaks with output:standalone
  ...(process.env.DOCKER_BUILD === "1" ? { output: "standalone" as const } : {}),
  reactStrictMode: true,
  poweredByHeader: false,
  async rewrites() {
    const apiProxyTarget = resolveProxyTarget();
    if (!apiProxyTarget) {
      return [];
    }
    return [
      {
        source: "/api/v1/:path*",
        destination: `${apiProxyTarget}/api/v1/:path*`,
      },
    ];
  },
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
