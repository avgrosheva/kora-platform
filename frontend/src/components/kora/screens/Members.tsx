import { useState } from 'react';
import type { Member } from '../types';
import { Badge, PageHeading, Panel, PrimaryButton, Tabs } from '../primitives';

export interface InvitationRow {
  id: string;
  email: string;
  sentAt: string;
  status: 'pending' | 'accepted' | 'expired';
}

const invitationStatusTone = {
  pending: 'neutral',
  accepted: 'good',
  expired: 'danger',
} as const;

export function Members({ orgName, members, invitations = [], onInvite, onMemberAction }: {
  orgName: string;
  members: Member[];
  invitations?: InvitationRow[];
  onInvite: () => void;
  onMemberAction?: (id: string) => void;
}) {
  const [tab, setTab] = useState<'members' | 'invitations'>('members');

  return (
    <div className="relative z-10 max-w-[1200px] px-9 pb-24 pt-10">
      <PageHeading
        kicker={'MEMBERS / ' + orgName.toUpperCase()}
        title="Members"
        blurb="Who can see and analyze documents in this organization."
      />

      <div className="kora-rise kora-d1 mb-5 flex flex-wrap items-center justify-between gap-4">
        <Tabs
          active={tab}
          onSelect={setTab}
          tabs={[
            { id: 'members', label: 'Members' },
            { id: 'invitations', label: 'Invitations', hint: String(invitations.length) },
          ]}
        />
        <PrimaryButton onClick={onInvite}>+ INVITE MEMBER</PrimaryButton>
      </div>

      <Panel className="kora-rise kora-d2 overflow-hidden">
        {tab === 'members' ? (
          <>
            <div className="grid grid-cols-[2.6fr_1fr_1fr_40px] gap-4 border-b border-white/[0.05] px-5 py-3 font-mono text-[9.5px] tracking-label text-fg-faint">
              <span>EMAIL</span><span>ROLE</span><span>JOINED</span><span />
            </div>
            {members.map((member) => (
              <div key={member.id} className="grid grid-cols-[2.6fr_1fr_1fr_40px] items-center gap-4 px-5 py-4 transition-colors hover:bg-white/[0.022]">
                <div className="flex min-w-0 items-center gap-3">
                  <div className="flex h-[30px] w-[30px] shrink-0 items-center justify-center rounded-full border border-accent/[0.32] bg-accent/[0.14] text-[11.5px] font-semibold text-accent-pale">
                    {member.email.charAt(0).toUpperCase()}
                  </div>
                  <div className="min-w-0">
                    <div className="truncate font-mono text-[12.5px] text-fg-secondary">{member.email}</div>
                    {member.isCurrentUser && (
                      <div className="mt-[3px] font-mono text-[9px] tracking-badge text-fg-faint">YOU</div>
                    )}
                  </div>
                </div>
                <div><Badge tone={member.role === 'owner' ? 'accent' : 'neutral'}>{member.role.toUpperCase()}</Badge></div>
                <div className="font-mono text-[11px] text-fg-muted">{member.joinedAt}</div>
                <button
                  type="button"
                  onClick={() => onMemberAction?.(member.id)}
                  aria-label="Member actions"
                  className="cursor-pointer border-none bg-transparent text-right text-sm text-fg-faint hover:text-fg-secondary"
                >
                  ···
                </button>
              </div>
            ))}
          </>
        ) : invitations.length === 0 ? (
          <div className="px-5 py-14 text-center text-[13px] text-fg-dim">No invitations yet.</div>
        ) : (
          invitations.map((inv) => (
            <div key={inv.id} className="flex items-center justify-between gap-4 px-5 py-4">
              <span className="min-w-0 truncate font-mono text-[12.5px] text-fg-secondary">{inv.email}</span>
              <div className="flex shrink-0 items-center gap-3">
                <Badge tone={invitationStatusTone[inv.status]}>{inv.status.toUpperCase()}</Badge>
                <span className="font-mono text-[11px] text-fg-muted">{inv.sentAt}</span>
              </div>
            </div>
          ))
        )}
      </Panel>
    </div>
  );
}
