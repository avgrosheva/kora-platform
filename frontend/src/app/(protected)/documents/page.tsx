"use client";

import Link from "next/link";
import { FileText } from "lucide-react";
import { format } from "date-fns";
import { useActiveOrg } from "@/features/organizations/active-org-context";
import { useDocuments } from "@/features/documents/hooks";
import { UploadButton } from "@/features/documents/components/upload-button";
import { DocumentStatusBadge } from "@/components/shared/document-status-badge";
import { EmptyState } from "@/components/shared/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export default function DocumentsPage() {
  const { activeOrg } = useActiveOrg();
  const { data, isLoading } = useDocuments(activeOrg?.id ?? null);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Documents</h1>
          <p className="text-sm text-muted-foreground">{activeOrg?.name}</p>
        </div>
        {activeOrg && <UploadButton organizationId={activeOrg.id} />}
      </div>

      {isLoading ? (
        <Skeleton className="h-96" />
      ) : !data || data.items.length === 0 ? (
        <EmptyState
          icon={FileText}
          title="No documents yet"
          description="Upload a PDF, DOCX, or TXT file to begin analysis."
        />
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Filename</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Size</TableHead>
              <TableHead>Uploaded</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.items.map((doc) => (
              <TableRow key={doc.id} className="cursor-pointer">
                <TableCell>
                  <Link href={`/documents/${doc.id}`} className="hover:text-primary">
                    {doc.original_filename}
                  </Link>
                </TableCell>
                <TableCell>
                  <DocumentStatusBadge status={doc.status} />
                </TableCell>
                <TableCell className="text-xs text-muted-foreground">
                  {(doc.size_bytes / 1024).toFixed(0)} KB
                </TableCell>
                <TableCell className="text-xs text-muted-foreground">
                  {format(new Date(doc.created_at), "MMM d, yyyy HH:mm")}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}