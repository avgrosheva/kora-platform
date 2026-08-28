"use client";

import { useRef } from "react";
import { useRouter } from "next/navigation";
import { format } from "date-fns";
import { formatFileSize } from "@/lib/utils";
import { toast } from "sonner";
import { useActiveOrg } from "@/features/organizations/active-org-context";
import { useDocuments, useUploadDocument } from "@/features/documents/hooks";
import { Documents } from "@/components/kora/screens/Documents";
import { Meter } from "@/components/kora/primitives";
import { NoActiveOrg } from "@/features/organizations/components/no-active-org";
import type { DocumentSummary } from "@/components/kora/types";
import type { DocumentRead } from "@/types/api";

const ACCEPTED_TYPES = ".pdf,.docx,.txt";

function toDocumentSummary(doc: DocumentRead): DocumentSummary {
  return {
    id: doc.id,
    filename: doc.original_filename,
    status: doc.status,
    sizeLabel: formatFileSize(doc.size_bytes),
    uploadedAt: format(new Date(doc.created_at), "MMM d, yyyy HH:mm"),
    contentType: doc.content_type,
    pages: doc.page_count,
    processedAt: doc.processed_at,
  };
}

export default function DocumentsPage() {
  const router = useRouter();
  const { activeOrg, isLoading: orgsLoading } = useActiveOrg();
  const { data, isLoading } = useDocuments(activeOrg?.id ?? null);
  const { upload, isUploading, progress } = useUploadDocument(activeOrg?.id ?? "");
  const inputRef = useRef<HTMLInputElement>(null);

  if (orgsLoading) {
    return <div className="relative z-10 p-9 text-sm text-fg-dim">Loading…</div>;
  }

  if (!activeOrg) {
    return <NoActiveOrg />;
  }

  if (isLoading) {
    return <div className="relative z-10 p-9 text-sm text-fg-dim">Loading…</div>;
  }

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      const documentId = await upload(file);
      toast.success("Document uploaded.");
      router.push(`/documents/${documentId}`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Upload failed.");
    } finally {
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  return (
    <>
      <Documents
        orgName={activeOrg.name}
        documents={(data?.items ?? []).map(toDocumentSummary)}
        onOpenDocument={(id) => router.push(`/documents/${id}`)}
        onUpload={() => inputRef.current?.click()}
      />
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_TYPES}
        className="hidden"
        onChange={handleFileChange}
      />
      {isUploading && (
        <div className="fixed right-[26px] top-[74px] z-30 flex w-52 flex-col gap-2 rounded-[11px] border border-white/10 bg-ink-850/95 px-4 py-3 shadow-glow-accent">
          <span className="font-mono text-[10px] tracking-label text-fg-dim">UPLOADING…</span>
          <Meter percent={progress} tone="accent" thick />
          <span className="font-mono text-[10px] text-fg-muted">{progress}%</span>
        </div>
      )}
    </>
  );
}
