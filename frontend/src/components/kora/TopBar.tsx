import { useState } from 'react';
import type { Organization } from './types';

export function TopBar({ organizations, currentOrgId, userEmail, userRole = 'OWNER', onSwitchOrg, onCreateOrg, onSignOut, onAccountPrefs }: {
  organizations: Organization[];
  currentOrgId: string;
  userEmail: string;
  userRole?: string;
  onSwitchOrg: (id: string) => void;
  onCreateOrg: () => void;
  onSignOut?: () => void;
  onAccountPrefs?: () => void;
}) {
  const [openMenu, setOpenMenu] = useState<'org' | 'account' | null>(null);
  const current = organizations.find((o) => o.id === currentOrgId);

  return (
    <header className="relative z-40 flex h-[58px] shrink-0 items-center justify-between border-b border-white/[0.055] bg-ink-950/75 px-[26px] backdrop-blur-lg">
      <div className="flex items-center gap-[18px]">
        <div className="flex items-center gap-2">
          <div className="h-[18px] w-[18px] rounded-[5px] bg-gradient-to-br from-accent to-accent-deep shadow-[0_0_16px_-4px_rgba(77,141,255,0.8)]" />
          <span className="text-[16px] font-semibold tracking-[-0.2px]">Kora</span>
        </div>

        <div className="relative">
          <button
            type="button"
            onClick={() => setOpenMenu(openMenu === 'org' ? null : 'org')}
            className="flex cursor-pointer items-center gap-[9px] rounded-lg border border-white/[0.07] bg-white/[0.02] px-2.5 py-1.5 font-mono text-[12px] text-fg-tertiary transition-colors hover:border-white/[0.16]"
          >
            {current?.name}
            <span className="text-[10px] text-fg-faint">▲▼</span>
          </button>

          {openMenu === 'org' && (
            <div className="kora-rise absolute left-0 top-[38px] z-50 w-[232px] rounded-[11px] border border-white/[0.09] bg-ink-850 p-1.5 shadow-panel-pop">
              <div className="px-2.5 pb-1.5 pt-2 font-mono text-[10px] tracking-label text-fg-faint">
                ORGANIZATIONS
              </div>
              {organizations.map((org) => {
                const on = org.id === currentOrgId;
                return (
                  <button
                    key={org.id}
                    type="button"
                    onClick={() => { onSwitchOrg(org.id); setOpenMenu(null); }}
                    className={'flex w-full cursor-pointer items-center justify-between gap-2 rounded-lg border px-2.5 py-2 text-left text-[13.5px] transition-colors ' + (on ? 'border-accent/[0.22] bg-accent/10 text-fg' : 'border-transparent text-fg-quiet hover:bg-white/[0.04] hover:text-fg')}
                  >
                    <span>{org.name}</span>
                    <span className={'font-mono text-[10px] ' + (on ? 'text-accent-ghost' : 'text-fg-faint')}>
                      /{org.slug}
                    </span>
                  </button>
                );
              })}
              <div className="mx-1 my-1.5 h-px bg-white/[0.06]" />
              <button
                type="button"
                onClick={() => { onCreateOrg(); setOpenMenu(null); }}
                className="w-full cursor-pointer rounded-lg border-none bg-transparent px-2.5 py-2 text-left font-mono text-[11.5px] tracking-badge text-accent-ghost transition-colors hover:bg-accent/10"
              >
                + NEW ORGANIZATION
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="relative">
        <button
          type="button"
          onClick={() => setOpenMenu(openMenu === 'account' ? null : 'account')}
          className="flex cursor-pointer items-center gap-[9px] border-none bg-transparent"
        >
          <span className="font-mono text-[11px] tracking-badge text-fg-faint">{userEmail}</span>
          <span className="flex h-7 w-7 items-center justify-center rounded-full border border-accent/35 bg-accent/[0.14] text-[12.5px] font-semibold text-accent-pale">
            {userEmail.charAt(0).toUpperCase()}
          </span>
        </button>

        {openMenu === 'account' && (
          <div className="kora-rise absolute right-0 top-10 z-50 w-[200px] rounded-[11px] border border-white/[0.09] bg-ink-850 p-1.5 shadow-panel-pop">
            <div className="mb-1 border-b border-white/[0.06] px-2.5 pb-2.5 pt-1">
              <div className="text-[13px] text-fg-secondary">{userEmail}</div>
              <div className="mt-[3px] font-mono text-[10px] text-fg-faint">
                {userRole} · {current?.name.toUpperCase()}
              </div>
            </div>
            <button type="button" onClick={onAccountPrefs} className="w-full cursor-pointer rounded-lg border-none bg-transparent px-2.5 py-2 text-left text-[13.5px] text-fg-quiet transition-colors hover:bg-white/[0.04] hover:text-fg">
              Account preferences
            </button>
            <button type="button" onClick={onSignOut} className="w-full cursor-pointer rounded-lg border-none bg-transparent px-2.5 py-2 text-left text-[13.5px] text-fg-quiet transition-colors hover:bg-white/[0.04] hover:text-fg">
              Sign out
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
