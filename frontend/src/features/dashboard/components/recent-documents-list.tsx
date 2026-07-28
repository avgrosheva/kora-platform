import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/shared/empty-state";
import { FileText } from "lucide-react";
import { format } from "date-fns";
import type { DashboardResponse, DocumentStatus } from "@/types/api";

const STATUS_VARIANTS: Record<DocumentStatus, "default" | "secondary" | "destructive" | "outline"> = {
  uploaded: "outline",
  processing: "secondary",
  completed: "default",
  failed: "destructive",
};

export function RecentDocumentsList({ documents }: { documents: DashboardResponse["recent_documents"] }) {
  return (
    <Card className="border-border/50">
      <CardHeader>
        <CardTitle className="text-sm font-medium">Recent Documents</CardTitle>
      </CardHeader>
      <CardContent>
        {documents.length === 0 ? (
          <EmptyState icon={FileText} title="No documents yet" description="Upload a document to get started." />
        ) : (
          <ul className="divide-y divide-border/50">
            {documents.map((doc) => (
              <li key={doc.id} className="flex items-center justify-between py-3">
                <Link
                  href={`/documents/${doc.id}`}
                  className="truncate text-sm font-medium hover:text-primary"
                >
                  {doc.filename}
                </Link>
                <div className="flex shrink-0 items-center gap-3">
                  <span className="text-xs text-muted-foreground">
                    {format(new Date(doc.created_at), "MMM d, yyyy")}
                  </span>
                  <Badge variant={STATUS_VARIANTS[doc.status]}>{doc.status}</Badge>
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}