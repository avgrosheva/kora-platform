import { apiClient } from "@/lib/api-client";
import type { ChatResponse, ChatV2Response } from "@/types/api";

export const chatApi = {
  ask: async (organizationId: string, question: string, topK?: number): Promise<ChatResponse> => {
    const { data } = await apiClient.post<ChatResponse>("/chat", {
      organization_id: organizationId,
      question,
      top_k: topK,
    });
    return data;
  },

  askV2: async (
    organizationId: string,
    question: string,
    documentId?: string
  ): Promise<ChatV2Response> => {
    const { data } = await apiClient.post<ChatV2Response>("/chat/v2", {
      organization_id: organizationId,
      document_id: documentId,
      question,
    });
    return data;
  },
};