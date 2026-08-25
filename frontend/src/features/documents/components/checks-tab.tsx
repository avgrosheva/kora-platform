"use client";

import { ShieldAlert, ShieldCheck, ShieldQuestion } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { UnifiedFindingSeverityBadge } from "@/components/shared/unified-finding-severity-badge";
import { FindingTypeBadge } from "@/components/shared/finding-type-badge";
import { useDocumentCoverage, useDocumentFindings } from "../hooks";
import type { DocumentRead } from "@/types/api";

// Rendered above the finding list whenever there's at least one -- never
// collapsed into a single generic count line, since "N deterministic
// checks fired" and "N diligence risks identified" and "N Kora-inferred
// concerns" are different statements about the document.
function FindingsSummaryLine({
  deterministic,
  documentStated,
  aiInferred,
}: {
  deterministic: number;
  documentStated: number;
  aiInferred: number;
}) {
  const parts: string[] = [];
  if (deterministic > 0) parts.push(`${deterministic} deterministic inconsistenc${deterministic === 1 ? "y" : "ies"}`);
  if (documentStated > 0) parts.push(`${documentStated} diligence risk${documentStated === 1 ? "" : "s"} identified`);
  if (aiInferred > 0) parts.push(`${aiInferred} Kora-inferred concern${aiInferred === 1 ? "" : "s"}`);
  return <p className="text-xs text-muted-foreground">{parts.join(" · ")}</p>;
}

export function ChecksTab({ document }: { document: DocumentRead }) {
  const { data: findingsData, isLoading: findingsLoading } = useDocumentFindings(document.id);
  const { data: coverage, isLoading: coverageLoading } = useDocumentCoverage(document.id);

  if (findingsLoading || coverageLoading) return <Skeleton className="h-64" />;

  const findings = findingsData?.findings ?? [];

  if (findings.length === 0) {
    // Distinguish "we haven't extracted enough to check anything yet"
    // from "we checked, and it's genuinely clean" -- collapsing these
    // into one "No issues found" message is exactly the bug this tab
    // used to have.
    const hasFinancialEvidence = (coverage?.coverage.financial?.found ?? 0) > 0;

    if (!hasFinancialEvidence) {
      return (
        <EmptyState
          icon={ShieldQuestion}
          title="Insufficient information to evaluate"
          description="No financial facts have been extracted yet, so deterministic checks have nothing to run against. Extract financial data first, then check back."
        />
      );
    }

    return (
      <EmptyState
        icon={ShieldCheck}
        title="No deterministic inconsistencies detected"
        description="Financial facts and extracted risk claims were checked and nothing was flagged. This does not mean the underlying business has no risks -- only that nothing in the uploaded materials contradicted itself or matched a known risk pattern."
      />
    );
  }

  return (
    <div className="space-y-4">
      <FindingsSummaryLine
        deterministic={findingsData?.deterministic_count ?? 0}
        documentStated={findingsData?.document_stated_count ?? 0}
        aiInferred={findingsData?.ai_inferred_count ?? 0}
      />

      <div className="space-y-3">
        {findings.map((finding, index) => (
          <Card key={index} className="border-border/50">
            <CardContent className="py-4">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1">
                  <div className="mb-1 flex flex-wrap items-center gap-2">
                    <UnifiedFindingSeverityBadge severity={finding.severity} />
                    <FindingTypeBadge type={finding.type} />
                    <span className="text-xs text-muted-foreground">{finding.category.replace(/_/g, " ")}</span>
                  </div>
                  <h3 className="text-sm font-semibold">{finding.title}</h3>
                  {finding.evidence && (
                    <p className="mt-1 text-sm text-muted-foreground">{finding.evidence}</p>
                  )}
                  {finding.explanation && (
                    <p className="mt-1 text-sm text-muted-foreground">{finding.explanation}</p>
                  )}
                  {finding.implication && (
                    <p className="mt-2 text-xs text-muted-foreground">
                      <span className="font-medium">Why it matters: </span>
                      {finding.implication}
                    </p>
                  )}
                  {finding.recommended_next_step && (
                    <p className="mt-2 flex items-start gap-1.5 rounded-md bg-accent/50 p-2 text-xs">
                      <ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                      <span>
                        <span className="font-medium">Ask the founder:</span> {finding.recommended_next_step}
                      </span>
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
