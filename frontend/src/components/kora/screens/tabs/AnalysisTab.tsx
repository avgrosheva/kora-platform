import type {
  CoverageAssessmentRead,
  DocumentAnalysisRead,
  DocumentStatus,
  InvestmentScoreResponse,
  UnifiedFinding,
} from "@/types/api";
import {
  Badge, EmptyState, FactChips, FactField, GapRow, GhostButton, LoadPulse,
  Meter, Panel, PrimaryButton, SectionLabel,
} from "../../primitives";
import { UnifiedFindingCard } from "./unified-finding";
import { COVERAGE_THRESHOLD_PERCENT } from "./constants";

const POSITIVE_SIGNAL_THRESHOLD = 70;

const SEVERITY_RANK: Record<UnifiedFinding["severity"], number> = {
  critical: 0, high: 1, medium: 2, low: 3, informational: 4,
};

const SCORE_DIMENSIONS = ["financial_score", "growth_score", "risk_score", "market_score", "team_score"] as const;

const CATEGORY_LABELS: Record<string, string> = {
  financial_score: "Financial",
  growth_score: "Growth",
  risk_score: "Risk (stability)",
  market_score: "Market",
  team_score: "Team",
};

export function AnalysisTab({
  status, analysis, score, findings, totalConcerns, coverage,
  isAnalyzing = false, onRerun, onAskKora, onViewAllFindings,
}: {
  status: DocumentStatus;
  analysis: DocumentAnalysisRead | null;
  score: InvestmentScoreResponse | null;
  findings: UnifiedFinding[];
  totalConcerns: number;
  coverage: CoverageAssessmentRead | null;
  isAnalyzing?: boolean;
  onRerun: () => void;
  onAskKora: () => void;
  onViewAllFindings: () => void;
}) {
  const canAnalyze = status === "completed";
  const hasAnyData = !!score || findings.length > 0 || (coverage?.overall_confidence ?? 0) > 0;

  if (!hasAnyData) {
    return (
      <EmptyState
        title="No business analysis yet"
        blurb={
          canAnalyze
            ? "Run AI analysis to extract company details, findings, and a composite score."
            : "Process the document first, from the Overview tab."
        }
        action={
          canAnalyze ? (
            <PrimaryButton onClick={onRerun} className={isAnalyzing ? "pointer-events-none opacity-50" : ""}>
              {isAnalyzing ? "◌ ANALYZING…" : "▷ RUN ANALYSIS"}
            </PrimaryButton>
          ) : undefined
        }
      />
    );
  }

  const scored = score?.overall_score != null;
  const coveragePercent = coverage ? Math.round(coverage.overall_confidence * 100) : 0;

  const positiveSignals = score
    ? SCORE_DIMENSIONS
        .filter((k) => score[k] != null && (score[k] as number) >= POSITIVE_SIGNAL_THRESHOLD)
        .sort((a, b) => (score[b] as number) - (score[a] as number))
        .slice(0, 3)
        .map((k) => ({ label: CATEGORY_LABELS[k], value: Math.round(score[k] as number) }))
    : [];

  const bySeverity = [...findings].sort((a, b) => SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity]);
  const topConcerns = bySeverity.slice(0, 3);
  const recommendedNextStep = bySeverity.find((f) => f.recommended_next_step)?.recommended_next_step ?? null;
  const criticalGaps = coverage?.critical_missing_fields ?? [];

  const f = analysis;

  return (
    <div>
      {/* assessment status */}
      <section className={"relative mb-4 overflow-hidden rounded-2xl border border-white/[0.07] px-7 py-[26px] " + (scored ? "bg-hero-accent" : "bg-hero-warn")}>
        {isAnalyzing && <LoadPulse />}
        <div className="relative flex flex-wrap items-start justify-between gap-9">
          <div className="min-w-[280px]">
            <div className="mb-3.5 font-mono text-[10px] tracking-kicker text-accent-ghost">DECISION SNAPSHOT</div>
            {scored ? (
              <>
                <div className="mb-3 flex items-baseline gap-3.5">
                  <span className="font-mono text-[52px] font-medium tracking-[-2px] text-fg">{Math.round(score!.overall_score as number)}</span>
                  <Badge tone="good">COMPOSITE SCORE</Badge>
                </div>
                <p className="m-0 max-w-[600px] text-[13px] text-fg-muted [text-wrap:pretty]">
                  Composite score computed from document-stated facts and deterministic checks at current coverage.
                </p>
              </>
            ) : (
              <>
                <div className="mb-3 flex items-center gap-[11px]">
                  <span className="kora-blink h-[7px] w-[7px] rounded-full bg-warn shadow-[0_0_12px_2px_rgba(242,178,76,0.7)]" />
                  <span className="text-[23px] font-medium tracking-[-0.5px] text-warn-wash">Not yet scored</span>
                </div>
                <p className="m-0 max-w-[600px] text-[13px] text-fg-muted [text-wrap:pretty]">
                  Kora withholds a composite score until evidence coverage is sufficient.{" "}
                  {criticalGaps.length} critical gap{criticalGaps.length === 1 ? "" : "s"} blocking a result.
                </p>
              </>
            )}
          </div>

          <div className="w-[210px] shrink-0">
            <div className="mb-2.5 flex items-baseline justify-between">
              <span className="font-mono text-[10px] tracking-label text-fg-dim">COVERAGE</span>
              <span className={"font-mono text-[19px] " + (coveragePercent >= COVERAGE_THRESHOLD_PERCENT ? "text-good" : "text-warn")}>
                {coveragePercent}%
              </span>
            </div>
            <Meter thick percent={coveragePercent} tone={coveragePercent >= COVERAGE_THRESHOLD_PERCENT ? "good" : "warn"} markerAt={COVERAGE_THRESHOLD_PERCENT} delayClass="kora-d5" />
            <div className="mt-2 font-mono text-[9.5px] text-fg-faint">SCORE THRESHOLD {COVERAGE_THRESHOLD_PERCENT}%</div>
          </div>
        </div>
      </section>

      {/* signals · concerns · gaps */}
      <div className="mb-4 grid grid-cols-[1fr_1.25fr_0.95fr] gap-4">
        <Panel className="p-5">
          <SectionLabel className="mb-5">TOP POSITIVE SIGNALS</SectionLabel>
          {positiveSignals.length === 0 ? (
            <div className="text-xs text-fg-disabled">No dimension scored {POSITIVE_SIGNAL_THRESHOLD}+ yet.</div>
          ) : (
            <div className="flex flex-col gap-[18px]">
              {positiveSignals.map((signal, i) => (
                <div key={signal.label}>
                  <div className="mb-2 flex items-baseline justify-between">
                    <span className="text-[13px] text-fg-secondary">{signal.label}</span>
                    <span className={"font-mono text-sm " + (signal.value >= 80 ? "text-good" : "text-accent-pale")}>
                      {signal.value}
                    </span>
                  </div>
                  <Meter percent={signal.value} tone={signal.value >= 80 ? "good" : "accent"} delayClass={"kora-d" + Math.min(6, i + 4)} />
                </div>
              ))}
            </div>
          )}
        </Panel>

        <Panel className="p-5">
          <div className="mb-[18px] flex items-baseline justify-between">
            <SectionLabel>TOP CONCERNS</SectionLabel>
            {totalConcerns > 0 && (
              <button
                type="button"
                onClick={onViewAllFindings}
                className="cursor-pointer border-none bg-transparent font-mono text-[9.5px] text-accent-ghost hover:text-accent-pale"
              >
                VIEW ALL {totalConcerns} →
              </button>
            )}
          </div>
          {topConcerns.length === 0 ? (
            <div className="text-xs text-fg-disabled">No findings yet.</div>
          ) : (
            <div className="flex flex-col gap-2.5">
              {topConcerns.map((finding, i) => (
                <UnifiedFindingCard key={i} finding={finding} compact />
              ))}
            </div>
          )}
        </Panel>

        <Panel className="flex flex-col p-5">
          <SectionLabel className="mb-[18px]">CRITICAL GAPS</SectionLabel>
          {criticalGaps.length === 0 ? (
            <div className="text-xs text-fg-disabled">No critical gaps.</div>
          ) : (
            <div className="flex flex-col gap-[9px]">
              {criticalGaps.map((gap) => <GapRow key={gap} label={gap} />)}
            </div>
          )}
          <div className="flex-1" />
          <p className="m-0 mt-[18px] text-[11.5px] text-fg-faint [text-wrap:pretty]">
            Request these to unlock a composite score.
          </p>
        </Panel>
      </div>

      {/* recommended next step */}
      {recommendedNextStep && (
        <div className="mb-4 flex flex-wrap items-center gap-4 rounded-[14px] border border-accent/[0.24] bg-gradient-to-r from-accent/[0.12] to-white/[0.012] px-[22px] py-[18px]">
          <span className="shrink-0 rounded-full border border-accent/30 px-[9px] py-[5px] font-mono text-[9.5px] tracking-label text-accent-ghost">
            NEXT STEP
          </span>
          <span className="text-[13.5px] text-fg-secondary [text-wrap:pretty]">{recommendedNextStep}</span>
          <div className="flex-1" />
          <PrimaryButton className="shrink-0 !py-[9px] !text-[10.5px]" onClick={onAskKora}>ASK KORA</PrimaryButton>
        </div>
      )}

      <div className="mb-5 flex justify-end gap-2.5">
        {!recommendedNextStep && <GhostButton onClick={onAskKora}>ASK KORA</GhostButton>}
        {canAnalyze && (
          <GhostButton onClick={onRerun} className={isAnalyzing ? "pointer-events-none opacity-50" : ""}>
            {isAnalyzing ? "RE-ANALYZING…" : "RE-RUN ANALYSIS"}
          </GhostButton>
        )}
      </div>

      {/* extracted facts */}
      <Panel className="px-[26px] py-6">
        <div className="mb-6 flex items-baseline justify-between">
          <h2 className="text-[13.5px] font-semibold">Extracted facts</h2>
          <span className="font-mono text-[9.5px] tracking-label text-fg-faint">SOURCE · DOCUMENT ANALYSIS</span>
        </div>
        {!f ? (
          <div className="py-4 text-center text-[12.5px] text-fg-dim">
            Not yet extracted — run analysis to populate company facts.
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-x-10 gap-y-[26px]">
            <FactField label="COMPANY"><div className="text-sm text-fg">{f.company_name ?? "—"}</div></FactField>
            <FactField label="INDUSTRY"><div className="text-sm text-fg">{f.industry ?? "—"}</div></FactField>
            <FactField label="SUMMARY" wide>
              <div className="text-sm text-fg-tertiary [text-wrap:pretty]">{f.summary ?? "—"}</div>
            </FactField>
            <FactField label="BUSINESS_MODEL" wide>
              <div className="text-sm text-fg-tertiary [text-wrap:pretty]">{f.business_model ?? "—"}</div>
            </FactField>
            <FactField label="KEY_PRODUCTS"><FactChips items={f.key_products ?? []} /></FactField>
            <FactField label="REVENUE_STREAMS"><FactChips items={f.revenue_streams ?? []} /></FactField>
            <FactField label="TARGET_CUSTOMERS"><FactChips items={f.customers ?? []} /></FactField>
            <FactField label="COMPETITORS"><FactChips items={f.competitors ?? []} /></FactField>
            <FactField label="RISKS"><FactChips items={f.risks ?? []} tone="danger" /></FactField>
            <FactField label="OPPORTUNITIES"><FactChips items={f.opportunities ?? []} tone="good" /></FactField>
          </div>
        )}
      </Panel>
    </div>
  );
}
