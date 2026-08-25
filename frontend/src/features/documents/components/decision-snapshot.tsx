"use client";

import { ArrowRight, CheckCircle2, ShieldQuestion, TrendingUp } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { UnifiedFindingSeverityBadge } from "@/components/shared/unified-finding-severity-badge";
import { FindingTypeBadge } from "@/components/shared/finding-type-badge";
import { useDocumentCoverage, useDocumentFindings, useScore } from "../hooks";
import type { CategoryBreakdownEntry, DocumentRead, UnifiedFindingSeverity } from "@/types/api";

const CATEGORY_LABELS: Record<string, string> = {
  financial_score: "Financial",
  growth_score: "Growth",
  risk_score: "Risk (stability)",
  market_score: "Market",
  team_score: "Team",
};

const SEVERITY_RANK: Record<UnifiedFindingSeverity, number> = {
  critical: 0, high: 1, medium: 2, low: 3, informational: 4,
};

// A category counts as a "positive signal" only once it's actually
// assessed and clears a reasonably high bar -- this is a display
// threshold on top of assessment_status, not a substitute for it: the
// headline score can still be null (insufficient evidence overall)
// while one individual, well-supported dimension is worth surfacing.
const POSITIVE_SIGNAL_THRESHOLD = 70;

/**
 * A one-glance summary for the Analysis tab: is there enough evidence
 * to trust a score, what's going well, what's concerning, what's
 * missing, and what to ask next. Reads only already-computed data
 * (Score, Findings, Coverage) -- no AI call is triggered by loading
 * this panel. Renders nothing at all if none of those three have any
 * data yet, rather than showing an empty-looking card.
 */
export function DecisionSnapshot({ document }: { document: DocumentRead }) {
  const { data: score } = useScore(document.id);
  const { data: findingsData } = useDocumentFindings(document.id);
  const { data: coverage } = useDocumentCoverage(document.id);

  const findings = findingsData?.findings ?? [];
  const hasAnyData = !!score || findings.length > 0 || (coverage?.overall_confidence ?? 0) > 0;

  if (!hasAnyData) return null;

  const positiveSignals = score?.category_breakdown
    ? (Object.entries(score.category_breakdown) as [string, CategoryBreakdownEntry][])
        .filter(([, entry]) => entry.status === "assessed" && (entry.score ?? 0) >= POSITIVE_SIGNAL_THRESHOLD)
        .sort(([, a], [, b]) => (b.score ?? 0) - (a.score ?? 0))
        .slice(0, 3)
    : [];

  const bySeverity = [...findings].sort((a, b) => SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity]);
  const topConcerns = bySeverity.slice(0, 3);
  const recommendedNextStep = bySeverity.find((f) => f.recommended_next_step)?.recommended_next_step;
  const criticalGaps = coverage?.critical_missing_fields ?? [];

  const statusLabel =
    score?.assessment_status === "sufficient_evidence"
      ? "Sufficient evidence for a score"
      : score?.assessment_status === "insufficient_evidence"
        ? "Insufficient evidence for a composite score"
        : "Not yet scored";
  const StatusIcon = score?.assessment_status === "sufficient_evidence" ? CheckCircle2 : ShieldQuestion;

  return (
    <Card className="border-border/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm font-medium">
          <StatusIcon className="h-4 w-4 text-muted-foreground" />
          Decision Snapshot
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={score?.assessment_status === "sufficient_evidence" ? "secondary" : "outline"}>
            {statusLabel}
          </Badge>
          {score?.overall_score !== null && score?.overall_score !== undefined && (
            <span className="text-xs text-muted-foreground">Overall score: {score.overall_score.toFixed(0)}/100</span>
          )}
          {coverage && (
            <span className="text-xs text-muted-foreground">
              Coverage: {(coverage.overall_confidence * 100).toFixed(0)}%
            </span>
          )}
        </div>

        {positiveSignals.length > 0 && (
          <div>
            <p className="mb-1.5 text-xs font-medium text-muted-foreground">Top positive signals</p>
            <div className="flex flex-wrap gap-1.5">
              {positiveSignals.map(([key, entry]) => (
                <Badge key={key} variant="outline" className="gap-1 text-[10px]">
                  <TrendingUp className="h-3 w-3" />
                  {CATEGORY_LABELS[key] ?? key}: {entry.score?.toFixed(0)}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {topConcerns.length > 0 && (
          <div>
            <p className="mb-1.5 text-xs font-medium text-muted-foreground">Top concerns</p>
            <div className="space-y-1.5">
              {topConcerns.map((finding, index) => (
                <div key={index} className="flex flex-wrap items-center gap-1.5 text-xs">
                  <UnifiedFindingSeverityBadge severity={finding.severity} />
                  <FindingTypeBadge type={finding.type} />
                  <span>{finding.title}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {criticalGaps.length > 0 && (
          <div>
            <p className="mb-1.5 text-xs font-medium text-muted-foreground">Critical gaps</p>
            <div className="flex flex-wrap gap-1.5">
              {criticalGaps.map((field) => (
                <Badge key={field} variant="destructive" className="text-[10px]">
                  {field.replace(/_/g, " ")}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {recommendedNextStep && (
          <p className="flex items-start gap-1.5 rounded-md bg-accent/50 p-2 text-xs">
            <ArrowRight className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
            <span>
              <span className="font-medium">Recommended next step: </span>
              {recommendedNextStep}
            </span>
          </p>
        )}
      </CardContent>
    </Card>
  );
}
