import { FieldLabel, GhostButton, PageHeading, Panel, PanelHeader } from '../primitives';

export interface ProfileUser {
  email: string;
  fullName: string | null;
  createdAt: string;
  isActive: boolean;
}

export function Profile({ user, onLogout }: {
  user: ProfileUser;
  onLogout: () => void;
}) {
  return (
    <div className="relative z-10 max-w-[820px] px-9 pb-24 pt-10">
      <PageHeading kicker="PROFILE" title="Profile" blurb="Manage your account." />

      <Panel className="kora-rise kora-d1 mb-[18px] overflow-hidden">
        <PanelHeader title="Account" />
        <div className="grid grid-cols-2 gap-[18px] p-[22px]">
          <div>
            <FieldLabel>EMAIL</FieldLabel>
            <div className="text-[14px] text-fg-secondary">{user.email}</div>
          </div>
          <div>
            <FieldLabel>FULL NAME</FieldLabel>
            <div className="text-[14px] text-fg-secondary">{user.fullName ?? '—'}</div>
          </div>
          <div>
            <FieldLabel>ACCOUNT CREATED</FieldLabel>
            <div className="font-mono text-[14px] text-fg-secondary">{user.createdAt}</div>
          </div>
          <div>
            <FieldLabel>STATUS</FieldLabel>
            <div className="text-[14px] text-fg-secondary">{user.isActive ? 'Active' : 'Inactive'}</div>
          </div>
        </div>
        <div className="border-t border-white/[0.055] px-[22px] py-[18px]">
          <div className="rounded-[9px] border border-white/[0.09] bg-white/[0.025] px-4 py-3 text-[13.5px] leading-relaxed text-fg-dim [text-wrap:pretty]">
            Password changes and profile editing aren't available yet — the backend doesn't
            currently expose an endpoint for updating account details.
          </div>
        </div>
      </Panel>

      <section className="kora-rise kora-d2 rounded-[14px] border border-danger/[0.22] bg-gradient-to-b from-danger/[0.05] to-white/[0.008] p-[22px]">
        <div className="mb-2.5 flex items-center gap-[9px]">
          <span className="h-1.5 w-1.5 rounded-full bg-danger shadow-[0_0_10px_2px_rgba(255,92,92,0.7)]" />
          <span className="font-mono text-[11px] tracking-label text-danger-soft">SESSION</span>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-5">
          <p className="m-0 max-w-[440px] text-[13.5px] text-fg-muted [text-wrap:pretty]">
            End your current session on this device.
          </p>
          <GhostButton tone="danger" onClick={onLogout}>LOG OUT</GhostButton>
        </div>
      </section>
    </div>
  );
}
