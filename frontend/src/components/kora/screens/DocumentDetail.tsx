import type { ReactNode } from 'react';
import type { DetailTabId, DocumentSummary } from '../types';
import { StatusBadge, Tabs } from '../primitives';

// User-facing tab text only -- ids stay wired to the routes/handlers in
// page.tsx, so relabeling here never touches behavior.
const TABS: { id: DetailTabId; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'analysis', label: 'Snapshot' },
  { id: 'financials', label: 'Financials' },
  { id: 'checks', label: "What's Concerning" },
  { id: 'coverage', label: "What's Missing" },
  { id: 'score', label: 'Score' },
  { id: 'dd', label: 'Due Diligence' },
  { id: 'ddv2', label: 'Full Report' },
];

export function DocumentDetail({ document: doc, activeTab, onSelectTab, onBack, children }: {
  document: DocumentSummary;
  activeTab: DetailTabId;
  onSelectTab: (id: DetailTabId) => void;
  onBack: () => void;
  children: ReactNode;
}) {
  return (
    <div className="relative z-10 max-w-[1360px] px-9 pb-24 pt-[30px]">
      <div className="kora-rise mb-1.5 flex items-center gap-3">
        <button
          type="button"
          onClick={onBack}
          className="cursor-pointer border-none bg-transparent p-0 font-mono text-[11.5px] tracking-kicker text-fg-faint hover:text-accent-pale"
        >
          DOCUMENTS /
        </button>
        <span className="font-mono text-[11.5px] tracking-kicker text-fg-muted">{doc.filename.toUpperCase()}</span>
      </div>

      <div className="kora-rise mb-[22px] flex items-center gap-3">
        <h1 className="m-0 text-[29px] font-semibold tracking-tight">{doc.filename}</h1>
        <StatusBadge status={doc.status} />
      </div>

      <div className="kora-rise kora-d1 mb-[26px]">
        <Tabs tabs={TABS} active={activeTab} onSelect={onSelectTab} />
      </div>

      <div className="kora-rise">{children}</div>
    </div>
  );
}
