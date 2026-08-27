"use client";

import { useState } from "react";
import { toast } from "sonner";
import { FieldLabel, GhostButton, PrimaryButton } from "@/components/kora/primitives";
import { inviteMemberSchema } from "../schemas";
import { useInviteMember } from "../hooks";
import type { InvitationRead } from "../types";
import type { MembershipRole } from "@/types/api";

const ROLES: MembershipRole[] = ["member", "admin", "owner"];

export function InviteMemberDialog({ open, onClose, organizationId }: {
  open: boolean;
  onClose: () => void;
  organizationId: string;
}) {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<MembershipRole>("member");
  // There's no email-sending backend yet -- the only way to hand the
  // invite to its recipient is to copy the link ourselves, so the
  // dialog shows it here instead of closing straight after send.
  const [createdInvitation, setCreatedInvitation] = useState<InvitationRead | null>(null);
  const inviteMember = useInviteMember(organizationId);

  if (!open) return null;

  const handleClose = () => {
    setEmail("");
    setRole("member");
    setCreatedInvitation(null);
    onClose();
  };

  const handleSubmit = () => {
    const result = inviteMemberSchema.safeParse({ email, role });
    if (!result.success) {
      toast.error(result.error.issues[0]?.message ?? "Invalid invitation details.");
      return;
    }
    inviteMember.mutate(result.data, {
      onSuccess: (invitation) => {
        toast.success(`Invitation created for ${result.data.email}.`);
        setCreatedInvitation(invitation);
      },
      onError: (error) => toast.error(error.message || "Could not send invitation."),
    });
  };

  const inviteLink = createdInvitation
    ? `${window.location.origin}/accept-invitation?token=${createdInvitation.token}`
    : null;

  const handleCopyLink = async () => {
    if (!inviteLink) return;
    try {
      await navigator.clipboard.writeText(inviteLink);
      toast.success("Link copied.");
    } catch {
      toast.error("Could not copy link.");
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-[60] flex items-center justify-center bg-[#030508]/75 p-6 backdrop-blur-sm"
      onClick={handleClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="kora-rise w-[min(420px,100%)] overflow-hidden rounded-2xl border border-white/[0.09] bg-gradient-to-b from-ink-850 to-ink-800 shadow-modal"
      >
        <header className="flex items-center justify-between border-b border-white/[0.07] bg-gradient-to-r from-accent/10 to-transparent px-5 py-[18px]">
          <h2 className="text-sm font-semibold">{createdInvitation ? "Invitation link" : "Invite a member"}</h2>
          <button
            type="button"
            onClick={handleClose}
            aria-label="Close"
            className="flex h-6 w-6 cursor-pointer items-center justify-center rounded-[7px] border border-white/[0.09] bg-transparent text-[13px] text-fg-muted hover:border-white/20 hover:text-fg"
          >
            ×
          </button>
        </header>

        {createdInvitation ? (
          <>
            <div className="p-5">
              <p className="m-0 mb-[18px] text-[12.5px] leading-relaxed text-fg-dim [text-wrap:pretty]">
                There's no email delivery yet — send this link to <span className="text-fg-secondary">{createdInvitation.email}</span> yourself.
              </p>
              <FieldLabel>LINK</FieldLabel>
              <div className="flex items-center gap-2">
                <input
                  readOnly
                  value={inviteLink ?? ""}
                  onFocus={(e) => e.currentTarget.select()}
                  className="w-full rounded-[9px] border border-white/[0.09] bg-white/[0.025] px-[13px] py-[11px] font-mono text-[11.5px] text-fg-secondary outline-none"
                />
                <GhostButton tone="neutral" className="shrink-0" onClick={handleCopyLink}>COPY</GhostButton>
              </div>
            </div>
            <footer className="flex justify-end px-5 pb-5">
              <PrimaryButton onClick={handleClose}>DONE</PrimaryButton>
            </footer>
          </>
        ) : (
          <>
            <div className="p-5">
              <FieldLabel>EMAIL</FieldLabel>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoFocus
                onKeyDown={(e) => { if (e.key === "Enter") handleSubmit(); }}
                className="mb-[18px] w-full rounded-[9px] border border-accent/35 bg-white/[0.03] px-[13px] py-[11px] text-[13px] text-fg-secondary shadow-[0_0_22px_-12px_rgba(77,141,255,0.9)] outline-none"
              />
              <FieldLabel>ROLE</FieldLabel>
              <div className="flex gap-2">
                {ROLES.map((r) => (
                  <button
                    key={r}
                    type="button"
                    onClick={() => setRole(r)}
                    className={
                      "flex-1 cursor-pointer rounded-[9px] border px-3 py-2 font-mono text-[10.5px] tracking-badge transition " +
                      (role === r
                        ? "border-accent/[0.45] bg-accent/[0.16] text-accent-pale"
                        : "border-white/[0.09] bg-white/[0.02] text-fg-quiet hover:border-white/20")
                    }
                  >
                    {r.toUpperCase()}
                  </button>
                ))}
              </div>
            </div>

            <footer className="flex justify-end gap-[9px] px-5 pb-5">
              <GhostButton tone="neutral" onClick={handleClose}>CANCEL</GhostButton>
              <PrimaryButton onClick={handleSubmit}>
                {inviteMember.isPending ? "SENDING…" : "SEND INVITATION"}
              </PrimaryButton>
            </footer>
          </>
        )}
      </div>
    </div>
  );
}
