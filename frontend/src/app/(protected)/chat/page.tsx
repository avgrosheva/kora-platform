"use client";

import { useState, useRef, useEffect } from "react";
import { Send, MessageSquare } from "lucide-react";
import { toast } from "sonner";
import { useActiveOrg } from "@/features/organizations/active-org-context";
import { useAskChat } from "@/features/chat/hooks";
import { ChatMessageBubble } from "@/features/chat/components/chat-message-bubble";
import { SourcesPanel } from "@/features/chat/components/sources-panel";
import { EmptyState } from "@/components/shared/empty-state";
import type { ChatMessage } from "@/features/chat/types";
import type { ChatSource } from "@/types/api";

export default function ChatPage() {
  const { activeOrg } = useActiveOrg();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [latestSources, setLatestSources] = useState<ChatSource[]>([]);
  const askChat = useAskChat();
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = () => {
    const question = input.trim();
    if (!question || !activeOrg) return;

    const userMessage: ChatMessage = { id: crypto.randomUUID(), role: "user", content: question };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");

    askChat.mutate(
      { organizationId: activeOrg.id, question },
      {
        onSuccess: (response) => {
          setMessages((prev) => [
            ...prev,
            {
              id: crypto.randomUUID(),
              role: "assistant",
              content: response.answer,
              sources: response.sources,
              modelUsed: response.model_used,
            },
          ]);
          setLatestSources(response.sources);
        },
        onError: (error) => {
          toast.error(error.message || "Chat request failed.");
          setMessages((prev) => prev.slice(0, -1));
        },
      }
    );
  };

  if (!activeOrg) {
    return (
      <EmptyState icon={MessageSquare} title="No organization selected" description="Select an organization to start chatting." />
    );
  }

  return (
    <div className="flex h-[calc(100vh-8rem)] gap-6">
      <div className="flex flex-1 flex-col">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Chat</h1>
          <p className="text-sm text-muted-foreground">
            Ask questions about {activeOrg.name}'s indexed documents.
          </p>
        </div>

        <div className="mt-4 flex-1 space-y-4 overflow-y-auto pr-2">
          {messages.length === 0 ? (
            <EmptyState
              icon={MessageSquare}
              title="No messages yet"
              description="Ask something like “What was Acme's ARR last quarter?”"
            />
          ) : (
            messages.map((message) => <ChatMessageBubble key={message.id} message={message} />)
          )}
          {askChat.isPending && (
            <ChatMessageBubble
              message={{ id: "pending", role: "assistant", content: "Thinking…" }}
            />
          )}
          <div ref={scrollRef} />
        </div>

        <div className="mt-4 flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="Ask a question…"
            disabled={askChat.isPending}
            className="h-10 flex-1 rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
          />
          <button
            type="button"
            onClick={handleSend}
            disabled={askChat.isPending || !input.trim()}
            className="flex h-10 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground shadow-sm hover:bg-primary/90 disabled:opacity-50"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className="hidden w-72 shrink-0 lg:block">
        <SourcesPanel sources={latestSources} />
      </div>
    </div>
  );
}