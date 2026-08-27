"use client";

import { toast } from "sonner";
import { CreateOrgModal } from "@/components/kora/CreateOrgModal";
import { useCreateOrganization } from "../hooks";

export function CreateOrgDialog({ open, onOpenChange }: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const createOrg = useCreateOrganization();

  const handleCreate = (values: { name: string; slug?: string }) => {
    if (!values.name.trim()) {
      toast.error("Name is required.");
      return;
    }
    createOrg.mutate(
      { name: values.name.trim(), slug: values.slug || undefined },
      {
        onSuccess: () => {
          toast.success("Organization created.");
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
