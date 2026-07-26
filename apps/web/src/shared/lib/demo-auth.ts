import { createHmac, randomUUID, timingSafeEqual } from "crypto";

export type DemoUser = {
  id: string;
  email: string;
  full_name: string;
  status: "active";
};

const TOKEN_PREFIX = "cldemo.";

function demoSecret(): string {
  return (
    process.env.DEMO_AUTH_SECRET ||
    process.env.JWT_SECRET ||
    "crimelens-vercel-open-demo"
  );
}

/** Open demo login unless explicitly disabled. */
export function isOpenDemoLoginEnabled(): boolean {
  return (
    process.env.OPEN_DEMO_LOGIN !== "false" &&
    process.env.NEXT_PUBLIC_OPEN_DEMO_LOGIN !== "false"
  );
}

/**
 * Prefer a real API when configured. On Vercel with no remote API, use demo auth.
 */
export function resolveApiUpstream(): string | null {
  const explicit = (process.env.CRIMELENS_API_PROXY_TARGET ?? "").trim().replace(/\/$/, "");
  if (explicit) {
    if (/localhost|127\.0\.0\.1/i.test(explicit) && process.env.VERCEL) {
      return null;
    }
    return explicit;
  }
  if (process.env.VERCEL) {
    return null;
  }
  return "http://127.0.0.1:8000";
}

export function displayNameFromEmail(email: string): string {
  const local = email.split("@", 1)[0] ?? "guest";
  const cleaned = local.replace(/[._]+/g, " ").trim();
  return cleaned ? cleaned.replace(/\b\w/g, (c) => c.toUpperCase()) : "CrimeLens Guest";
}

export function issueDemoToken(email: string): string {
  const normalized = email.toLowerCase().trim();
  const body = Buffer.from(
    JSON.stringify({
      id: randomUUID(),
      email: normalized,
      full_name: displayNameFromEmail(normalized),
      status: "active",
      exp: Date.now() + 7 * 24 * 60 * 60 * 1000,
      type: "demo",
    }),
    "utf8",
  ).toString("base64url");
  const sig = createHmac("sha256", demoSecret()).update(body).digest("base64url");
  return `${TOKEN_PREFIX}${body}.${sig}`;
}

export function verifyDemoToken(token: string): DemoUser | null {
  if (!token.startsWith(TOKEN_PREFIX)) return null;
  const raw = token.slice(TOKEN_PREFIX.length);
  const dot = raw.lastIndexOf(".");
  if (dot <= 0) return null;
  const body = raw.slice(0, dot);
  const sig = raw.slice(dot + 1);
  const expected = createHmac("sha256", demoSecret()).update(body).digest("base64url");
  try {
    const a = Buffer.from(sig);
    const b = Buffer.from(expected);
    if (a.length !== b.length || !timingSafeEqual(a, b)) return null;
  } catch {
    return null;
  }
  try {
    const payload = JSON.parse(Buffer.from(body, "base64url").toString("utf8")) as {
      id?: string;
      email?: string;
      full_name?: string;
      status?: string;
      exp?: number;
      type?: string;
    };
    if (payload.type !== "demo" || !payload.email || !payload.id) return null;
    if (typeof payload.exp === "number" && payload.exp < Date.now()) return null;
    return {
      id: payload.id,
      email: payload.email,
      full_name: payload.full_name || displayNameFromEmail(payload.email),
      status: "active",
    };
  } catch {
    return null;
  }
}

export function bearerFromRequest(request: Request): string | null {
  const header = request.headers.get("authorization");
  if (header && header.toLowerCase().startsWith("bearer ")) {
    return header.slice(7).trim();
  }
  return null;
}

export async function proxyToUpstream(
  upstream: string,
  path: string,
  request: Request,
): Promise<Response> {
  const url = `${upstream}${path}`;
  const headers = new Headers();
  const allow = [
    "accept",
    "accept-language",
    "authorization",
    "content-type",
    "cookie",
    "x-crimelens-locale",
  ];
  for (const key of allow) {
    const value = request.headers.get(key);
    if (value) headers.set(key, value);
  }

  const init: RequestInit = {
    method: request.method,
    headers,
    redirect: "manual",
  };
  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = await request.arrayBuffer();
  }

  const upstreamRes = await fetch(url, init);
  // Buffer the body so we can drop content-encoding headers that break clients
  // when undici already decoded the stream.
  const body = await upstreamRes.arrayBuffer();
  const outHeaders = new Headers();
  const contentType = upstreamRes.headers.get("content-type");
  if (contentType) outHeaders.set("content-type", contentType);
  const setCookie = upstreamRes.headers.getSetCookie?.() ?? [];
  for (const cookie of setCookie) {
    outHeaders.append("set-cookie", cookie);
  }

  return new Response(body, {
    status: upstreamRes.status,
    statusText: upstreamRes.statusText,
    headers: outHeaders,
  });
}
