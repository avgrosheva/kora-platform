"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { TopBar as KoraTopBar } from "@/components/kora/TopBar";
import { useActiveOrg } from "@/features/organizations/active-org-context";
import { useMembers } from "@/features/organizations/hooks";
import { useAuth } from "@/features/auth/auth-context";
import { CreateOrgDialog } from "@/features/organizations/components/create-org-dialog";

export function Topbar() {
  const router = useRouter();
  const { user, logout } = useAuth();
  const { organizations, activeOrg, setActiveOrgId } = useActiveOrg();
  const { data: members } = useMembers(activeOrg?.id);
  const [createOpen, setCreateOpen] = useState(false);

  const myRole = members?.find((m) => m.user_id === user?.id)?.role;

  return (
    <>
      <KoraTopBar
        organizations={organizations}
        currentOrgId={activeOrg?.id ?? ""}
        userEmail={user?.email ?? ""}
        userRole={myRole?.toUpperCase()}
        onSwitchOrg={setActiveOrgId}
        onCreateOrg={() => setCreateOpen(true)}
        onSignOut={logout}
        onAccountPrefs={() => router.push("/profile")}
      />
      <CreateOrgDialog open={createOpen} onOpenChange={setCreateOpen} />
    </>
  );
}
