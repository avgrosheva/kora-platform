import type { DueDiligenceV2Response, RecommendationStatus } from "@/types/api";
import { Badge, EmptyState, GhostButton, Panel, PrimaryButton } from "../../primitives";

const RECOMMENDATION_LABEL: Record<RecommendationStatus, string> = {
  strong_candidate: "STRONG CANDIDATE",
  worth_exploring: "WORTH EXPLORING",
  needs_more_info: "NEEDS MORE INFO",
  concerns_identified: "CONCERNS IDENTIFIED",
};

const RECOMMENDATION_TONE: Record<RecommendationStatus, "good" | "accent" | "neutral" | "danger"> = {
  strong_candidate: "good",
  worth_exploring: "accent",
  needs_more_info: "neutral",
  concerns_identified: "danger",
};

export function DueDiligenceV2Tab({ report, isGenerating = false, onGenerate, onExportMarkdown, onExportPdf }: {
  /** Session-only: cleared on tab remount / re-navigation, same as the mutation it comes from. */
  report: DueDiligenceV2Response | null;
  isGenerating?: boolean;
  onGenerate: () => void;
  onExportMarkdown: () => void;
  onExportPdf: () => void;
}) {
  if (!report) {
    return (
      <EmptyState
        title="No report generated yet"
        blurb="A complete written summary you can download and share — verified facts, red flags, and suggested questions for the founders, grounded in what's actually in the document."
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

      <Panel className="mb-4 px-[26px] py-6">
        <div className="mb-3.5 flex flex-wrap items-center justify-between gap-4">
          <h2 className="text-[16px] font-semibold">Executive summary</h2>
          <Badge tone={RECOMMENDATION_TONE[report.recommendation_status]}>{RECOMMENDATION_LABEL[report.recommendation_status]}</Badge>
        </div>
        <p className="m-0 mb-6 text-[14.5px] leading-[1.7] text-fg-tertiary [text-wrap:pretty]">{report.executive_summary}</p>
        {report.verified_facts.length > 0 && (
          <div className="grid grid-cols-[repeat(auto-fit,minmax(150px,1fr))] gap-5 border-t border-white/[0.055] pt-5">
            {report.verified_facts.map((fact) => (
              <div key={fact.label}>
                <div className="mb-2 font-mono text-[10.5px] tracking-label text-fg-faint">{fact.label.toUpperCase()}</div>
                <div className="font-mono text-[19px] text-fg">{fact.value_display}</div>
              </div>
            ))}
          </div>
        )}
      </Panel>

      {report.red_flags.length > 0 && (
        <Panel className="mb-4 px-6 py-[22px]">
          <div className="mb-4 flex items-center gap-2.5">
            <span className="h-1.5 w-1.5 rounded-full bg-danger shadow-[0_0_10px_2px_rgba(255,92,92,0.7)]" />
            <h2 className="text-[15px] font-semibold text-danger-pale">Red flags ({report.red_flags.length})</h2>
          </div>
          <div className="flex flex-col gap-2.5">
            {report.red_flags.map((flag, i) => (
              <div
                key={i}
                className={"rounded-[10px] border px-4 py-3.5 " + (flag.severity === "critical" ? "border-danger/[0.18] bg-danger/[0.05]" : "border-warn/[0.16] bg-warn/[0.04]")}
              >
                <div className="mb-1.5 flex flex-wrap items-center gap-2.5">
                  <Badge tone={flag.severity === "critical" ? "danger" : flag.severity === "warning" ? "warn" : "neutral"}>
                    {flag.severity.toUpperCase()}
                  </Badge>
                  <span className="text-[14.5px] font-medium">{flag.title}</span>
                </div>
                <p className="m-0 text-[13px] leading-relaxed text-fg-muted [text-wrap:pretty]">{flag.description}</p>
              </div>
            ))}
          </div>
        </Panel>
      )}

      {report.founder_questions.length > 0 && (
        <Panel className="mb-4 px-6 py-[22px]">
          <h2 className="mb-4 text-[15px] font-semibold">Questions for the founders</h2>
          <div className="flex flex-col gap-3">
            {report.founder_questions.map((q, i) => (
              <div key={i} className="flex items-start gap-3">
                <span className="mt-0.5 shrink-0">
                  <Badge tone={q.priority === "high" ? "danger" : "warn"}>{q.priority.toUpperCase()}</Badge>
                </span>
                <span className="text-[14px] leading-relaxed text-fg-tertiary [text-wrap:pretty]">{q.question}</span>
              </div>
            ))}
          </div>
        </Panel>
      )}

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
