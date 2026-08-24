import type { ChatSource, ToolCallRecord } from "@/types/api";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: ChatSource[];
  toolCalls?: ToolCallRecord[];
  modelUsed?: string;
}