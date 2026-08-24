"use client";

import { ShieldCheck, ShieldAlert } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { FindingSeverityBadge } from "@/components/shared/finding-severity-badge";
import { useDocumentChecks } from "../hooks";
import type { DocumentRead } from "@/types/api";

export function ChecksTab({ document }: { document: DocumentRead }) {
  const { data, isLoading } = useDocumentChecks(document.id);

  if (isLoading) return <Skeleton className="h-64" />;

  if (!data || data.findings.length === 0) {
    return (
      <EmptyState
        icon={ShieldCheck}
        title="No issues found"
        description="Deterministic checks ran against this document's financial facts and found nothing to flag. Extract financial facts first if this seems unexpected."
      />
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex gap-3 text-xs text-muted-foreground">
        <span>{data.critical_count} critical</span>
        <span>{data.warning_count} warning</span>
        <span>{data.info_count} info</span>
      </div>

      <div className="space-y-3">
        {data.findings.map((finding) => (
          <Card key={finding.id} className="border-border/50">
            <CardContent className="py-4">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1">
                  <div className="mb-1 flex items-center gap-2">
                    <FindingSeverityBadge severity={finding.severity} />
                    <span className="text-xs text-muted-foreground">{finding.category.replace(/_/g, " ")}</span>
                  </div>
                  <h3 className="text-sm font-semibold">{finding.title}</h3>
                  <p className="mt-1 text-sm text-muted-foreground">{finding.description}</p>
                  {finding.suggested_question && (
                    <p className="mt-2 flex items-start gap-1.5 rounded-md bg-accent/50 p-2 text-xs">
                      <ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                      <span><span className="font-medium">Ask the founder:</span> {finding.suggested_question}</span>
                    </p>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}