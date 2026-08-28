"use client";

import { useState } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { createQueryClient } from "@/lib/query-client";
import { AuthProvider } from "@/features/auth/auth-context";
import { ActiveOrgProvider } from "@/features/organizations/active-org-context";
import { Toaster } from "sonner";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(createQueryClient);

  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ActiveOrgProvider>
          {children}
          <Toaster
            theme="dark"
            position="top-right"
            toastOptions={{
              unstyled: true,
              classNames: {
                toast:
                  "kora-slide-in flex items-start gap-[11px] rounded-[11px] border px-4 py-[13px] font-sans text-[12.5px] shadow-[0_10px_40px_-14px_rgba(0,0,0,0.6)] " +
                  "border-white/[0.09] bg-gradient-to-r from-white/[0.05] to-ink-850/95 text-fg-secondary",
                title: "font-medium",
                description: "text-fg-dim",
                success:
                  "!border-good/30 !bg-gradient-to-r !from-good/[0.14] !to-ink-850/95 !text-good-wash shadow-[0_0_40px_-14px_rgba(70,217,160,0.6)]",
                error:
                  "!border-danger/30 !bg-gradient-to-r !from-danger/[0.14] !to-ink-850/95 !text-danger-soft shadow-[0_0_40px_-14px_rgba(255,92,92,0.6)]",
                warning:
                  "!border-warn/30 !bg-gradient-to-r !from-warn/[0.14] !to-ink-850/95 !text-warn-wash shadow-[0_0_40px_-14px_rgba(242,178,76,0.6)]",
              },
            }}
          />
        </ActiveOrgProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}