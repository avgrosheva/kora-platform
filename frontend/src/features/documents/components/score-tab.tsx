"use client";

import { toast } from "sonner";
import { Gauge } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { useCalculateScore, useFinancialMetrics, useScore } from "../hooks";
import type { DocumentRead } from "@/types/api";

import { ScoreBreakdownCard } from "./score-breakdown-card";

function SubScore({ label, value }: { label: string; value: number | null }) {
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium">{value !== null ? value.toFixed(0) : "—"}</span>
      </div>
      <Progress value={value ?? 0} className="h-1.5" />
    </div>
  );
}

export function ScoreTab({ document }: { document: DocumentRead }) {
  const { data: financials } = useFinancialMetrics(document.id);
  const { data: score, isLoading } = useScore(document.id);
  const calculateScore = useCalculateScore(document.id);

  const canScore = !!financials;

  const handleCalculate = () => {
    calculateScore.mutate(undefined, {
      onSuccess: () => toast.success("Investment score calculated."),
      onError: (error) => toast.error(error.message),
    });
  };

  if (isLoading) return <Skeleton className="h-64" />;

  if (!score) {
    return (
      <div className="space-y-4">
        <EmptyState
          icon={Gauge}
          title="Not scored yet"
          description={
            canScore
              ? "Calculate a deterministic investment score from available data."
              : "Extract financial metrics or run analysis first."
          }
        />
        <div className="flex justify-center">
          <button
            type="button"
            onClick={handleCalculate}
            disabled={calculateScore.isPending}
            className="flex h-9 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground shadow-sm hover:bg-primary/90 disabled:opacity-50"
          >
            <Gauge className="h-4 w-4" />
            {calculateScore.isPending ? "Calculating…" : "Calculate Score"}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <button
          type="button"
          onClick={handleCalculate}
          disabled={calculateScore.isPending}
          className="flex h-8 items-center gap-2 rounded-md border border-input px-3 text-xs font-medium hover:bg-accent disabled:opacity-50"
        >
          {calculateScore.isPending ? "Recalculating…" : "Recalculate"}
        </button>
      </div>

      <Card className="border-border/50">
        <CardContent className="space-y-6 py-6">
          <div className="text-center">
            <p className="text-xs text-muted-foreground">Overall Score</p>
            <p className="text-5xl font-bold tracking-tight">
              {score.overall_score !== null ? score.overall_score.toFixed(1) : "—"}
            </p>
            <p className="text-xs text-muted-foreground">
              Confidence: {score.confidence_score !== null ? `${(score.confidence_score * 100).toFixed(0)}%` : "—"}
            </p>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <SubScore label="Financial" value={score.financial_score} />
            <SubScore label="Growth" value={score.growth_score} />
            <SubScore label="Risk (stability)" value={score.risk_score} />
            <SubScore label="Market" value={score.market_score} />
          </div>

          {score.reasoning && (
            <div>
              <p className="mb-1 text-xs text-muted-foreground">Reasoning</p>
              <p className="text-sm leading-relaxed text-muted-foreground">{score.reasoning}</p>
            </div>
          )}
          {score.category_breakdown && (
            <ScoreBreakdownCard
              breakdown={score.category_breakdown}
              methodologyVersion={score.methodology_version}
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}