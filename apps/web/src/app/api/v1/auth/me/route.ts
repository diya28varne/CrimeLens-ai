import { NextResponse } from "next/server";

import {
  bearerFromRequest,
  proxyToUpstream,
  resolveApiUpstream,
  verifyDemoToken,
} from "@/shared/lib/demo-auth";

export async function GET(request: Request) {
  const upstream = resolveApiUpstream();
  const token = bearerFromRequest(request);

  // Demo tokens are always handled locally (even if an upstream exists).
  if (token?.startsWith("cldemo.")) {
    const user = verifyDemoToken(token);
    if (!user) {
      return NextResponse.json(
        { error: { message: "Invalid or expired access token", code: "UNAUTHORIZED" } },
        { status: 401 },
      );
    }
    return NextResponse.json({
      data: {
        user,
        roles: ["admin"],
        permissions: ["*"],
        jurisdictions: { district_ids: [], station_ids: [] },
      },
    });
  }

  if (upstream) {
    try {
      return await proxyToUpstream(upstream, "/api/v1/auth/me", request);
    } catch {
      return NextResponse.json(
        { error: { message: "API unavailable", code: "API_UNAVAILABLE" } },
        { status: 503 },
      );
    }
  }

  return NextResponse.json(
    { error: { message: "Authentication required", code: "UNAUTHORIZED" } },
    { status: 401 },
  );
}
