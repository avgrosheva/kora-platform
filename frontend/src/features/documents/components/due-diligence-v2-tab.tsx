"use client";

import { toast } from "sonner";
import { FileSearch, Download, FileType, HelpCircle } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/shared/empty-state";
import { RecommendationBadge } from "@/components/shared/recommendation-badge";
import { Badge } from "@/components/ui/badge";
import { documentsApi } from "../api";
import { useGenerateDueDiligenceV2 } from "../hooks";
import type { DocumentRead } from "@/types/api";

export function DueDiligenceV2Tab({ document }: { document: DocumentRead }) {
  const generateReport = useGenerateDueDiligenceV2(document.id);

  const handleGenerate = () => {
    generateReport.mutate(undefined, {
      onSuccess: () => toast.success("Due diligence report generated."),
      onError: (error) => toast.error(error.message),
    });
  };

  const handleExport = async (format: "md" | "pdf") => {
    try {
      if (format === "md") {
        await documentsApi.exportMarkdown(document.id, `due-diligence-${document.original_filename}.md`);
      } else {
        await documentsApi.exportPdf(document.id, `due-diligence-${document.original_filename}.pdf`);
      }
      toast.success(`Exported as ${format.toUpperCase()}.`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Export failed.");
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <button
          type="button"
          onClick={handleGenerate}
          disabled={generateReport.isPending}
          className="flex h-9 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground shadow-sm hover:bg-primary/90 disabled:opacity-50"
        >
          <FileSearch className="h-4 w-4" />
          {generateReport.isPending ? "Generating…" : "Generate Report"}
        </button>

        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => handleExport("md")}
            className="flex h-9 items-center gap-2 rounded-md border border-input px-3 text-sm font-medium hover:bg-accent"
          >
            <Download className="h-4 w-4" />
            Export Markdown
          </button>
          <button
            type="button"
            onClick={() => handleExport("pdf")}
            className="flex h-9 items-center gap-2 rounded-md border border-input px-3 text-sm font-medium hover:bg-accent"
          >
            <FileType className="h-4 w-4" />
            Export PDF
          </button>
        </div>
      </div>

      {!generateReport.data ? (
        <EmptyState
          icon={FileSearch}
          title="No report generated in this session"
          description="Generates the evidence-grounded report: verified facts, red flags from deterministic checks, and founder questions — on top of the AI-written narrative."
        />
      ) : (
        <div className="space-y-4">
          {/* Executive header: recommendation + verified facts */}
          <Card className="border-border/50">
            <CardContent className="space-y-4 py-5">
              <div className="flex items-center justify-between">
                <h2 className="text-base font-semibold">Executive Summary</h2>
                <RecommendationBadge status={generateReport.data.recommendation_status} />
              </div>
              <p className="text-sm leading-relaxed text-muted-foreground">
                {generateReport.data.executive_summary}
              </p>

              {generateReport.data.verified_facts.length > 0 && (
                <div className="grid gap-3 border-t border-border/50 pt-4 sm:grid-cols-3 md:grid-cols-4">
                  {generateReport.data.verified_facts.map((fact) => (
                    <div key={fact.label}>
                      <p className="text-xs text-muted-foreground">{fact.label}</p>
                      <p className="text-lg font-semibold">{fact.value_display}</p>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Red flags */}
          {generateReport.data.red_flags.length > 0 && (
            <Card className="border-destructive/30">
              <CardContent className="space-y-3 py-4">
                <h3 className="text-sm font-semibold text-destructive">
                  Red Flags ({generateReport.data.red_flags.length})
                </h3>
                {generateReport.data.red_flags.map((flag) => (
                  <div key={flag.id} className="rounded-md border border-border/50 p-3">
                    <div className="flex items-center gap-2">
                      <Badge variant={flag.severity === "critical" ? "destructive" : "secondary"} className="text-[10px]">
                        {flag.severity}
                      </Badge>
                      <p className="text-sm font-medium">{flag.title}</p>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">{flag.description}</p>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Founder questions */}
          {generateReport.data.founder_questions.length > 0 && (
            <Card className="border-border/50">
              <CardContent className="space-y-2 py-4">
                <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold">
                  <HelpCircle className="h-4 w-4 text-muted-foreground" />
                  Questions for the Founders
                </h3>
                <ul className="space-y-2">
                  {generateReport.data.founder_questions.map((q, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm">
                      <Badge variant={q.priority === "high" ? "destructive" : "outline"} className="mt-0.5 shrink-0 text-[10px]">
                        {q.priority}
                      </Badge>
                      <span>{q.question}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {/* Full narrative sections (collapsed-by-default feel via smaller text, still all visible) */}
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-muted-foreground">Full Report</h3>
            {generateReport.data.sections.map((section) => (
              <Card key={section.title} className="border-border/50">
                <CardContent className="py-4">
                  <h4 className="mb-2 text-sm font-semibold">{section.title}</h4>
                  <p className="whitespace-pre-line text-sm leading-relaxed text-muted-foreground">
                    {section.content}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>

          {generateReport.data.sources.length > 0 && (
            <Card className="border-border/50">
              <CardContent className="py-4">
                <h3 className="mb-2 text-sm font-semibold">Sources</h3>
                <ul className="space-y-2">
                  {generateReport.data.sources.map((source, i) => (
                    <li key={`${source.document_id}-${source.chunk_index}`} className="text-xs text-muted-foreground">
                      <span className="font-medium text-foreground">
                        [{i + 1}] similarity {source.similarity_score.toFixed(2)}:
                      </span>{" "}
                      {source.snippet}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}