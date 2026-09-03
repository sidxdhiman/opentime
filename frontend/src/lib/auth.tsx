"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import { api, type User } from "./api";
import { onUnauthorized } from "@/lib/http";

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const tokens = api.getStoredTokens();
    if (!tokens) {
      setIsLoading(false);
      return;
    }

    let active = true;
    api
      .me()
      .then(setUser)
      .catch(() => api.clearTokens())
      .finally(() => {
        if (active) setIsLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  // Global 401 (session-expired) handling: any authenticated request that
  // comes back 401 clears the session once, so expired sessions and stale
  // cross-user requests can never keep the user half-logged-in.
  useEffect(() => {
    return onUnauthorized(() => {
      api.clearTokens();
      setUser(null);
      router.push("/login");
    });
  }, [router]);

  const login = useCallback(
    async (email: string, password: string) => {
      const response = await api.login({ email, password });
      api.storeTokens(response.tokens);
      setUser(response.user);
      router.push("/dashboard");
    },
    [router],
  );

  const register = useCallback(
    async (email: string, password: string, fullName?: string) => {
      const response = await api.register({ email, password, full_name: fullName });
      api.storeTokens(response.tokens);
      setUser(response.user);
      // New users go through onboarding before the dashboard
      router.push("/onboarding");
    },
    [router],
  );

  const logout = useCallback(async () => {
    await api.logout();
    setUser(null);
    router.push("/login");
  }, [router]);

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
