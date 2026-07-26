/** Browser-safe open-demo tokens (no Node crypto). Works on Vercel without a backend. */

export type ClientDemoUser = {
  id: string;
  email: string;
  full_name: string;
  status: "active";
};

const PREFIX = "cldemo.";

function b64urlEncode(text: string): string {
  const bytes = new TextEncoder().encode(text);
  let bin = "";
  bytes.forEach((b) => {
    bin += String.fromCharCode(b);
  });
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

function b64urlDecode(value: string): string {
  const padded = value.replace(/-/g, "+").replace(/_/g, "/");
  const pad = padded.length % 4 === 0 ? "" : "=".repeat(4 - (padded.length % 4));
  const bin = atob(padded + pad);
  const bytes = Uint8Array.from(bin, (c) => c.charCodeAt(0));
  return new TextDecoder().decode(bytes);
}

export function displayNameFromEmail(email: string): string {
  const local = email.split("@", 1)[0] ?? "guest";
  const cleaned = local.replace(/[._]+/g, " ").trim();
  return cleaned ? cleaned.replace(/\b\w/g, (c) => c.toUpperCase()) : "CrimeLens Guest";
}

export function isClientDemoToken(token: string | null | undefined): boolean {
  return Boolean(token && token.startsWith(PREFIX));
}

export function createClientDemoToken(email: string): string {
  const normalized = email.toLowerCase().trim();
  const payload = {
    id: crypto.randomUUID(),
    email: normalized,
    full_name: displayNameFromEmail(normalized),
    status: "active",
    exp: Date.now() + 7 * 24 * 60 * 60 * 1000,
    type: "demo",
  };
  return `${PREFIX}${b64urlEncode(JSON.stringify(payload))}.client`;
}

export function parseClientDemoToken(token: string): ClientDemoUser | null {
  if (!token.startsWith(PREFIX)) return null;
  const raw = token.slice(PREFIX.length);
  const body = raw.includes(".") ? raw.slice(0, raw.lastIndexOf(".")) : raw;
  try {
    const payload = JSON.parse(b64urlDecode(body)) as {
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
      full_name: payload.full_name || displayNameFromEmail(payload.email),
      status: "active",
    };
  } catch {
    return null;
  }
}
