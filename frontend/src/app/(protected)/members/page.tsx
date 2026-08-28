"use client";

import { useState } from "react";
import { format } from "date-fns";
import { useActiveOrg } from "@/features/organizations/active-org-context";
import { useAuth } from "@/features/auth/auth-context";
import { useMembers, useInvitations } from "@/features/organizations/hooks";
import { Members as KoraMembers } from "@/components/kora/screens/Members";
import type { Member as KoraMember } from "@/components/kora/types";
import { NoActiveOrg } from "@/features/organizations/components/no-active-org";
import { InviteMemberDialog } from "@/features/organizations/components/invite-member-dialog";
import { MemberActionsModal } from "@/features/organizations/components/member-actions-modal";
import type { InvitationRow } from "@/components/kora/screens/Members";
import type { InvitationRead } from "@/features/organizations/types";
import type { MembershipRead } from "@/types/api";

function toKoraMember(m: MembershipRead, currentUserId?: string): KoraMember {
  return {
    id: m.user_id,
    email: m.email,
    role: m.role,
    joinedAt: format(new Date(m.created_at), "MMM d, yyyy"),
    isCurrentUser: m.user_id === currentUserId,
  };
}

function toKoraInvitation(i: InvitationRead): InvitationRow {
  const status: InvitationRow["status"] = i.accepted_at
    ? "accepted"
    : new Date(i.expires_at) < new Date()
      ? "expired"
      : "pending";
  return {
    id: i.id,
    email: i.email,
    sentAt: format(new Date(i.created_at), "MMM d, yyyy"),
    status,
  };
}

export default function MembersPage() {
  const { user } = useAuth();
  const { activeOrg, isLoading: orgsLoading } = useActiveOrg();
  const { data: members, isLoading } = useMembers(activeOrg?.id);
  const { data: invitations } = useInvitations(activeOrg?.id);
  const [inviteOpen, setInviteOpen] = useState(false);
  const [actionUserId, setActionUserId] = useState<string | null>(null);

  if (orgsLoading || isLoading) {
    return <div className="relative z-10 p-9 text-sm text-fg-dim">Loading…</div>;
  }

  if (!activeOrg) {
    return <NoActiveOrg />;
  }

  const myRole = members?.find((m) => m.user_id === user?.id)?.role;
  const actionMember = members?.find((m) => m.user_id === actionUserId) ?? null;
  const ownerCount = members?.filter((m) => m.role === "owner").length ?? 0;

  return (
    <>
      <KoraMembers
        orgName={activeOrg.name}
        members={(members ?? []).map((m) => toKoraMember(m, user?.id))}
        invitations={(invitations ?? []).map(toKoraInvitation)}
        onInvite={() => setInviteOpen(true)}
        onMemberAction={(id) => setActionUserId(id)}
      />

      <InviteMemberDialog open={inviteOpen} onClose={() => setInviteOpen(false)} organizationId={activeOrg.id} />
      <MemberActionsModal
        member={actionMember}
        organizationId={activeOrg.id}
        myRole={myRole}
        currentUserId={user?.id}
        ownerCount={ownerCount}
        onClose={() => setActionUserId(null)}
      />
    </>
  );
}
