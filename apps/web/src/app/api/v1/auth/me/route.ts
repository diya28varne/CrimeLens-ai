import { NextResponse } from "next/server";

import {
  bearerFromRequest,
  proxyToUpstream,
  resolveApiUpstream,
  verifyDemoToken,
} from "@/shared/lib/demo-auth";

function parseLooseDemoToken(token: string) {
  const verified = verifyDemoToken(token);
  if (verified) return verified;
  // Browser-minted demo tokens end with ".client" (no HMAC).
  if (!token.startsWith("cldemo.") || !token.endsWith(".client")) return null;
  try {
    const raw = token.slice("cldemo.".length, -".client".length);
    const body = raw.endsWith(".") ? raw.slice(0, -1) : raw;
    const json = Buffer.from(body, "base64url").toString("utf8");
    const payload = JSON.parse(json) as {
      id?: string;
      email?: string;
      full_name?: string;
      exp?: number;
      type?: string;
    };
    if (payload.type !== "demo" || !payload.email || !payload.id) return null;
    if (typeof payload.exp === "number" && payload.exp < Date.now()) return null;
    return {
      id: payload.id,
      email: payload.email,
      full_name: payload.full_name || payload.email,
      status: "active" as const,
    };
  } catch {
    return null;
  }
}

export async function GET(request: Request) {
  const upstream = resolveApiUpstream();
  const token = bearerFromRequest(request);

  if (token?.startsWith("cldemo.")) {
    const user = parseLooseDemoToken(token);
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
