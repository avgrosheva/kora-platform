import type { CoverageAssessmentRead, InvestmentScoreResponse } from "@/types/api";
import { Badge, EmptyState, FieldLabel, GapChip, GhostButton, Meter, Panel, PrimaryButton } from "../../primitives";
import { COVERAGE_THRESHOLD_PERCENT } from "./constants";

const SUB_SCORES: { key: "financial_score" | "growth_score" | "risk_score" | "market_score"; label: string }[] = [
  { key: "financial_score", label: "FINANCIAL" },
  { key: "growth_score", label: "GROWTH" },
  { key: "risk_score", label: "RISK (STABILITY)" },
  { key: "market_score", label: "MARKET" },
];

const CATEGORY_LABELS: Record<string, string> = {
  financial_score: "Financial", growth_score: "Growth", risk_score: "Risk (Stability)", market_score: "Market", team_score: "Team",
};

export function ScoreTab({ score, coverage, canScore, isCalculating = false, onCalculate }: {
  score: InvestmentScoreResponse | null;
  coverage: CoverageAssessmentRead | null;
  /** Financial metrics must exist before a score can be calculated. */
  canScore: boolean;
  isCalculating?: boolean;
  onCalculate: () => void;
}) {
  if (!score) {
    return (
      <EmptyState
        title="Not scored yet"
        blurb={canScore ? "Calculate a deterministic investment score from available data." : "Extract financial metrics or run analysis first."}
        action={
          canScore ? (
            <PrimaryButton onClick={onCalculate} className={isCalculating ? "pointer-events-none opacity-50" : ""}>
              {isCalculating ? "◌ CALCULATING…" : "▷ CALCULATE SCORE"}
            </PrimaryButton>
          ) : undefined
        }
      />
    );
  }

  const insufficient = score.overall_score == null;
  const coveragePercent = coverage ? Math.round(coverage.overall_confidence * 100) : 0;
  const criticalGaps = coverage?.critical_missing_fields ?? [];
  const confidencePercent = score.confidence_score != null ? Math.round(score.confidence_score * 100) : null;

  return (
    <div>
      <div className="mb-4 flex justify-end">
        <GhostButton onClick={onCalculate} className={isCalculating ? "pointer-events-none opacity-50" : ""}>
          {isCalculating ? "RECALCULATING…" : "RECALCULATE"}
        </GhostButton>
      </div>

      {insufficient ? (
        <section className="relative mb-5 overflow-hidden rounded-2xl border border-white/[0.07] bg-hero-warn px-[30px] py-[52px] text-center">
          <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-full border border-warn/30 bg-warn/[0.07] shadow-[0_0_40px_-14px_rgba(242,178,76,0.7)]">
            <span className="h-[18px] w-0.5 rotate-[38deg] rounded bg-warn shadow-[0_0_8px_rgba(242,178,76,0.9)]" />
          </div>
          <div className="mb-3.5 font-mono text-[11px] tracking-[0.18em] text-fg-muted">NO SCORE YET</div>
          <h2 className="m-0 mb-2.5 text-[22px] font-medium tracking-[-0.5px] text-warn-wash">
            Not enough information yet to give a confident rating
          </h2>
          <p className="mx-auto m-0 max-w-[520px] text-[14px] leading-relaxed text-fg-dim [text-wrap:pretty]">
            Kora shows no number rather than a misleading one. Coverage is {coveragePercent}% against a{" "}
            {COVERAGE_THRESHOLD_PERCENT}% threshold, with {criticalGaps.length} critical gap{criticalGaps.length === 1 ? "" : "s"} outstanding.
          </p>
          {criticalGaps.length > 0 && (
            <div className="my-5 flex flex-wrap justify-center gap-2">
              {criticalGaps.map((gap) => <GapChip key={gap} label={gap} />)}
            </div>
          )}
        </section>
      ) : (
        <section className="mb-5 overflow-hidden rounded-2xl border border-white/[0.07] bg-hero-accent px-[30px] py-11 text-center">
          <div className="mb-4 font-mono text-[11px] tracking-[0.18em] text-accent-ghost">INVESTMENT SCORE</div>
          <div className="font-mono text-[76px] leading-none tracking-[-3px] text-fg [text-shadow:0_0_40px_rgba(77,141,255,0.55)]">
            {Math.round(score.overall_score as number)}
          </div>
          <p className="m-0 mt-3.5 text-[14px] text-fg-dim">
            Deterministic score from available evidence
            {confidencePercent != null ? " · confidence " + confidencePercent + "%" : ""}
          </p>
        </section>
      )}

      <div className="mb-5 grid grid-cols-[repeat(auto-fit,minmax(200px,1fr))] gap-3.5">
        {SUB_SCORES.map((s) => {
          const value = score[s.key];
          return (
            <Panel key={s.key} className="!rounded-xl p-[18px]">
              <FieldLabel>{s.label}</FieldLabel>
              <div className={"font-mono text-[20px] " + (value == null ? "text-fg-ghost" : value >= 80 ? "text-good" : "text-accent-pale")}>
                {value != null ? Math.round(value) : "—"}
              </div>
            </Panel>
          );
        })}
      </div>

      {score.reasoning && (
        <Panel className="mb-5 px-[22px] py-5">
          <FieldLabel>REASONING</FieldLabel>
          <p className="m-0 text-[14px] leading-relaxed text-fg-tertiary [text-wrap:pretty]">{score.reasoning}</p>
        </Panel>
      )}

      {score.category_breakdown && (
        <Panel className="px-[22px] py-5">
          <div className="mb-5 flex items-baseline justify-between">
            <h2 className="text-[14.5px] font-semibold">Score breakdown</h2>
            {score.methodology_version && (
              <span className="font-mono text-[10.5px] tracking-label text-fg-faint">
                {score.methodology_version.replace("kora_score_", "").toUpperCase()}
              </span>
            )}
          </div>
          <div className="flex flex-col gap-[18px]">
            {Object.entries(score.category_breakdown).map(([key, entry]) => (
              <div key={key}>
                <div className="mb-2 flex items-baseline justify-between">
                  <span className="text-[14px] text-fg-secondary">{CATEGORY_LABELS[key] ?? key}</span>
                  {entry.status === "not_assessable" ? (
                    <Badge tone="neutral">NOT ASSESSABLE</Badge>
                  ) : (
                    <span className="font-mono text-[12.5px] text-fg-muted">
                      weight {Math.round(entry.weight * 100)}% ·{" "}
                      <span className="text-accent-pale">{entry.score != null ? Math.round(entry.score) : "—"}</span>
                    </span>
                  )}
                </div>
                <Meter percent={entry.score ?? 0} tone={entry.status === "not_assessable" ? "warn" : "accent"} />
                {entry.contribution != null && (
                  <div className="mt-1.5 font-mono text-[11px] text-fg-faint">
                    CONTRIBUTES {entry.contribution.toFixed(1)} PTS TO OVERALL SCORE
                  </div>
                )}
              </div>
            ))}
          </div>
        </Panel>
      )}
    </div>
  );
}
