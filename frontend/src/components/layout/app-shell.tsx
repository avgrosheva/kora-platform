"use client";

import { Sidebar } from "./sidebar";
import { Topbar } from "./topbar";
import { ChatWidget } from "@/features/chat/components/chat-widget";
import { ChatWidgetProvider } from "@/features/chat/chat-widget-context";
import { FlowLines } from "@/components/kora/FlowLines";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <ChatWidgetProvider>
      <div className="relative flex min-h-screen overflow-hidden bg-ink-950 font-sans text-fg">
        <Sidebar />
        <main className="relative flex min-w-0 flex-1 flex-col">
          <Topbar />
          <div className="relative flex-1 overflow-y-auto">
            <FlowLines />
            {children}
          </div>
        </main>
        <ChatWidget />
      </div>
    </ChatWidgetProvider>
  );
}
