import { apiClient } from "@/lib/api-client";
import type { ChatResponse } from "@/types/api";

export const chatApi = {
  ask: async (organizationId: string, question: string, topK?: number): Promise<ChatResponse> => {
    const { data } = await apiClient.post<ChatResponse>("/chat", {
      organization_id: organizationId,
      question,
      top_k: topK,
    });
    return data;
  },
};