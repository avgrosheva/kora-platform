"use client";

import { toast } from "sonner";
import { FileSearch, Download, FileType } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/shared/empty-state";
import { documentsApi } from "../api";
import { useGenerateDueDiligence } from "../hooks";
import type { DocumentRead } from "@/types/api";

export function DueDiligenceTab({ document }: { document: DocumentRead }) {
  const generateReport = useGenerateDueDiligence(document.id);

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
          description="Click Generate Report for a full AI-written investment report, grounded in this document's existing data and content."
        />
      ) : (
        <div className="space-y-4">
          {generateReport.data.sections.map((section) => (
            <Card key={section.title} className="border-border/50">
              <CardContent className="py-4">
                <h3 className="mb-2 text-sm font-semibold">{section.title}</h3>
                <p className="whitespace-pre-line text-sm leading-relaxed text-muted-foreground">
                  {section.content}
                </p>
              </CardContent>
            </Card>
          ))}

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