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
    const { data } = await apiClient.post<ChatV2Response>(
      "/chat/v2",
      { organization_id: organizationId, document_id: documentId, question },
      // Tool-calling chat runs up to MAX_TOOL_ROUNDS=4 sequential LLM
      // calls server-side (chat_v2_service.py), each with its own 60s
      // budget -- worst case ~240s, well past apiClient's shared 60s
      // default built for single-call endpoints. That mismatch is what
      // silently killed slow-but-legitimate analytical answers before
      // the backend ever got a chance to finish.
      { timeout: 240_000 }
    );
    return data;
  },
};