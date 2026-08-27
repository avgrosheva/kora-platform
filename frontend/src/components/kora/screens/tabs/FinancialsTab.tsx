import type { FinancialMetricsRead } from "@/types/api";
import { formatCurrency, formatNumber, formatPercent } from "@/lib/utils";
import { EmptyState, GhostButton, MetricCell, Panel, PrimaryButton } from "../../primitives";

export function FinancialsTab({
  metrics, canRun, canExtractFacts, isRunning = false, isExtractingFacts = false, onRun, onExtractFacts,
}: {
  metrics: FinancialMetricsRead | null;
  /** Business analysis (Analysis tab) must exist before summary metrics can be extracted. */
  canRun: boolean;
  /** Document must be processed before time-series facts can be extracted. */
  canExtractFacts: boolean;
  isRunning?: boolean;
  isExtractingFacts?: boolean;
  onRun: () => void;
  onExtractFacts: () => void;
}) {
  if (!metrics) {
    return (
      <div>
        <EmptyState title="No financial metrics yet" blurb="Extract financial KPIs from this document." />
        <div className="mt-[22px] flex flex-col items-center gap-3">
          <div className="flex flex-wrap justify-center gap-2.5">
            {canRun && (
              <PrimaryButton onClick={onRun} className={isRunning ? "pointer-events-none opacity-50" : ""}>
                {isRunning ? "EXTRACTING…" : "EXTRACT FINANCIAL METRICS"}
              </PrimaryButton>
            )}
            {canExtractFacts && (
              <GhostButton tone="neutral" onClick={onExtractFacts} className={isExtractingFacts ? "pointer-events-none opacity-50" : ""}>
                {isExtractingFacts ? "EXTRACTING…" : "EXTRACT TIME-SERIES FACTS"}
              </GhostButton>
            )}
          </div>
          {canRun || canExtractFacts ? (
            <p className="m-0 max-w-[420px] text-center text-[11.5px] leading-relaxed text-fg-faint [text-wrap:pretty]">
              "Extract Time-Series Facts" powers Coverage, Findings, Score, and the Decision Snapshot —
              run it here even if you also extract the summary metrics above.
            </p>
          ) : (
            <p className="m-0 max-w-[420px] text-center text-[11.5px] leading-relaxed text-fg-faint [text-wrap:pretty]">
              Process the document, then run business analysis, from the Overview and Analysis tabs.
            </p>
          )}
        </div>
      </div>
    );
  }

  const currency = metrics.currency ?? "USD";
  const money = (v: number | null) => (v != null ? formatCurrency(v, currency) : null);
  const pct = (v: number | null) => (v != null ? formatPercent(v) : null);
  const num = (v: number | null) => (v != null ? formatNumber(v) : null);
  const confidencePercent = metrics.confidence_score != null ? Math.round(metrics.confidence_score * 100) : null;

  const rows: { key: string; value: string | null }[] = [
    { key: "REVENUE", value: money(metrics.revenue) },
    { key: "ARR", value: money(metrics.arr) },
    { key: "MRR", value: money(metrics.mrr) },
    { key: "GROSS_MARGIN", value: pct(metrics.gross_margin) },
    { key: "EBITDA", value: money(metrics.ebitda) },
    { key: "BURN_RATE", value: money(metrics.burn_rate) },
    { key: "RUNWAY", value: metrics.runway_months != null ? `${metrics.runway_months} mo` : null },
    { key: "CASH", value: money(metrics.cash) },
    { key: "CUSTOMERS", value: num(metrics.customers) },
    { key: "GROWTH_RATE", value: pct(metrics.growth_rate) },
    { key: "CAC", value: money(metrics.cac) },
    { key: "LTV", value: money(metrics.ltv) },
    { key: "VALUATION", value: money(metrics.valuation) },
  ];

  return (
    <div>
      <div className="mb-3.5 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-2.5">
          <span className="font-mono text-[10px] tracking-label text-fg-dim">CONFIDENCE</span>
          <span className="font-mono text-[13px] text-accent-pale">{confidencePercent != null ? `${confidencePercent}%` : "—"}</span>
          {confidencePercent != null && (
            <span className="inline-block h-1 w-[90px] overflow-hidden rounded bg-white/[0.08]">
              <span
                className="block h-full bg-gradient-to-r from-accent/40 to-accent-bright shadow-glow-accent"
                style={{ width: confidencePercent + "%" }}
              />
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {canExtractFacts && (
            <GhostButton onClick={onExtractFacts} className={isExtractingFacts ? "pointer-events-none opacity-50" : ""}>
              {isExtractingFacts ? "EXTRACTING…" : "EXTRACT TIME-SERIES FACTS"}
            </GhostButton>
          )}
          <GhostButton onClick={onRun} className={isRunning ? "pointer-events-none opacity-50" : ""}>
            {isRunning ? "RE-EXTRACTING…" : "RE-RUN EXTRACTION"}
          </GhostButton>
        </div>
      </div>

      <Panel className="grid grid-cols-[repeat(auto-fit,minmax(190px,1fr))] py-1.5">
        {rows.map((m) => (
          <MetricCell key={m.key} label={m.key} value={m.value} />
        ))}
      </Panel>
    </div>
  );
}
