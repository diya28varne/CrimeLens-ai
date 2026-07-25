const ACCESS_TOKEN_KEY = "cl_access_token";

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem(ACCESS_TOKEN_KEY);
}

export function setAccessToken(token: string | null): void {
  if (typeof window === "undefined") return;
  if (!token) {
    sessionStorage.removeItem(ACCESS_TOKEN_KEY);
    return;
  }
  sessionStorage.setItem(ACCESS_TOKEN_KEY, token);
}

export function clearAccessToken(): void {
  setAccessToken(null);
}
