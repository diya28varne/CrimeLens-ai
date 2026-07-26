import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/** Phase 1: pass-through. Auth gating lands with Identity module. */
export function middleware(_request: NextRequest) {
  return NextResponse.next();
}

export const config = {
  matcher: [
    "/dashboard/:path*",
    "/analytics/:path*",
    "/map/:path*",
    "/prediction/:path*",
    "/simulation/:path*",
    "/advisor/:path*",
    "/story/:path*",
    "/explain/:path*",
    "/reports/:path*",
  ],
};
