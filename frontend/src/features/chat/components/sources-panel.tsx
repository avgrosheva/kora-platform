import { FileText } from "lucide-react";
import Link from "next/link";
import { ScrollArea } from "@/components/ui/scroll-area";
import { EmptyState } from "@/components/shared/empty-state";
import type { ChatSource } from "@/types/api";

export function SourcesPanel({ sources }: { sources: ChatSource[] }) {
  return (
    <div className="flex h-full flex-col border-l border-border/50 pl-4">
      <h2 className="mb-3 text-sm font-semibold">Sources</h2>
      <ScrollArea className="flex-1">
        {sources.length === 0 ? (
          <EmptyState icon={FileText} title="No sources yet" description="Ask a question to see supporting excerpts." />
        ) : (
          <div className="space-y-3 pr-2">
            {sources.map((source, i) => (
              <div key={`${source.document_id}-${source.chunk_index}`} className="rounded-md border border-border/50 p-3">
                <div className="mb-1.5 flex items-center justify-between">
                  <Link
                    href={`/documents/${source.document_id}`}
                    className="text-xs font-medium text-primary hover:underline"
                  >
                    Excerpt {i + 1}
                  </Link>
                  <span className="text-xs text-muted-foreground">
                    {(source.similarity_score * 100).toFixed(0)}% match
                  </span>
                </div>
                <p className="line-clamp-4 text-xs text-muted-foreground">{source.snippet}</p>
              </div>
            ))}
          </div>
        )}
      </ScrollArea>
    </div>
  );
}