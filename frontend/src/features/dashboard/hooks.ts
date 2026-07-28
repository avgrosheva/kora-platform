"use client";

import { useQuery } from "@tanstack/react-query";
import { dashboardApi } from "./api";

export function useDashboard(organizationId: string | null) {
  return useQuery({
    queryKey: ["dashboard", organizationId],
    queryFn: () => dashboardApi.get(organizationId as string),
    enabled: !!organizationId,
  });
}