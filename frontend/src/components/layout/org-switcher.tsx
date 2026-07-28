"use client";

import { Building2, ChevronsUpDown } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { useActiveOrg } from "@/features/organizations/active-org-context";
import { Skeleton } from "@/components/ui/skeleton";

export function OrgSwitcher() {
  const { organizations, activeOrg, setActiveOrgId, isLoading } = useActiveOrg();

  if (isLoading) {
    return <Skeleton className="h-9 w-40" />;
  }

  if (organizations.length === 0) {
    return (
      <span className="text-sm text-muted-foreground">No organizations</span>
    );
  }

  return (
    <DropdownMenu>
        <DropdownMenuTrigger
        className="flex h-9 w-48 items-center justify-between rounded-md border border-input bg-background px-3 text-sm font-medium shadow-sm outline-none hover:bg-accent hover:text-accent-foreground focus-visible:ring-2 focus-visible:ring-ring"
        >
        <span className="flex items-center gap-2 truncate">
            <Building2 className="h-4 w-4 shrink-0" />
            <span className="truncate">
            {activeOrg?.name ?? "Select organization"}
            </span>
        </span>

        <ChevronsUpDown className="h-4 w-4 shrink-0 opacity-50" />
        </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-48">
        {organizations.map((org) => (
          <DropdownMenuItem key={org.id} onClick={() => setActiveOrgId(org.id)}>
            {org.name}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}