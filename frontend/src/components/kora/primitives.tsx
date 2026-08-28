import type { ReactNode } from 'react';
import type { Severity, FindingSource, Finding } from './types';

/* ---------------- surfaces ---------------- */

export function Panel({ className = '', children }: { className?: string; children: ReactNode }) {
  return (
    <section className={'rounded-[14px] border border-white/[0.06] bg-white/[0.018] ' + className}>
      {children}
    </section>
  );
}

export function PanelHeader({ title, aside }: { title: string; aside?: ReactNode }) {
  return (
    <header className="flex items-center justify-between border-b border-white/[0.055] px-5 py-4">
      <h2 className="text-[13.5px] font-semibold">{title}</h2>
      {aside}
    </header>
  );
}

/* ---------------- type ---------------- */

export function SectionLabel({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={'font-mono text-[10px] tracking-label text-fg-dim ' + className}>{children}</div>
  );
}

export function FieldLabel({ children }: { children: ReactNode }) {
  return <div className="mb-2 font-mono text-[9.5px] tracking-label text-fg-faint">{children}</div>;
}

export function Kicker({ children }: { children: ReactNode }) {
  return <div className="mb-2.5 font-mono text-[10.5px] tracking-kicker text-fg-faint">{children}</div>;
}

export function PageHeading({ kicker, title, blurb, action }: {
  kicker: string; title: string; blurb?: string; action?: ReactNode;
}) {
  return (
    <div className="kora-rise mb-7 flex flex-wrap items-start justify-between gap-6">
      <div>
        <Kicker>{kicker}</Kicker>
        <h1 className="m-0 mb-2 text-[32px] font-semibold tracking-tight">{title}</h1>
        {blurb && <p className="m-0 max-w-[520px] text-sm text-fg-dim [text-wrap:pretty]">{blurb}</p>}
      </div>
      {action}
    </div>
  );
}

/* ---------------- badges ---------------- */

type BadgeTone = 'neutral' | 'accent' | 'danger' | 'warn' | 'good';

const badgeTone: Record<BadgeTone, string> = {
  neutral: 'text-fg-quiet bg-white/[0.04] border-white/10',
  accent: 'text-accent-pale bg-accent/[0.12] border-accent/30',
  danger: 'text-danger-soft bg-danger/[0.12] border-danger/30',
  warn: 'text-warn bg-warn/10 border-warn/[0.28]',
  good: 'text-good bg-good/[0.08] border-good/30',
};

export function Badge({ tone = 'neutral', children }: { tone?: BadgeTone; children: ReactNode }) {
  return (
    <span className={'rounded-full border px-2 py-[3px] font-mono text-[9px] tracking-badge ' + badgeTone[tone]}>
      {children}
    </span>
  );
}

const severityTone: Record<Severity, BadgeTone> = { high: 'danger', medium: 'warn', low: 'neutral' };

export const SeverityBadge = ({ severity }: { severity: Severity }) => (
  <Badge tone={severityTone[severity]}>{severity.toUpperCase()}</Badge>
);

const sourceLabel: Record<FindingSource, string> = {
  'document-stated': 'DOCUMENT-STATED',
  'kora-inferred': 'KORA-INFERRED',
  deterministic: 'DETERMINISTIC CHECK',
};

export const SourceBadge = ({ source }: { source: FindingSource }) => (
  <Badge tone="neutral">{sourceLabel[source]}</Badge>
);

export function StatusBadge({ status }: { status: string }) {
  const tone: BadgeTone =
    status === 'completed' ? 'accent' : status === 'failed' ? 'danger' : 'neutral';
  return <Badge tone={tone}>{status.toUpperCase()}</Badge>;
}

export function Chip({ tone = 'neutral', children }: { tone?: 'neutral' | 'danger' | 'good'; children: ReactNode }) {
  const cls =
    tone === 'danger' ? 'text-danger-wash border-danger/[0.22] bg-danger/[0.06]'
    : tone === 'good' ? 'text-good-pale border-good/[0.22] bg-good/[0.06]'
    : 'text-fg-tertiary border-white/[0.09] bg-white/[0.03]';
  return <span className={'rounded-full border px-2.5 py-[5px] text-xs ' + cls}>{children}</span>;
}

export function GapChip({ label }: { label: string }) {
  return (
    <span className="rounded-full border border-dashed border-danger/30 bg-danger/[0.05] px-[11px] py-1.5 font-mono text-[11px] text-danger-pale">
      {label}
    </span>
  );
}

export function GapRow({ label }: { label: string }) {
  return (
    <div className="flex items-center justify-between rounded-[9px] border border-dashed border-danger/[0.26] bg-danger/[0.05] px-[13px] py-[11px]">
      <span className="font-mono text-[11.5px] text-danger-pale">{label}</span>
      <span className="font-mono text-[9px] tracking-badge text-fg-dim">MISSING</span>
    </div>
  );
}

/* ---------------- buttons ---------------- */

export function PrimaryButton({ children, onClick, className = '', type = 'button' }: {
  children: ReactNode; onClick?: () => void; className?: string; type?: 'button' | 'submit';
}) {
  return (
    <button
      type={type}
      onClick={onClick}
      className={'cursor-pointer rounded-[9px] border-none bg-accent-btn px-[17px] py-[11px] font-mono text-[11px] tracking-badge text-accent-ink shadow-glow-accent transition hover:brightness-110 ' + className}
    >
      {children}
    </button>
  );
}

export function GhostButton({ children, onClick, tone = 'accent', className = '' }: {
  children: ReactNode; onClick?: () => void; tone?: 'accent' | 'neutral' | 'danger'; className?: string;
}) {
  const cls =
    tone === 'danger' ? 'text-danger-ink bg-danger/[0.14] border-danger/[0.36] hover:bg-danger/[0.24]'
    : tone === 'neutral' ? 'text-fg-secondary bg-white/[0.03] border-white/[0.11] hover:border-accent/40'
    : 'text-fg-secondary bg-accent/10 border-accent/[0.32] hover:bg-accent/20 hover:shadow-glow-accent';
  return (
    <button
      type="button"
      onClick={onClick}
      className={'cursor-pointer rounded-[9px] border px-4 py-2.5 font-mono text-[10.5px] tracking-badge transition ' + cls + ' ' + className}
    >
      {children}
    </button>
  );
}

/* ---------------- data display ---------------- */

type MeterTone = 'accent' | 'warn' | 'good' | 'danger';

const meterFill: Record<MeterTone, string> = {
  accent: 'bg-gradient-to-r from-accent/30 to-accent-bright shadow-glow-accent',
  warn: 'bg-gradient-to-r from-warn/40 to-warn-pale shadow-glow-warn',
  good: 'bg-gradient-to-r from-good/40 to-good shadow-glow-good',
  danger: 'bg-gradient-to-r from-danger/40 to-danger shadow-glow-danger',
};

export function Meter({ percent, tone = 'accent', thick = false, markerAt, delayClass = '' }: {
  percent: number; tone?: MeterTone; thick?: boolean; markerAt?: number; delayClass?: string;
}) {
  return (
    <div className={'relative overflow-hidden rounded bg-white/[0.07] ' + (thick ? 'h-1.5' : 'h-[3px]')}>
      <div
        className={'kora-grow-x h-full ' + meterFill[tone] + ' ' + delayClass}
        style={{ width: Math.max(0, Math.min(100, percent)) + '%' }}
      />
      {markerAt != null && (
        <div className="absolute -top-1 -bottom-1 w-px bg-white/35" style={{ left: markerAt + '%' }} />
      )}
    </div>
  );
}

export function StatCard({ label, value, tone = 'default', badge, delayClass = '' }: {
  label: string;
  value: ReactNode;
  tone?: 'default' | 'accent' | 'warn' | 'good' | 'muted';
  badge?: ReactNode;
  delayClass?: string;
}) {
  const rule =
    tone === 'warn' ? 'via-warn/35' : tone === 'good' ? 'via-good/35'
    : tone === 'accent' ? 'via-accent/55' : 'via-accent/35';
  const valueTone =
    tone === 'warn' ? 'text-warn' : tone === 'good' ? 'text-good'
    : tone === 'muted' ? 'text-fg-disabled' : 'text-fg';
  return (
    <div className={'kora-rise relative rounded-xl border border-white/[0.06] bg-panel-sheen p-[18px] ' + delayClass}>
      <div className={'absolute inset-x-4 top-0 h-px bg-gradient-to-r from-transparent to-transparent ' + rule} />
      <div className="mb-3 break-words font-mono text-[10px] tracking-label text-fg-dim">{label}</div>
      <div className="flex flex-wrap items-baseline gap-2.5">
        <div className={'whitespace-nowrap text-[clamp(22px,2.1vw,30px)] font-medium tracking-[-1px] ' + valueTone}>
          {value}
        </div>
        {badge}
      </div>
    </div>
  );
}

export function MetricCell({ label, value, flagged }: { label: string; value: string | null; flagged?: boolean }) {
  return (
    <div className="border-b border-white/[0.04] px-[22px] py-[18px]">
      <FieldLabel>{label.toUpperCase()}</FieldLabel>
      <div className="flex items-center gap-2">
        <span className={'font-mono text-[19px] ' + (value ? 'text-fg' : 'text-fg-ghost')}>{value ?? '—'}</span>
        {flagged && <Badge tone="warn">FLAGGED</Badge>}
      </div>
    </div>
  );
}

export function FactField({ label, children, wide }: { label: string; children: ReactNode; wide?: boolean }) {
  return (
    <div className={wide ? 'col-span-full' : undefined}>
      <FieldLabel>{label}</FieldLabel>
      {children}
    </div>
  );
}

export function FactChips({ items, tone = 'neutral' }: { items: string[]; tone?: 'neutral' | 'danger' | 'good' }) {
  if (!items.length) return <div className="font-mono text-[13px] text-fg-disabled">—</div>;
  return (
    <div className="flex flex-wrap gap-[7px]">
      {items.map((item) => <Chip key={item} tone={tone}>{item}</Chip>)}
    </div>
  );
}

/* ---------------- findings ---------------- */

const findingAccent: Record<Severity, { rail: string; frame: string }> = {
  high: {
    rail: 'bg-danger shadow-glow-danger',
    frame: 'border-danger/[0.16] hover:border-danger/[0.34] bg-gradient-to-r from-danger/[0.06] to-white/[0.012]',
  },
  medium: {
    rail: 'bg-warn shadow-glow-warn',
    frame: 'border-warn/[0.16] hover:border-warn/[0.34] bg-gradient-to-r from-warn/[0.055] to-white/[0.012]',
  },
  low: {
    rail: 'bg-white/30',
    frame: 'border-white/[0.08] hover:border-white/20 bg-white/[0.015]',
  },
};

export function FindingCard({ finding, compact = false, onClick }: {
  finding: Finding; compact?: boolean; onClick?: () => void;
}) {
  const tone = findingAccent[finding.severity];
  return (
    <article
      onClick={onClick}
      className={'relative rounded-xl border transition-colors ' + tone.frame + ' ' + (compact ? 'py-[13px] pl-4 pr-3.5' : 'py-[18px] pl-[22px] pr-5') + (onClick ? ' cursor-pointer' : '')}
    >
      <span className={'absolute left-0 w-0.5 rounded ' + tone.rail + ' ' + (compact ? 'top-3 bottom-3' : 'top-4 bottom-4')} />
      <div className="mb-2 flex flex-wrap items-center gap-[7px]">
        <SeverityBadge severity={finding.severity} />
        <SourceBadge source={finding.source} />
        {finding.category && <span className="font-mono text-[9px] text-fg-faint">{finding.category}</span>}
      </div>
      <h3 className={'mb-1 font-medium ' + (compact ? 'text-[13.5px]' : 'text-sm')}>{finding.title}</h3>
      {finding.metricRef && (
        <div className="mb-2 font-mono text-[10.5px] text-fg-dim">{finding.metricRef}</div>
      )}
      <p className="m-0 text-xs leading-relaxed text-fg-muted [text-wrap:pretty]">{finding.detail}</p>
    </article>
  );
}

/* ---------------- misc ---------------- */

export function EmptyState({ title, blurb, action }: { title: string; blurb?: string; action?: ReactNode }) {
  return (
    <div className="kora-rise rounded-[14px] border border-dashed border-white/10 px-5 py-16 text-center">
      <div className="mx-auto mb-[18px] h-12 w-11 rounded-md border-[1.5px] border-white/[0.16] bg-white/[0.02]" />
      <div className="mb-2 text-[15px] font-medium">{title}</div>
      {blurb && <div className="text-[12.5px] text-fg-dim">{blurb}</div>}
      {action && <div className="mt-6 flex justify-center">{action}</div>}
    </div>
  );
}

export function Tabs<T extends string>({ tabs, active, onSelect, size = 'md' }: {
  tabs: { id: T; label: string; hint?: string }[];
  active: T;
  onSelect: (id: T) => void;
  size?: 'sm' | 'md';
}) {
  return (
    <nav className="flex gap-0.5 overflow-x-auto whitespace-nowrap border-b border-white/[0.06]">
      {tabs.map((tab) => {
        const on = tab.id === active;
        return (
          <button
            key={tab.id}
            type="button"
            onClick={() => onSelect(tab.id)}
            className={'relative shrink-0 cursor-pointer border-none bg-transparent px-[13px] font-sans transition-colors ' + (size === 'sm' ? 'py-2.5 text-xs' : 'py-[11px] text-[13px]') + (on ? ' font-medium text-fg' : ' text-fg-dim hover:text-fg-tertiary')}
          >
            {tab.label}
            {tab.hint && <span className="ml-1.5 font-mono text-[9.5px] text-fg-faint">{tab.hint}</span>}
            {on && (
              <span className="absolute inset-x-2 -bottom-px h-[1.5px] bg-gradient-to-r from-transparent via-accent-bright to-transparent shadow-glow-accent" />
            )}
          </button>
        );
      })}
    </nav>
  );
}

export function Toast({ message }: { message: string }) {
  return (
    <div className="kora-slide-in fixed right-[26px] top-[74px] z-30 flex items-center gap-[11px] rounded-[11px] border border-good/30 bg-gradient-to-r from-good/[0.14] to-ink-850/95 px-4 py-[13px] shadow-[0_0_40px_-14px_rgba(70,217,160,0.6)]">
      <span className="h-[7px] w-[7px] rounded-full bg-good shadow-[0_0_10px_2px_rgba(70,217,160,0.8)]" />
      <span className="text-[12.5px] text-good-wash">{message}</span>
    </div>
  );
}

export function LoadPulse() {
  return (
    <div className="kora-pulse pointer-events-none absolute inset-x-0 top-0 h-[60%] bg-gradient-to-b from-accent/[0.28] to-transparent" />
  );
}
