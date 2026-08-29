import type { DocumentSummary } from '../types';
import { EmptyState, PageHeading, Panel, PrimaryButton, StatusBadge } from '../primitives';

export function Documents({ orgName, documents, onOpenDocument, onUpload }: {
  orgName: string;
  documents: DocumentSummary[];
  onOpenDocument: (id: string) => void;
  onUpload: () => void;
}) {
  return (
    <div className="relative z-10 max-w-[1360px] px-9 pb-24 pt-10">
      <PageHeading
        kicker={'DOCUMENTS / ' + orgName.toUpperCase()}
        title="Documents"
        blurb="One document is one analyzed company profile. Upload a PDF, DOCX, or TXT to begin analysis."
        action={<PrimaryButton className="mt-6 shrink-0" onClick={onUpload}>↑ UPLOAD DOCUMENT</PrimaryButton>}
      />

      {documents.length === 0 ? (
        <EmptyState
          title="No documents yet"
          blurb="Upload a pitch deck or financial document — Kora will find the numbers, check them for inconsistencies, and tell you whether it's worth digging deeper. Accepts PDF, DOCX, or TXT."
        />
      ) : (
        <Panel className="kora-rise kora-d1 overflow-hidden">
          <div className="grid grid-cols-[2.4fr_1fr_0.8fr_1.2fr] gap-4 border-b border-white/[0.05] px-5 py-3 font-mono text-[10.5px] tracking-label text-fg-faint">
            <span>FILENAME</span><span>STATUS</span><span>SIZE</span><span>UPLOADED</span>
          </div>
          {documents.map((doc) => (
            <div
              key={doc.id}
              onClick={() => onOpenDocument(doc.id)}
              className="grid cursor-pointer grid-cols-[2.4fr_1fr_0.8fr_1.2fr] items-center gap-4 px-5 py-4 transition-colors hover:bg-accent/[0.05]"
            >
              <div className="flex min-w-0 items-center gap-3">
                <span className="h-[26px] w-[26px] shrink-0 rounded-[7px] border border-white/[0.08] bg-white/[0.03]" />
                <span className="truncate text-[14.5px] font-medium">{doc.filename}</span>
              </div>
              <div><StatusBadge status={doc.status} /></div>
              <div className="font-mono text-[12px] text-fg-muted">{doc.sizeLabel}</div>
              <div className="font-mono text-[12px] text-fg-muted">{doc.uploadedAt}</div>
            </div>
          ))}
        </Panel>
      )}
    </div>
  );
}
