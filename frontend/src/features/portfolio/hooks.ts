"use client";

import { useQuery } from "@tanstack/react-query";
import { portfolioApi } from "./api";

export function usePortfolio(organizationId: string | null) {
  return useQuery({
    queryKey: ["portfolio", organizationId],
    queryFn: () => portfolioApi.get(organizationId as string),
    enabled: !!organizationId,
  });
}