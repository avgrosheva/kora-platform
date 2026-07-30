import { apiClient } from "@/lib/api-client";
import type { PortfolioResponse } from "@/types/api";

export const portfolioApi = {
  get: async (organizationId: string): Promise<PortfolioResponse> => {
    const { data } = await apiClient.get<PortfolioResponse>("/portfolio", {
      params: { organization_id: organizationId },
    });
    return data;
  },
};