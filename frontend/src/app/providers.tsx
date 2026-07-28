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
          <Toaster theme="dark" position="top-right" richColors />
        </ActiveOrgProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}