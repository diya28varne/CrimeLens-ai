import { NextRequest, NextResponse } from "next/server";

import { proxyToUpstream, resolveApiUpstream } from "@/shared/lib/demo-auth";

type RouteContext = { params: Promise<{ path: string[] }> };

async function handle(request: NextRequest, context: RouteContext) {
  const upstream = resolveApiUpstream();
  if (!upstream) {
    return NextResponse.json(
      {
        error: {
          message:
            "API is not configured. Set CRIMELENS_API_PROXY_TARGET to your public FastAPI origin.",
          code: "API_UNAVAILABLE",
        },
      },
      { status: 503 },
    );
  }

  const { path } = await context.params;
  const suffix = path.map(encodeURIComponent).join("/");
  const url = new URL(request.url);
  const targetPath = `/api/v1/${suffix}${url.search}`;

  try {
    return await proxyToUpstream(upstream, targetPath, request);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Upstream request failed";
    return NextResponse.json(
      { error: { message, code: "UPSTREAM_ERROR" } },
      { status: 502 },
    );
  }
}

export const GET = handle;
export const POST = handle;
export const PUT = handle;
export const PATCH = handle;
export const DELETE = handle;
export const OPTIONS = handle;
