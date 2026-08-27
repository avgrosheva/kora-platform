"use client";

import { createContext, useContext, useState, type ReactNode } from "react";

interface ChatWidgetContextValue {
  open: boolean;
  setOpen: (open: boolean) => void;
}

const ChatWidgetContext = createContext<ChatWidgetContextValue | null>(null);

/**
 * Lifts the floating chat widget's open/closed state out of the widget
 * itself so other screens (e.g. the Analysis tab's "Ask Kora" CTA) can
 * open it programmatically, not just its own toggle button.
 */
export function ChatWidgetProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  return <ChatWidgetContext.Provider value={{ open, setOpen }}>{children}</ChatWidgetContext.Provider>;
}

export function useChatWidget() {
  const ctx = useContext(ChatWidgetContext);
  if (!ctx) throw new Error("useChatWidget must be used within ChatWidgetProvider");
  return ctx;
}
