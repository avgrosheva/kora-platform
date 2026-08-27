"use client";

import { toast } from "sonner";
import { GhostButton } from "@/components/kora/primitives";
import { useChangeRole, useRemoveMember } from "../hooks";
import type { MembershipRead, MembershipRole } from "@/types/api";

const ASSIGNABLE_ROLES: MembershipRole[] = ["owner", "admin", "member"];

/**
 * Kora's `Members` screen exposes only a single `onMemberAction(id)`
 * callback per row -- no built-in menu, unlike the shadcn version this
 * replaces. This modal is the external UI that callback opens, styled
 * to match `CreateOrgModal`'s chrome. Gating mirrors the backend
 * exactly (organization_service.py): change_role is owner-only;
 * remove_member allows owner/admin for anyone, and anyone may remove
 * themselves (leave).
 */
export function MemberActionsModal({ member, organizationId, myRole, currentUserId, onClose }: {
  member: MembershipRead | null;
  organizationId: string;
  myRole?: MembershipRole;
  currentUserId?: string;
  onClose: () => void;
}) {
  const changeRole = useChangeRole(organizationId);
  const removeMember = useRemoveMember(organizationId);

  if (!member) return null;

  const isSelf = member.user_id === currentUserId;
  const canChangeRoles = myRole === "owner";
  const canRemove = myRole === "owner" || myRole === "admin" || isSelf;

  const handleChangeRole = (role: MembershipRole) => {
    changeRole.mutate(
      { userId: member.user_id, input: { role } },
      {
        onSuccess: () => {
          toast.success(`Role updated to ${role}.`);
          onClose();
        },
        onError: (error) => toast.error(error.message),
      }
    );
  };

  const handleRemove = () => {
    removeMember.mutate(member.user_id, {
      onSuccess: () => {
        toast.success(isSelf ? "You left the organization." : "Member removed.");
        onClose();
      },
      onError: (error) => toast.error(error.message),
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
        className="kora-rise w-[min(360px,100%)] overflow-hidden rounded-2xl border border-white/[0.09] bg-gradient-to-b from-ink-850 to-ink-800 shadow-modal"
      >
        <header className="flex items-center justify-between border-b border-white/[0.07] bg-gradient-to-r from-accent/10 to-transparent px-5 py-[18px]">
          <div className="min-w-0">
            <h2 className="truncate text-sm font-semibold">{member.email}</h2>
            <div className="mt-[3px] font-mono text-[9px] tracking-badge text-fg-faint">{member.role.toUpperCase()}</div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="flex h-6 w-6 shrink-0 cursor-pointer items-center justify-center rounded-[7px] border border-white/[0.09] bg-transparent text-[13px] text-fg-muted hover:border-white/20 hover:text-fg"
          >
            ×
          </button>
        </header>

        <div className="flex flex-col gap-2 p-3">
          {!canChangeRoles && !canRemove && (
            <p className="px-2 py-3 text-center text-[12.5px] text-fg-dim">No actions available.</p>
          )}
          {canChangeRoles &&
            ASSIGNABLE_ROLES.filter((r) => r !== member.role).map((role) => (
              <GhostButton key={role} tone="neutral" className="w-full text-left" onClick={() => handleChangeRole(role)}>
                MAKE {role.toUpperCase()}
              </GhostButton>
            ))}
          {canRemove && (
            <GhostButton tone="danger" className="w-full text-left" onClick={handleRemove}>
              {isSelf ? "LEAVE ORGANIZATION" : "REMOVE MEMBER"}
            </GhostButton>
          )}
        </div>
      </div>
    </div>
  );
}
