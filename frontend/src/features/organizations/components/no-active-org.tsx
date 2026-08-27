"use client";

import { useState } from "react";
import { EmptyState, GhostButton } from "@/components/kora/primitives";
import { CreateOrgDialog } from "./create-org-dialog";

/**
 * Shown on org-scoped screens (Members, Documents, Settings) when no
 * organization is selected -- either the user belongs to none yet, or
 * `activeOrgId` hasn't resolved. Portfolio's zero-org treatment is the
 * bigger, primary onboarding hero (`NoOrganizations` in
 * `components/kora/screens/Portfolio`); this is the compact form for
 * screens reached directly.
 */
export function NoActiveOrg() {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative z-10 max-w-[1200px] px-9 pb-24 pt-10">
      <EmptyState
        title="No organization selected"
        blurb="Create an organization to start uploading and analyzing companies."
        action={<GhostButton onClick={() => setOpen(true)}>+ CREATE ORGANIZATION</GhostButton>}
      />
      <CreateOrgDialog open={open} onOpenChange={setOpen} />
    </div>
  );
}
