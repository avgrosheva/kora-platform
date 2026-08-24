"use client";

import { ClipboardCheck } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { useDocumentCoverage, useMissingInformation } from "../hooks";
import type { DocumentRead } from "@/types/api";

const CATEGORY_LABELS: Record<string, string> = {
  company: "Company Overview", financial: "Financial", market: "Market", team: "Team",
};

export function CoverageTab({ document }: { document: DocumentRead }) {
  const { data: coverage, isLoading: coverageLoading } = useDocumentCoverage(document.id);
  const { data: missingInfo, isLoading: missingLoading } = useMissingInformation(document.id);

  if (coverageLoading || missingLoading) return <Skeleton className="h-96" />;

  if (!coverage) {
    return <EmptyState icon={ClipboardCheck} title="Coverage not available" />;
  }

  return (
    <div className="space-y-4">
      <Card className="border-border/50">
        <CardHeader>
          <CardTitle className="flex items-center justify-between text-sm font-medium">
            <span>Analysis Coverage</span>
            <span className="text-2xl font-bold">{(coverage.overall_confidence * 100).toFixed(0)}%</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-xs text-muted-foreground">
            Reflects how much of a thorough due-diligence checklist this document's data covers —
            not an investment-quality score. A strong company with a thin document will show low coverage here.
          </p>
          {Object.entries(coverage.coverage).map(([category, cat]) => (
            <div key={category}>
              <div className="mb-1 flex items-center justify-between text-xs">
                <span className="text-muted-foreground">{CATEGORY_LABELS[category] ?? category}</span>
                <span className="font-medium">{cat.found}/{cat.required}</span>
              </div>
              <Progress value={cat.score * 100} className="h-1.5" />
            </div>
          ))}
          {coverage.critical_missing_fields.length > 0 && (
            <div>
              <p className="mb-1.5 text-xs text-muted-foreground">Critical gaps</p>
              <div className="flex flex-wrap gap-1.5">
                {coverage.critical_missing_fields.map((field) => (
                  <Badge key={field} variant="destructive" className="text-[10px]">{field.replace(/_/g, " ")}</Badge>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {missingInfo && (
        <Card className="border-border/50">
          <CardHeader><CardTitle className="text-sm font-medium">Missing Information by Category</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {missingInfo.by_category.filter((c) => c.missing.length > 0).map((cat) => (
              <div key={cat.category}>
                <p className="mb-1.5 text-xs font-medium capitalize">{cat.category}</p>
                <div className="flex flex-wrap gap-1.5">
                  {cat.missing.map((field) => (
                    <Badge key={field} variant="outline" className="text-[10px]">{field.replace(/_/g, " ")}</Badge>
                  ))}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}