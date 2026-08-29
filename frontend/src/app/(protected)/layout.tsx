"use client";

/**
 * Wraps every route under (protected). Redirects to /login if there is
 * no authenticated user once the initial session check completes.
 */

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/features/auth/auth-context";
import { AppShell } from "@/components/layout/app-shell";

export default function ProtectedLayout({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !user) {
      router.replace("/login");
    }
  }, [isLoading, user, router]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center gap-3 bg-ink-950">
        <span className="kora-blink h-[7px] w-[7px] rounded-full bg-accent-bright shadow-[0_0_12px_2px_rgba(77,141,255,0.7)]" />
        <span className="font-mono text-[11px] tracking-kicker text-fg-dim">LOADING…</span>
      </div>
    );
  }

  if (!user) return null;

  return <AppShell>{children}</AppShell>;
}