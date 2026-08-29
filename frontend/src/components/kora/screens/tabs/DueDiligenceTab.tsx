import type { DueDiligenceResponse } from "@/types/api";
import { EmptyState, GhostButton, Panel, PrimaryButton } from "../../primitives";

export function DueDiligenceTab({ report, isGenerating = false, onGenerate, onExportMarkdown, onExportPdf }: {
  /** Session-only: cleared on tab remount / re-navigation, same as the mutation it comes from. */
  report: DueDiligenceResponse | null;
  isGenerating?: boolean;
  onGenerate: () => void;
  onExportMarkdown: () => void;
  onExportPdf: () => void;
}) {
  if (!report) {
    return (
      <EmptyState
        title="No report generated yet"
        blurb="Generate a diligence report from the extracted facts and findings."
        action={
          <PrimaryButton onClick={onGenerate} className={isGenerating ? "pointer-events-none opacity-50" : ""}>
            {isGenerating ? "GENERATING…" : "GENERATE REPORT"}
          </PrimaryButton>
        }
      />
    );
  }

  return (
    <div>
      <div className="mb-[18px] flex flex-wrap items-center justify-between gap-3.5">
        <GhostButton onClick={onGenerate} className={isGenerating ? "pointer-events-none opacity-50" : ""}>
          {isGenerating ? "REGENERATING…" : "REGENERATE REPORT"}
        </GhostButton>
        <div className="flex gap-[9px]">
          <GhostButton tone="neutral" onClick={onExportMarkdown}>↓ EXPORT MARKDOWN</GhostButton>
          <GhostButton tone="neutral" onClick={onExportPdf}>↓ EXPORT PDF</GhostButton>
        </div>
      </div>

      <div className="flex flex-col gap-3.5">
        {report.sections.map((section) => (
          <Panel key={section.title} className="px-6 py-5">
            <h2 className="mb-2 text-[14.5px] font-semibold">{section.title}</h2>
            <p className="m-0 whitespace-pre-line text-[14px] leading-relaxed text-fg-tertiary [text-wrap:pretty]">{section.content}</p>
          </Panel>
        ))}
      </div>

      {report.sources.length > 0 && (
        <Panel className="mt-3.5 px-6 py-5">
          <h2 className="mb-3 text-[14.5px] font-semibold">Sources</h2>
          <ul className="m-0 flex list-none flex-col gap-2 pl-0">
            {report.sources.map((source, i) => (
              <li key={`${source.document_id}-${source.chunk_index}`} className="text-[12.5px] leading-relaxed text-fg-dim">
                <span className="font-mono text-fg-muted">[{i + 1}] similarity {source.similarity_score.toFixed(2)}:</span> {source.snippet}
              </li>
            ))}
          </ul>
        </Panel>
      )}
    </div>
  );
}
