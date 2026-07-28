import { apiClient } from "@/lib/api-client";
import type { DashboardResponse } from "@/types/api";

export const dashboardApi = {
  get: async (organizationId: string): Promise<DashboardResponse> => {
    const { data } = await apiClient.get<DashboardResponse>("/dashboard", {
      params: { organization_id: organizationId },
    });
    return data;
  },
};