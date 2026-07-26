import { NextResponse } from "next/server";

import { proxyToUpstream, resolveApiUpstream } from "@/shared/lib/demo-auth";

export async function POST(request: Request) {
  const upstream = resolveApiUpstream();
  if (upstream) {
    try {
      return await proxyToUpstream(upstream, "/api/v1/auth/logout", request);
    } catch {
      // Demo / offline logout still succeeds locally.
    }
  }
  return new NextResponse(null, { status: 204 });
}
