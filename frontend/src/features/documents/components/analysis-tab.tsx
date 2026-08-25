"use client";

import { toast } from "sonner";
import { Sparkles } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { useAnalysis, useAnalyzeDocument } from "../hooks";
import type { DocumentRead } from "@/types/api";
import { DecisionSnapshot } from "./decision-snapshot";

function TagList({ items }: { items: string[] | null }) {
  if (!items || items.length === 0) return <p className="text-sm text-muted-foreground">—</p>;
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((item) => (
        <span key={item} className="rounded-md bg-accent px-2 py-0.5 text-xs">
          {item}
        </span>
      ))}
    </div>
  );
}

export function AnalysisTab({ document }: { document: DocumentRead }) {
  const { data: analysis, isLoading } = useAnalysis(document.id);
  const analyzeDocument = useAnalyzeDocument(document.id);

  const canAnalyze = document.status === "completed";

  const handleAnalyze = () => {
    analyzeDocument.mutate(undefined, {
      onSuccess: () => toast.success("Analysis complete."),
      onError: (error) => toast.error(error.message),
    });
  };

  if (isLoading) return <Skeleton className="h-64" />;

  if (!analysis) {
    return (
      <div className="space-y-4">
        <DecisionSnapshot document={document} />
        <EmptyState
          icon={Sparkles}
          title="No business analysis yet"
          description={
            canAnalyze
              ? "Run AI analysis to extract company details."
              : "Process the document first, from the Overview tab."
          }
        />
        {canAnalyze && (
          <div className="flex justify-center">
            <button
              type="button"
              onClick={handleAnalyze}
              disabled={analyzeDocument.isPending}
              className="flex h-9 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground shadow-sm hover:bg-primary/90 disabled:opacity-50"
            >
              <Sparkles className="h-4 w-4" />
              {analyzeDocument.isPending ? "Analyzing…" : "Run Analysis"}
            </button>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <DecisionSnapshot document={document} />

      <div className="flex justify-end">
        <button
          type="button"
          onClick={handleAnalyze}
          disabled={analyzeDocument.isPending}
          className="flex h-8 items-center gap-2 rounded-md border border-input px-3 text-xs font-medium hover:bg-accent disabled:opacity-50"
        >
          {analyzeDocument.isPending ? "Re-analyzing…" : "Re-run Analysis"}
        </button>
      </div>

      <Card className="border-border/50">
        <CardContent className="space-y-4 py-6">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <p className="text-xs text-muted-foreground">Company</p>
              <p className="mt-1 text-sm font-medium">{analysis.company_name ?? "—"}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Industry</p>
              <p className="mt-1 text-sm font-medium">{analysis.industry ?? "—"}</p>
            </div>
          </div>

          {analysis.summary && (
            <div>
              <p className="text-xs text-muted-foreground">Summary</p>
              <p className="mt-1 text-sm">{analysis.summary}</p>
            </div>
          )}

          {analysis.business_model && (
            <div>
              <p className="text-xs text-muted-foreground">Business Model</p>
              <p className="mt-1 text-sm">{analysis.business_model}</p>
            </div>
          )}

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <p className="mb-1.5 text-xs text-muted-foreground">Key Products</p>
              <TagList items={analysis.key_products} />
            </div>
            <div>
              <p className="mb-1.5 text-xs text-muted-foreground">Revenue Streams</p>
              <TagList items={analysis.revenue_streams} />
            </div>
            <div>
              <p className="mb-1.5 text-xs text-muted-foreground">Target Customers</p>
              <TagList items={analysis.customers} />
            </div>
            <div>
              <p className="mb-1.5 text-xs text-muted-foreground">Competitors</p>
              <TagList items={analysis.competitors} />
            </div>
            <div>
              <p className="mb-1.5 text-xs text-muted-foreground">Risks</p>
              <TagList items={analysis.risks} />
            </div>
            <div>
              <p className="mb-1.5 text-xs text-muted-foreground">Opportunities</p>
              <TagList items={analysis.opportunities} />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}