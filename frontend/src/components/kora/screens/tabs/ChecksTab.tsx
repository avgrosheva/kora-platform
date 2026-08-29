import type { UnifiedFinding } from "@/types/api";
import { EmptyState } from "../../primitives";
import { UnifiedFindingCard } from "./unified-finding";

export function ChecksTab({
  findings, deterministicCount, documentStatedCount, aiInferredCount, hasFinancialEvidence,
}: {
  findings: UnifiedFinding[];
  deterministicCount: number;
  documentStatedCount: number;
  aiInferredCount: number;
  /** Distinguishes "nothing to check against yet" from "checked, and it's clean". */
  hasFinancialEvidence: boolean;
}) {
  if (findings.length === 0) {
    return hasFinancialEvidence ? (
      <EmptyState
        title="Nothing concerning found"
        blurb="Financial facts and extracted risk claims were checked and nothing was flagged. This does not mean the underlying business has no risks — only that nothing in the uploaded materials contradicted itself or matched a known risk pattern."
      />
    ) : (
      <EmptyState
        title="Not enough information to check yet"
        blurb="No financial facts have been extracted yet, so there's nothing to check them against. Extract financial data first, from the Financials tab, then check back."
      />
    );
  }

  return (
    <div>
      <p className="m-0 mb-[18px] text-[13.5px] text-fg-dim [text-wrap:pretty]">
        Automated checks and things Kora flagged as worth a closer look.
      </p>
      <div className="mb-[18px] flex flex-wrap items-center gap-5">
        {deterministicCount > 0 && (
          <Legend tone="warn" label={deterministicCount + " DETERMINISTIC INCONSISTENC" + (deterministicCount === 1 ? "Y" : "IES")} />
        )}
        {documentStatedCount > 0 && (
          <Legend tone="danger" label={documentStatedCount + " DILIGENCE RISK" + (documentStatedCount === 1 ? "" : "S") + " IDENTIFIED"} />
        )}
        {aiInferredCount > 0 && (
          <Legend tone="accent" label={aiInferredCount + " KORA-INFERRED CONCERN" + (aiInferredCount === 1 ? "" : "S")} />
        )}
      </div>
      <div className="flex flex-col gap-3">
        {findings.map((finding, i) => (
          <UnifiedFindingCard key={i} finding={finding} />
        ))}
      </div>
    </div>
  );
}

function Legend({ tone, label }: { tone: "warn" | "danger" | "accent"; label: string }) {
  const dot = tone === "warn" ? "bg-warn shadow-glow-warn" : tone === "danger" ? "bg-danger shadow-glow-danger" : "bg-accent-bright shadow-glow-accent";
  return (
    <div className="flex items-center gap-2">
      <span className={"h-1.5 w-1.5 rounded-full " + dot} />
      <span className="font-mono text-[11.5px] text-fg-quiet">{label}</span>
    </div>
  );
}
