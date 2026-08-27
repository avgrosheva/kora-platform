import type { DocumentSummary } from '../types';
import { Badge, Meter, Panel, PanelHeader, PageHeading, PrimaryButton, StatCard, StatusBadge } from '../primitives';

export interface PortfolioMetrics {
  documentsAnalyzed: number;
  documentsTotal: number;
  averageRevenue: string | null;
  averageScore: number | null;
  averageCoverage: number | null;
}

export interface PortfolioRow extends DocumentSummary {
  score: number | null;
  /** null = coverage not assessed yet (distinct from a real 0%) -- render
   * the withheld "—" state, same convention as `score`. */
  coverage: number | null;
  openFindings: { severity: 'high' | 'medium' | 'low'; count: number }[];
}

export interface HealthBucket { label: string; count: number; }

export function Portfolio({ orgName, metrics, rows, health, topScored, onOpenDocument }: {
  orgName: string;
  metrics: PortfolioMetrics;
  rows: PortfolioRow[];
  health: HealthBucket[];
  topScored: { id: string; name: string; score: number }[];
  onOpenDocument: (id: string) => void;
}) {
  const maxHealth = Math.max(1, ...health.map((h) => h.count));

  return (
    <div className="relative z-10 max-w-[1360px] px-9 pb-24 pt-10">
      <PageHeading
        kicker={'PORTFOLIO / ' + orgName.toUpperCase()}
        title="Portfolio"
        blurb="Every document analyzed in this organization, with evidence coverage and open risk at a glance."
      />

      <div className="mb-4 grid grid-cols-[repeat(auto-fit,minmax(220px,1fr))] gap-3.5">
        <StatCard
          tone="accent"
          label="DOCUMENTS_ANALYZED"
          value={<>{metrics.documentsAnalyzed}<span className="text-[20px] text-fg-disabled"> / {metrics.documentsTotal}</span></>}
        />
        <StatCard label="AVERAGE_REVENUE" value={metrics.averageRevenue ?? '—'} tone={metrics.averageRevenue ? 'default' : 'muted'} delayClass="kora-d1" />
        <StatCard
          tone={metrics.averageScore == null ? 'muted' : 'default'}
          label="AVERAGE_INVESTMENT_SCORE"
          value={metrics.averageScore ?? '—'}
          badge={metrics.averageScore == null ? <Badge tone="warn">NOT SCORED</Badge> : undefined}
          delayClass="kora-d2"
        />
        <StatCard tone="warn" label="AVERAGE_COVERAGE" value={metrics.averageCoverage != null ? metrics.averageCoverage + '%' : '—'} delayClass="kora-d3" />
      </div>

      <Panel className="kora-rise kora-d2 mb-4 overflow-hidden">
        <PanelHeader
          title="Analyzed documents"
          aside={<span className="font-mono text-[10px] tracking-badge text-fg-faint">{rows.length} RESULT{rows.length === 1 ? '' : 'S'}</span>}
        />
        <div className="grid grid-cols-[2fr_0.8fr_1.2fr_1.5fr_0.9fr] gap-4 border-b border-white/[0.04] px-5 py-2.5 font-mono text-[9.5px] tracking-label text-fg-faint">
          <span>DOCUMENT</span><span>SCORE</span><span>COVERAGE</span><span>OPEN FINDINGS</span><span>STATUS</span>
        </div>
        {rows.map((row) => (
          <div
            key={row.id}
            onClick={() => onOpenDocument(row.id)}
            className="grid cursor-pointer grid-cols-[2fr_0.8fr_1.2fr_1.5fr_0.9fr] items-center gap-4 px-5 py-4 transition-colors hover:bg-accent/[0.05]"
          >
            <div>
              <div className="mb-[3px] text-sm font-medium">{row.companyName ?? row.filename}</div>
              <div className="font-mono text-[11px] text-fg-dim">{row.filename}</div>
            </div>
            <div className={'font-mono text-[13px] ' + (row.score == null ? 'text-warn' : 'text-fg')}>{row.score ?? '—'}</div>
            <div>
              <div className="mb-1.5"><Meter percent={row.coverage ?? 0} tone={row.coverage != null && row.coverage >= 60 ? 'good' : 'warn'} delayClass="kora-d5" /></div>
              <div className="font-mono text-[10px] text-fg-dim">{row.coverage != null ? row.coverage + '%' : '—'}</div>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {row.openFindings.map((f) => (
                <Badge key={f.severity} tone={f.severity === 'high' ? 'danger' : f.severity === 'medium' ? 'warn' : 'neutral'}>
                  {f.count} {f.severity.toUpperCase()}
                </Badge>
              ))}
            </div>
            <div><StatusBadge status={row.status} /></div>
          </div>
        ))}
      </Panel>

      <div className="grid grid-cols-[1.35fr_1fr] gap-4">
        <Panel className="kora-rise kora-d3 px-[22px] pb-[18px] pt-5">
          <div className="mb-6 flex items-baseline justify-between">
            <h2 className="text-[13.5px] font-semibold">Portfolio health</h2>
            <span className="font-mono text-[9.5px] tracking-label text-fg-faint">DOCUMENTS BY SIGNAL</span>
          </div>
          <div className="relative flex h-40 items-end border-b border-white/[0.07]">
            <div className="pointer-events-none absolute inset-0 flex flex-col justify-between">
              {[0, 1, 2, 3].map((i) => <div key={i} className="border-t border-dashed border-white/[0.05]" />)}
            </div>
            {health.map((bucket) => (
              <div key={bucket.label} className="flex h-full flex-1 items-end justify-center">
                {bucket.count > 0 ? (
                  <div
                    className="kora-grow-y w-[60px] rounded-t-md bg-gradient-to-b from-accent-bright to-accent/[0.18] shadow-[0_0_26px_-6px_rgba(77,141,255,0.7)]"
                    style={{ height: Math.round((bucket.count / maxHealth) * 84) + '%' }}
                  />
                ) : (
                  <div className="h-0.5 w-[60px] bg-white/[0.12]" />
                )}
              </div>
            ))}
          </div>
          <div className="mt-3 flex">
            {health.map((bucket) => (
              <div key={bucket.label} className={'flex-1 text-center font-mono text-[10px] ' + (bucket.count > 0 ? 'text-fg-quiet' : 'text-fg-faint')}>
                {bucket.label.toUpperCase()}{' '}
                <span className={bucket.count > 0 ? 'text-accent-bright' : ''}>{bucket.count}</span>
              </div>
            ))}
          </div>
        </Panel>

        <Panel className="kora-rise kora-d4 flex flex-col px-[22px] py-5">
          <h2 className="mb-[18px] text-[13.5px] font-semibold">Top scored documents</h2>
          {topScored.length === 0 ? (
            <div className="flex flex-1 flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-white/[0.08] px-5 py-[26px] text-center">
              <div className="h-[34px] w-[34px] rounded-[9px] border border-white/10 bg-white/[0.025]" />
              <div className="text-[13px] text-fg-quiet">No scored documents yet</div>
              <div className="max-w-[230px] text-[11.5px] text-fg-faint [text-wrap:pretty]">
                Scores appear once a deterministic investment score has been calculated.
              </div>
            </div>
          ) : (
            <ul className="m-0 flex list-none flex-col gap-2.5 p-0">
              {topScored.map((doc) => (
                <li key={doc.id} className="flex items-center justify-between rounded-[10px] border border-white/[0.06] bg-white/[0.02] px-3.5 py-3">
                  <span className="text-[13px]">{doc.name}</span>
                  <span className="font-mono text-[15px] text-good">{doc.score}</span>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>
    </div>
  );
}

/** Zero-state when the user belongs to no organization yet. */
export function NoOrganizations({ onCreate }: { onCreate: () => void }) {
  return (
    <div className="relative z-10 flex min-h-[620px] items-center justify-center px-9 py-16">
      <div className="kora-rise max-w-[520px] text-center">
        <div className="mx-auto mb-6 flex h-[58px] w-[58px] items-center justify-center rounded-2xl border border-accent/30 bg-accent/10 shadow-glow-accent-lg">
          <span className="h-5 w-[18px] rounded-[3px_5px_3px_3px] border-[1.5px] border-accent-soft" />
        </div>
        <div className="mb-3.5 font-mono text-[10px] tracking-[0.18em] text-fg-faint">NO ORGANIZATIONS</div>
        <h1 className="m-0 mb-3.5 text-[27px] font-semibold tracking-[-0.7px]">
          Create your first organization to get started
        </h1>
        <p className="m-0 mb-[26px] text-[13.5px] leading-relaxed text-fg-dim [text-wrap:pretty]">
          Kora turns company documents into structured, evidence-backed due-diligence profiles.
          Everything you upload lives inside an organization, so create one to begin.
        </p>
        <PrimaryButton onClick={onCreate}>+ CREATE ORGANIZATION</PrimaryButton>
      </div>
    </div>
  );
}
