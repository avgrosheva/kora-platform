"use client";

import { toast } from "sonner";
import { CreateOrgModal } from "@/components/kora/CreateOrgModal";
import { useCreateOrganization } from "../hooks";
import { useActiveOrg } from "../active-org-context";

export function CreateOrgDialog({ open, onOpenChange }: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const createOrg = useCreateOrganization();
  const { setActiveOrgId } = useActiveOrg();

  const handleCreate = (values: { name: string; slug?: string }) => {
    if (!values.name.trim()) {
      toast.error("Name is required.");
      return;
    }
    createOrg.mutate(
      { name: values.name.trim(), slug: values.slug || undefined },
      {
        onSuccess: (newOrg) => {
          toast.success("Organization created.");
          // The generic "pick a valid stored org, else the first one"
          // effect in ActiveOrgProvider never switches here on its own:
          // whatever was already active stays valid (still in the
          // list), so it never re-evaluates which org should be active.
          setActiveOrgId(newOrg.id);
          onOpenChange(false);
        },
        onError: (error) => toast.error(error.message || "Could not create organization."),
      }
    );
  };

  return (
    <CreateOrgModal open={open} onClose={() => onOpenChange(false)} onCreate={handleCreate} />
  );
}
