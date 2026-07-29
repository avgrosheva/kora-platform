"use client";

import { toast } from "sonner";
import { format } from "date-fns";
import { AlertTriangle, PlayCircle } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { DocumentStatusBadge } from "@/components/shared/document-status-badge";
import { useProcessDocument } from "../hooks";
import type { DocumentRead } from "@/types/api";

export function OverviewTab({ document }: { document: DocumentRead }) {
  const processDocument = useProcessDocument(document.id);

  const handleProcess = () => {
    processDocument.mutate(undefined, {
      onSuccess: (updated) => {
        if (updated.status === "failed") {
          toast.error(updated.processing_error || "Processing failed.");
        } else {
          toast.success("Document processed.");
        }
      },
      onError: (error) => toast.error(error.message),
    });
  };

  return (
    <div className="space-y-4">
      <Card className="border-border/50">
        <CardContent className="grid gap-4 py-6 sm:grid-cols-2">
          <div>
            <p className="text-xs text-muted-foreground">Status</p>
            <div className="mt-1">
              <DocumentStatusBadge status={document.status} />
            </div>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Content type</p>
            <p className="mt-1 text-sm">{document.content_type}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Size</p>
            <p className="mt-1 text-sm">{(document.size_bytes / 1024).toFixed(0)} KB</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Pages</p>
            <p className="mt-1 text-sm">{document.page_count ?? "—"}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Uploaded</p>
            <p className="mt-1 text-sm">{format(new Date(document.created_at), "PPp")}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Processed</p>
            <p className="mt-1 text-sm">
              {document.processed_at ? format(new Date(document.processed_at), "PPp") : "—"}
            </p>
          </div>
        </CardContent>
      </Card>

      {document.status === "failed" && document.processing_error && (
        <div className="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          {document.processing_error}
        </div>
      )}

      {document.status === "uploaded" && (
        <button
          type="button"
          onClick={handleProcess}
          disabled={processDocument.isPending}
          className="flex h-9 items-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground shadow-sm hover:bg-primary/90 disabled:opacity-50"
        >
          <PlayCircle className="h-4 w-4" />
          {processDocument.isPending ? "Processing…" : "Process Document"}
        </button>
      )}
    </div>
  );
}