import type { ReactNode } from 'react';
import type { DocumentSummary } from '../../types';
import { FieldLabel, Panel, PrimaryButton, StatusBadge } from '../../primitives';

export function OverviewTab({ document: doc, processingError, onProcess, isProcessing = false }: {
  document: DocumentSummary;
  /** Populated only when `status === 'failed'`; renders the reason inline. */
  processingError?: string | null;
  onProcess: () => void;
  isProcessing?: boolean;
}) {
  const fields: { label: string; value: ReactNode }[] = [
    { label: 'STATUS', value: <StatusBadge status={doc.status} /> },
    { label: 'CONTENT_TYPE', value: <Mono>{doc.contentType ?? null}</Mono> },
    { label: 'SIZE', value: <Mono>{doc.sizeLabel}</Mono> },
    { label: 'PAGES', value: <Mono>{doc.pages != null ? String(doc.pages) : null}</Mono> },
    { label: 'UPLOADED', value: <Mono>{doc.uploadedAt}</Mono> },
    { label: 'PROCESSED', value: <Mono>{doc.processedAt ?? null}</Mono> },
  ];

  return (
    <div>
      <Panel className="mb-5 px-[26px] py-6">
        <div className="grid grid-cols-[repeat(auto-fit,minmax(200px,1fr))] gap-x-10 gap-y-6">
          {fields.map((f) => (
            <div key={f.label}>
              <FieldLabel>{f.label}</FieldLabel>
              {f.value}
            </div>
          ))}
        </div>
      </Panel>

      {processingError && (
        <div className="mb-5 rounded-[9px] border border-danger/30 bg-danger/[0.08] px-4 py-3 text-[13px] text-danger-soft [text-wrap:pretty]">
          {processingError}
        </div>
      )}

      {doc.status === 'uploaded' && (
        <PrimaryButton onClick={onProcess} className={isProcessing ? 'pointer-events-none opacity-50' : ''}>
          {isProcessing ? '▷ PROCESSING…' : '▷ PROCESS DOCUMENT'}
        </PrimaryButton>
      )}
    </div>
  );
}

function Mono({ children }: { children: string | null }) {
  return <div className={'font-mono text-[13px] ' + (children ? 'text-fg-secondary' : 'text-fg-disabled')}>{children ?? '—'}</div>;
}
