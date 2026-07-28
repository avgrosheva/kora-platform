"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { useOrganizations } from "./hooks";
import type { OrganizationRead } from "@/types/api";

const STORAGE_KEY = "kora_active_org_id";

interface ActiveOrgContextValue {
  organizations: OrganizationRead[];
  activeOrg: OrganizationRead | null;
  setActiveOrgId: (id: string) => void;
  isLoading: boolean;
}

const ActiveOrgContext = createContext<ActiveOrgContextValue | undefined>(undefined);

export function ActiveOrgProvider({ children }: { children: ReactNode }) {
  const { data: organizations = [], isLoading } = useOrganizations();
  const [activeOrgId, setActiveOrgIdState] = useState<string | null>(null);

  useEffect(() => {
    if (organizations.length === 0) return;
    const stored = window.localStorage.getItem(STORAGE_KEY);
    const validStored = organizations.find((o) => o.id === stored);
    setActiveOrgIdState(validStored ? validStored.id : organizations[0].id);
  }, [organizations]);

  const setActiveOrgId = (id: string) => {
    window.localStorage.setItem(STORAGE_KEY, id);
    setActiveOrgIdState(id);
  };

  const activeOrg = organizations.find((o) => o.id === activeOrgId) ?? null;

  return (
    <ActiveOrgContext.Provider value={{ organizations, activeOrg, setActiveOrgId, isLoading }}>
      {children}
    </ActiveOrgContext.Provider>
  );
}

export function useActiveOrg(): ActiveOrgContextValue {
  const context = useContext(ActiveOrgContext);
  if (!context) {
    throw new Error("useActiveOrg must be used within an ActiveOrgProvider.");
  }
  return context;
}