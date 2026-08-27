"use client";

import { usePathname, useRouter } from "next/navigation";
import { Sidebar as KoraSidebar } from "@/components/kora/Sidebar";
import type { ScreenId } from "@/components/kora/types";

const SCREEN_ROUTES: Record<ScreenId, string> = {
  portfolio: "/portfolio",
  "no-org": "/portfolio",
  documents: "/documents",
  members: "/members",
  settings: "/settings",
  document: "/documents",
};

function screenIdForPathname(pathname: string): ScreenId {
  if (pathname.startsWith("/documents/")) return "document";
  if (pathname.startsWith("/documents")) return "documents";
  if (pathname.startsWith("/members")) return "members";
  if (pathname.startsWith("/settings")) return "settings";
  return "portfolio";
}

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  return (
    <KoraSidebar
      active={screenIdForPathname(pathname ?? "")}
      onNavigate={(id) => router.push(SCREEN_ROUTES[id])}
    />
  );
}
