"use client";

import { toast } from "sonner";
import { Calculator, Quote } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { formatCurrency, formatNumber, formatPercent } from "@/lib/utils";
import { useAnalysis, useExtractFinancialFacts, useFinancialMetrics, useRunFinancialAnalysis } from "../hooks";
import type { DocumentRead } from "@/types/api";

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-lg font-semibold">{value}</p>
    </div>
  );
}

export function FinancialsTab({ document }: { document: DocumentRead }) {
  const { data: analysis } = useAnalysis(document.id);
  const { data: metrics, isLoading } = useFinancialMetrics(document.id);
  const runFinancialAnalysis = useRunFinancialAnalysis(document.id);
  const extractFacts = useExtractFinancialFacts(document.id);

  const canRun = !!analysis;
  const canExtractFacts = document.status === "completed";

  const handleRun = () => {
    runFinancialAnalysis.mutate(undefined, {
      onSuccess: () => toast.success("Financial metrics extracted."),
      onError: (error) => toast.error(error.message),
    });
  };

  const handleExtractFacts = () => {
    extractFacts.mutate(undefined, {
      onSuccess: (result) =>
        toast.success(
          `${result.facts_extracted} cited financial fact${result.facts_extracted === 1 ? "" : "s"} extracted.`
        ),
      onError: (error) => toast.error(error.message),
    });
  };

  const extractFactsButton = (variant: "primary" | "secondary") => (
    <button
      type="button"
      onClick={handleExtractFacts}
      disabled={extractFacts.isPending}
      className={
        variant === "primary"
          ? "flex h-9 items-center gap-2 rounded-md border border-input px-4 text-sm font-medium hover:bg-accent disabled:opacity-50"
          : "flex h-8 items-center gap-2 rounded-md border border-input px-3 text-xs font-medium hover:bg-accent disabled:opacity-50"
      }
    >
      <Quote className={variant === "primary" ? "h-4 w-4" : "h-3.5 w-3.5"} />
      {extractFacts.isPending ? "Extracting…" : "Extract Time-Series Facts (with citations)"}
    </button>
  );

  if (isLoading) return <Skeleton className="h-64" />;

  if (!metrics) {
    return (
      <div className="space-y-4">
        <EmptyState
          icon={Calculator}
          title="No financial metrics yet"
          description={
            canRun
              ? "Extract financial KPIs from this document."
              : "Run business analysis first, from the Analysis tab."
          }
        />
        <div className="flex flex-col items-center gap-2">
          {canRun && (
            <button
              type="button"
              onClick={handleRun}
              disabled={runFinancialAnalysis.isPending}
              className="flex h-9 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground shadow-sm hover:bg-primary/90 disabled:opacity-50"
            >
              <Calculator className="h-4 w-4" />
              {runFinancialAnalysis.isPending ? "Extracting…" : "Extract Financial Metrics"}
            </button>
          )}
          {canExtractFacts && extractFactsButton("primary")}
          {(canRun || canExtractFacts) && (
            <p className="max-w-sm text-center text-xs text-muted-foreground">
              &ldquo;Extract Time-Series Facts&rdquo; is what powers Coverage, Findings, Score, and the
              Decision Snapshot — run it here even if you also extract the summary metrics above.
            </p>
          )}
        </div>
      </div>
    );
  }

  const currency = metrics.currency ?? "USD";

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-xs text-muted-foreground">
          Confidence: {metrics.confidence_score !== null ? `${(metrics.confidence_score * 100).toFixed(0)}%` : "—"}
        </p>
        <div className="flex items-center gap-2">
          {canExtractFacts && extractFactsButton("secondary")}
          <button
            type="button"
            onClick={handleRun}
            disabled={runFinancialAnalysis.isPending}
            className="flex h-8 items-center gap-2 rounded-md border border-input px-3 text-xs font-medium hover:bg-accent disabled:opacity-50"
          >
            {runFinancialAnalysis.isPending ? "Re-extracting…" : "Re-run Extraction"}
          </button>
        </div>
      </div>

      <Card className="border-border/50">
        <CardContent className="grid gap-6 py-6 sm:grid-cols-3">
          <Metric label="Revenue" value={formatCurrency(metrics.revenue, currency)} />
          <Metric label="ARR" value={formatCurrency(metrics.arr, currency)} />
          <Metric label="MRR" value={formatCurrency(metrics.mrr, currency)} />
          <Metric label="Gross Margin" value={formatPercent(metrics.gross_margin)} />
          <Metric label="EBITDA" value={formatCurrency(metrics.ebitda, currency)} />
          <Metric label="Burn Rate" value={formatCurrency(metrics.burn_rate, currency)} />
          <Metric label="Runway" value={metrics.runway_months !== null ? `${metrics.runway_months} mo` : "—"} />
          <Metric label="Cash" value={formatCurrency(metrics.cash, currency)} />
          <Metric label="Customers" value={formatNumber(metrics.customers)} />
          <Metric label="Growth Rate" value={formatPercent(metrics.growth_rate)} />
          <Metric label="CAC" value={formatCurrency(metrics.cac, currency)} />
          <Metric label="LTV" value={formatCurrency(metrics.ltv, currency)} />
          <Metric label="Valuation" value={formatCurrency(metrics.valuation, currency)} />
        </CardContent>
      </Card>
    </div>
  );
}