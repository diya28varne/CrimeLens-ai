import { NextResponse } from "next/server";

import {
  isOpenDemoLoginEnabled,
  issueDemoToken,
  proxyToUpstream,
  resolveApiUpstream,
  verifyDemoToken,
} from "@/shared/lib/demo-auth";

type LoginBody = {
  email?: string;
  password?: string;
  client?: string;
};

export async function POST(request: Request) {
  const upstream = resolveApiUpstream();
  if (upstream) {
    try {
      return await proxyToUpstream(upstream, "/api/v1/auth/login", request);
    } catch {
      // Fall through to demo login when local/remote API is down.
    }
  }

  if (!isOpenDemoLoginEnabled()) {
    return NextResponse.json(
      { error: { message: "API unavailable", code: "API_UNAVAILABLE" } },
      { status: 503 },
    );
  }

  let body: LoginBody;
  try {
    body = (await request.json()) as LoginBody;
  } catch {
    return NextResponse.json(
      { error: { message: "Invalid JSON body", code: "BAD_REQUEST" } },
      { status: 400 },
    );
  }

  const email = (body.email ?? "").trim().toLowerCase();
  const password = body.password ?? "";
  if (!email.includes("@") || email.length < 3 || !password) {
    return NextResponse.json(
      { error: { message: "Invalid email or password", code: "INVALID_CREDENTIALS" } },
      { status: 401 },
    );
  }

  const accessToken = issueDemoToken(email);
  const user = verifyDemoToken(accessToken);
  if (!user) {
    return NextResponse.json(
      { error: { message: "Login failed", code: "LOGIN_FAILED" } },
      { status: 500 },
    );
  }

  return NextResponse.json({
    data: {
      user,
      access_token: accessToken,
      expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
      permissions: ["*"],
    },
  });
}
