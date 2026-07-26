"use client";

import { useCallback, useEffect, useState } from "react";

import { apiFetch } from "@/shared/api/client";
import { clearAccessToken } from "@/shared/lib/auth-storage";
import { appConfig } from "@/shared/config";

export type AuthUser = {
  id: string;
  email: string;
  full_name: string;
  status: string;
};

type AuthState = {
  loading: boolean;
  user: AuthUser | null;
  refresh: () => Promise<void>;
  signOut: () => Promise<void>;
};

/** Resolves signed-in state from session cookie and/or bearer token. */
export function useAuthSession(): AuthState {
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState<AuthUser | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiFetch<{ data: { user: AuthUser } }>("/auth/me");
      setUser(res.data.user);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const signOut = useCallback(async () => {
    try {
      await fetch(`${appConfig.apiBaseUrl}/auth/logout`, {
        method: "POST",
        credentials: "include",
      });
    } catch {
      // still clear local session
    }
    clearAccessToken();
    setUser(null);
    window.location.assign("/login");
  }, []);

  return { loading, user, refresh, signOut };
}
