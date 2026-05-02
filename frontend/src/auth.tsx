import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api, clearTokens, setTokens, getAccessToken, setOnSessionExpired } from "./api";

type User = { id: string; email: string; name: string; role: string; level?: string | null; tutor_id?: string | null };

type AuthCtx = {
  user: User | null | undefined; // undefined = checking
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

const Ctx = createContext<AuthCtx>({} as any);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null | undefined>(undefined);

  // Registra callback global para sessão expirada (refresh falhou)
  useEffect(() => {
    setOnSessionExpired(() => setUser(null));
    return () => setOnSessionExpired(null);
  }, []);

  useEffect(() => {
    (async () => {
      const token = await getAccessToken();
      if (!token) return setUser(null);
      try {
        const { data } = await api.get("/auth/me");
        setUser(data);
      } catch {
        await clearTokens();
        setUser(null);
      }
    })();
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const { data } = await api.post("/auth/login", { email, password });
    // Backend agora retorna access_token + refresh_token (e mantém legacy `token`)
    const access: string = data.access_token || data.token;
    const refresh: string | undefined = data.refresh_token;
    await setTokens(access, refresh ?? null);
    setUser(data.user);
  }, []);

  const logout = useCallback(async () => {
    try { await api.post("/auth/logout"); } catch {}
    await clearTokens();
    setUser(null);
  }, []);

  return <Ctx.Provider value={{ user, login, logout }}>{children}</Ctx.Provider>;
}

export const useAuth = () => useContext(Ctx);
