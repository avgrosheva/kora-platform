"use client";

/**
 * Global authentication state: current user, login/logout actions, and
 * loading state while the initial session check runs. Wraps the app in
 * `providers.tsx`. Route protection itself lives in
 * `app/(protected)/layout.tsx`, which reads `useAuth()`.
 */

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { authApi } from "./api";
import { setStoredToken } from "@/lib/api-client";
import type { UserRead } from "@/types/api";
import type { LoginCredentials } from "./types";

interface AuthContextValue {
  user: UserRead | null;
  isLoading: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserRead | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const token = typeof window !== "undefined" ? window.localStorage.getItem("kora_access_token") : null;
    if (!token) {
      setIsLoading(false);
      return;
    }
    authApi
      .me()
      .then(setUser)
      .catch(() => setStoredToken(null))
      .finally(() => setIsLoading(false));
  }, []);

  const login = async (credentials: LoginCredentials) => {
    const { access_token } = await authApi.login(credentials);
    setStoredToken(access_token);
    const currentUser = await authApi.me();
    setUser(currentUser);
    router.push("/portfolio");
  };

  const logout = () => {
    setStoredToken(null);
    setUser(null);
    router.push("/login");
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider.");
  }
  return context;
}