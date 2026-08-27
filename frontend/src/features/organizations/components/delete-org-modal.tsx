"use client";

import { toast } from "sonner";
import { useRouter } from "next/navigation";
import { GhostButton } from "@/components/kora/primitives";
import { useDeleteOrganization } from "../hooks";
import type { OrganizationRead } from "@/types/api";

/**
 * Kora's `Settings` screen calls `onDelete` directly with no
 * confirmation step built in -- deleting an organization is
 * destructive and irreversible, so this is the confirmation UI that
 * callback opens instead of deleting immediately. Styled to match
 * `CreateOrgModal`'s chrome.
 */
export function DeleteOrgModal({ open, organization, onClose }: {
  open: boolean;
  organization: OrganizationRead;
  onClose: () => void;
}) {
  const router = useRouter();
  const deleteOrg = useDeleteOrganization();

  if (!open) return null;

  const handleDelete = () => {
    deleteOrg.mutate(organization.id, {
      onSuccess: () => {
        toast.success("Organization deleted.");
        onClose();
        router.push("/portfolio");
      },
      onError: (error) => toast.error(error.message || "Could not delete organization."),
    });
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-[60] flex items-center justify-center bg-[#030508]/75 p-6 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="kora-rise w-[min(420px,100%)] overflow-hidden rounded-2xl border border-danger/[0.3] bg-gradient-to-b from-ink-850 to-ink-800 shadow-modal"
      >
        <header className="flex items-center justify-between border-b border-white/[0.07] bg-gradient-to-r from-danger/10 to-transparent px-5 py-[18px]">
          <h2 className="text-sm font-semibold text-danger-soft">Delete {organization.name}?</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="flex h-6 w-6 shrink-0 cursor-pointer items-center justify-center rounded-[7px] border border-white/[0.09] bg-transparent text-[13px] text-fg-muted hover:border-white/20 hover:text-fg"
          >
            ×
          </button>
        </header>

        <div className="p-5">
          <p className="m-0 text-[13px] leading-relaxed text-fg-muted [text-wrap:pretty]">
            This permanently deletes the organization, its documents, and all associated data.
            This action cannot be undone. Only the organization owner can do this.
          </p>
        </div>

        <footer className="flex justify-end gap-[9px] px-5 pb-5">
          <GhostButton tone="neutral" onClick={onClose}>CANCEL</GhostButton>
          <GhostButton tone="danger" onClick={handleDelete}>
            {deleteOrg.isPending ? "DELETING…" : "DELETE ORGANIZATION"}
          </GhostButton>
        </footer>
      </div>
    </div>
  );
}
