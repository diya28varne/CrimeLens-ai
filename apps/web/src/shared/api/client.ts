import { appConfig } from "@/shared/config";
import { getAccessToken } from "@/shared/lib/auth-storage";
import { readStoredLocale } from "@/shared/i18n";

export class ApiError extends Error {
  status: number;
  code?: string;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

function currentLocale(): string {
  if (typeof window === "undefined") return "en";
  try {
    return readStoredLocale();
  } catch {
    return "en";
  }
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type") && init.body) {
    headers.set("Content-Type", "application/json");
  }
  const token = getAccessToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  const locale = currentLocale();
  headers.set(
    "Accept-Language",
    locale === "kn" ? "kn-IN,kn;q=0.9,en;q=0.5" : "en-IN,en;q=0.9",
  );
  headers.set("X-CrimeLens-Locale", locale);

  const response = await fetch(`${appConfig.apiBaseUrl}${path}`, {
    ...init,
    headers,
    credentials: "include",
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new ApiError(
      payload?.error?.message ?? `Request failed (${response.status})`,
      response.status,
      payload?.error?.code,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}
