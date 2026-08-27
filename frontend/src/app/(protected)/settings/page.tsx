"use client";

import { useState } from "react";
import { toast } from "sonner";
import { useActiveOrg } from "@/features/organizations/active-org-context";
import { useUpdateOrganization } from "@/features/organizations/hooks";
import { updateOrgSchema } from "@/features/organizations/schemas";
import { Settings as KoraSettings } from "@/components/kora/screens/Settings";
import { NoActiveOrg } from "@/features/organizations/components/no-active-org";
import { DeleteOrgModal } from "@/features/organizations/components/delete-org-modal";

export default function SettingsPage() {
  const { activeOrg, isLoading } = useActiveOrg();
  const updateOrg = useUpdateOrganization(activeOrg?.id ?? "");
  const [deleteOpen, setDeleteOpen] = useState(false);

  if (isLoading) {
    return <div className="relative z-10 p-9 text-sm text-fg-dim">Loading…</div>;
  }

  if (!activeOrg) {
    return <NoActiveOrg />;
  }

  const handleSave = (values: { name: string; slug: string }) => {
    const result = updateOrgSchema.safeParse(values);
    if (!result.success) {
      toast.error(result.error.issues[0]?.message ?? "Invalid organization details.");
      return;
    }
    updateOrg.mutate(result.data, {
      onSuccess: () => toast.success("Organization updated."),
      onError: (error) => toast.error(error.message || "Could not update organization."),
    });
  };

  return (
    <>
      {/* key forces a remount when the active org changes, so the
          screen's own local name/slug state (no prop-sync effect in
          the shipped component) always re-initializes from the new org. */}
      <KoraSettings
        key={activeOrg.id}
        organization={activeOrg}
        onSave={handleSave}
        onDelete={() => setDeleteOpen(true)}
      />
      <DeleteOrgModal open={deleteOpen} organization={activeOrg} onClose={() => setDeleteOpen(false)} />
    </>
  );
}
