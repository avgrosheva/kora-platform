"use client";

import { LogOut, User as UserIcon } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { useAuth } from "@/features/auth/auth-context";
import { OrgSwitcher } from "./org-switcher";

export function Topbar() {
  const { user, logout } = useAuth();

  const initials = (user?.full_name || user?.email || "?")
    .split(" ")
    .map((part) => part[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <header className="flex h-16 items-center justify-between border-b border-border/50 bg-background px-6">
      <OrgSwitcher />
      <DropdownMenu>
        <DropdownMenuTrigger className="flex items-center gap-2 rounded-full outline-none ring-offset-background focus-visible:ring-2 focus-visible:ring-ring">
        <Avatar className="h-8 w-8">
            <AvatarFallback className="bg-primary/10 text-xs text-primary">
            {initials}
            </AvatarFallback>
        </Avatar>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-56">
            <div className="px-2 py-1.5">
            <div className="font-medium">
                {user?.full_name || "Account"}
            </div>
            <div className="text-xs text-muted-foreground">
                {user?.email}
            </div>
            </div>
          <DropdownMenuSeparator />
          <DropdownMenuItem onSelect={() => (window.location.href = "/settings")}>
            <UserIcon className="mr-2 h-4 w-4" />
            Settings
          </DropdownMenuItem>
          <DropdownMenuItem
            onClick={logout}
            className="text-destructive focus:text-destructive"
          >
            <LogOut className="mr-2 h-4 w-4" />
            Log out
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  );
}