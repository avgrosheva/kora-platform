"use client";

import { User, Building2, LogOut, Info } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/features/auth/auth-context";
import { useActiveOrg } from "@/features/organizations/active-org-context";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RoleBadge } from "@/components/shared/role-badge";
import { ChangePasswordNote } from "@/features/auth/components/change-password-note";
import { useMembers } from "@/features/organizations/hooks";
import { format } from "date-fns";

export default function SettingsPage() {
  const { user, logout } = useAuth();
  const { activeOrg } = useActiveOrg();
  const { data: members } = useMembers(activeOrg?.id);

  const myMembership = members?.find((m) => m.user_id === user?.id);

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground">Manage your account and preferences.</p>
      </div>

      <Card className="border-border/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <User className="h-4 w-4 text-muted-foreground" />
            Account
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <p className="text-xs text-muted-foreground">Email</p>
              <p className="mt-1 text-sm">{user?.email}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Full name</p>
              <p className="mt-1 text-sm">{user?.full_name || "—"}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Account created</p>
              <p className="mt-1 text-sm">
                {user ? format(new Date(user.created_at), "PPP") : "—"}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Status</p>
              <p className="mt-1 text-sm">{user?.is_active ? "Active" : "Inactive"}</p>
            </div>
          </div>
          <ChangePasswordNote />
        </CardContent>
      </Card>

      {activeOrg && (
        <Card className="border-border/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Building2 className="h-4 w-4 text-muted-foreground" />
              Current Organization
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">{activeOrg.name}</p>
                <p className="text-xs text-muted-foreground">/{activeOrg.slug}</p>
              </div>
              {myMembership && <RoleBadge role={myMembership.role} />}
            </div>
            <p className="text-xs text-muted-foreground">
              To manage members, roles, or invitations, visit the{" "}
              <a href={`/organizations/${activeOrg.id}`} className="text-primary hover:underline">
                organization page
              </a>
              .
            </p>
          </CardContent>
        </Card>
      )}

      <Card className="border-destructive/30">
        <CardHeader>
          <CardTitle className="text-base text-destructive">Session</CardTitle>
        </CardHeader>
        <CardContent>
          <button
            type="button"
            onClick={() => {
              logout();
              toast.success("Logged out.");
            }}
            className="flex h-9 items-center gap-2 rounded-md border border-destructive/50 px-4 text-sm font-medium text-destructive hover:bg-destructive/10"
          >
            <LogOut className="h-4 w-4" />
            Log out
          </button>
        </CardContent>
      </Card>
    </div>
  );
}