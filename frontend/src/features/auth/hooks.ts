"use client";

import { useMutation } from "@tanstack/react-query";
import { useAuth } from "./auth-context";
import type { LoginCredentials } from "./types";

/** Wraps `useAuth().login` in a TanStack Query mutation for loading/error state in forms. */
export function useLoginMutation() {
  const { login } = useAuth();
  return useMutation({
    mutationFn: (credentials: LoginCredentials) => login(credentials),
  });
}