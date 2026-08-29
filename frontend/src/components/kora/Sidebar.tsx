import type { ReactNode } from 'react';
import type { ScreenId } from './types';

/** Finalized IA: Portfolio | Documents — divider — Members | Settings. */
const PRIMARY: { id: ScreenId; label: string; icon: ReactNode }[] = [
  { id: 'portfolio', label: 'Portfolio', icon: <span className="h-[13px] w-[13px] rounded-full border-[1.5px] border-current border-r-transparent opacity-80" /> },
  { id: 'documents', label: 'Documents', icon: <span className="h-3.5 w-[11px] rounded-[2px_4px_2px_2px] border-[1.5px] border-current opacity-80" /> },
];

const SECONDARY: { id: ScreenId; label: string; icon: ReactNode }[] = [
  { id: 'members', label: 'Members', icon: <span className="h-[13px] w-[13px] rounded-full border-[1.5px] border-current opacity-70" /> },
  { id: 'settings', label: 'Settings', icon: <span className="h-[13px] w-[13px] rounded-[3px] border-[1.5px] border-current opacity-70" /> },
];

function NavItem({ label, icon, active, muted, onClick }: {
  label: string; icon: ReactNode; active: boolean; muted?: boolean; onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={'relative flex cursor-pointer items-center gap-[11px] rounded-lg border-none bg-transparent px-[11px] py-[9px] text-left font-sans transition-colors ' + (muted ? 'text-[14px] text-fg-quiet hover:bg-white/[0.03] hover:text-fg-secondary' : 'text-[14.5px] text-fg-tertiary hover:bg-white/[0.035] hover:text-fg')}
    >
      {active && (
        <span className={'absolute inset-0 rounded-lg bg-accent-rail border ' + (muted ? 'border-accent/20' : 'border-accent/[0.22] shadow-[inset_0_0_20px_-8px_rgba(77,141,255,0.7)]')} />
      )}
      <span className="relative">{icon}</span>
      <span className="relative">{label}</span>
    </button>
  );
}

export function Sidebar({ active, onNavigate, versionLabel = 'KORA v2 · BUILD 214' }: {
  active: ScreenId;
  onNavigate: (id: ScreenId) => void;
  versionLabel?: string;
}) {
  return (
    <aside className="relative z-30 flex w-[228px] shrink-0 flex-col border-r border-white/[0.055] bg-sidebar px-3 pb-[18px] pt-4">
      <nav className="flex flex-col gap-0.5">
        {PRIMARY.map((item) => (
          <NavItem
            key={item.id}
            {...item}
            active={active === item.id || (item.id === 'documents' && active === 'document')}
            onClick={() => onNavigate(item.id)}
          />
        ))}
      </nav>

      <div className="mx-2 my-3.5 h-px bg-white/[0.06]" />

      <nav className="flex flex-col gap-0.5">
        {SECONDARY.map((item) => (
          <NavItem key={item.id} {...item} muted active={active === item.id} onClick={() => onNavigate(item.id)} />
        ))}
      </nav>

      <div className="flex-1" />
      <div className="px-[11px] font-mono text-[10px] tracking-label text-fg-ghost">{versionLabel}</div>
    </aside>
  );
}
