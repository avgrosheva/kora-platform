"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { toast } from "sonner";
import { useActiveOrg } from "@/features/organizations/active-org-context";
import { useAskChat, useAskChatV2 } from "@/features/chat/hooks";
import { useChatWidget } from "@/features/chat/chat-widget-context";
import { useDocument } from "@/features/documents/hooks";
import { ChatWidget as KoraChatWidget } from "@/components/kora/ChatWidget";
import type { ChatMessage as KoraChatMessage } from "@/components/kora/types";
import type { ChatMessage } from "@/features/chat/types";
import type { ChatSource, ToolCallRecord } from "@/types/api";

const EMPTY_CONVERSATION_SUGGESTIONS = [
  "What are the biggest risks?",
  "Why this score?",
  "What should I ask the founders?",
  "What's missing?",
];

const TOOL_LABELS: Record<string, string> = {
  search_document_chunks: "Searched documents",
  get_financial_time_series: "Fetched time series",
  calculate_metric: "Calculated metric",
  get_missing_information: "Checked missing info",
};

function sourceLabel(source: ChatSource): string {
  return `Excerpt ${source.chunk_index + 1} · ${(source.similarity_score * 100).toFixed(0)}%`;
}

function toolLabel(call: ToolCallRecord): string {
  return "⚙ " + (TOOL_LABELS[call.tool_name] ?? call.tool_name);
}

/** Maps our real chat messages onto the design system's simpler shape.
 * Tool calls have no dedicated slot in the new widget, so they're folded
 * into the same source-chip row as citations rather than dropped. */
function toKoraMessages(messages: ChatMessage[]): KoraChatMessage[] {
  return messages.map((m) => ({
    id: m.id,
    role: m.role,
    text: m.content,
    sources: [
      ...(m.sources ?? []).map((s) => ({ label: sourceLabel(s) })),
      ...(m.toolCalls ?? []).map((c) => ({ label: toolLabel(c) })),
    ],
  }));
}

/**
 * Global floating chat widget, mounted once in `AppShell` so it persists
 * across route navigation. Scoped to the currently active organization
 * -- conversation state resets whenever the active org changes, so a
 * question never appears to answer for the wrong company's data.
 */
export function ChatWidget() {
  const { activeOrg } = useActiveOrg();
  const pathname = usePathname();
  const documentMatch = /^\/documents\/([^/]+)/.exec(pathname ?? "");
  const { data: activeDocument } = useDocument(documentMatch ? documentMatch[1] : undefined);

  const { open, setOpen } = useChatWidget();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [useTools, setUseTools] = useState(false);
  const askChat = useAskChat();
  const askChatV2 = useAskChatV2();
  const activeOrgIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (activeOrgIdRef.current !== null && activeOrgIdRef.current !== (activeOrg?.id ?? null)) {
      setMessages([]);
    }
    activeOrgIdRef.current = activeOrg?.id ?? null;
  }, [activeOrg?.id]);

  const isPending = askChat.isPending || askChatV2.isPending;

  const handleSend = (text: string) => {
    const question = text.trim();
    if (!question || !activeOrg) return;

    const userMessage: ChatMessage = { id: crypto.randomUUID(), role: "user", content: question };
    setMessages((prev) => [...prev, userMessage]);

    // On failure, the user's own question stays in the transcript with
    // a visible error reply rather than being silently removed --
    // vanishing it (the old behavior) is indistinguishable from "the
    // message was never sent," which is exactly what made a slow-but-
    // legitimate analytical answer look like a hang instead of a
    // request that was still, correctly, in flight.
    const handleError = (error: Error) => {
      toast.error(error.message || "Chat request failed.");
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: "assistant", content: error.message || "Sorry, that request failed. Please try again." },
      ]);
    };

    if (useTools) {
      askChatV2.mutate(
        { organizationId: activeOrg.id, question },
        {
          onSuccess: (response) => {
            setMessages((prev) => [
              ...prev,
              {
                id: crypto.randomUUID(), role: "assistant", content: response.answer,
                sources: response.sources, toolCalls: response.tool_calls, modelUsed: response.model_used,
              },
            ]);
          },
          onError: handleError,
        }
      );
      return;
    }

    askChat.mutate(
      { organizationId: activeOrg.id, question },
      {
        onSuccess: (response) => {
          setMessages((prev) => [
            ...prev,
            { id: crypto.randomUUID(), role: "assistant", content: response.answer, sources: response.sources, modelUsed: response.model_used },
          ]);
        },
        onError: handleError,
      }
    );
  };

  if (!activeOrg) return null;

  const contextLabel = activeDocument
    ? `${activeOrg.name.toUpperCase()} · ${activeDocument.original_filename.toUpperCase()}`
    : activeOrg.name.toUpperCase();

  return (
    <KoraChatWidget
      open={open}
      onToggle={() => setOpen(!open)}
      messages={toKoraMessages(messages)}
      contextLabel={contextLabel}
      mode={useTools ? "ANALYTICAL" : "STANDARD"}
      onModeToggle={() => setUseTools((v) => !v)}
      isThinking={isPending}
      thinkingLabel={useTools && askChatV2.isPending ? "ANALYZING — CAN TAKE A MINUTE OR TWO…" : undefined}
      suggestions={messages.length === 0 ? EMPTY_CONVERSATION_SUGGESTIONS : undefined}
      placeholder={`Ask about ${activeOrg.name}'s indexed documents…`}
      onSend={handleSend}
    />
  );
}
