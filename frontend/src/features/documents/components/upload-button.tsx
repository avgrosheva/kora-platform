"use client";

import { useRef } from "react";
import { Upload } from "lucide-react";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import { Progress } from "@/components/ui/progress";
import { PrimaryButton, Meter } from "@/components/kora/primitives";
import { useUploadDocument } from "../hooks";

const ACCEPTED_TYPES = ".pdf,.docx,.txt";

/**
 * `variant="kora"` renders the trigger with the new design system's
 * `PrimaryButton` (for screens already on the redesign); the default
 * `"shadcn"` keeps the original button for screens not yet migrated.
 * Upload logic (file picking, progress, redirect) is identical either
 * way -- only the trigger's visual chrome differs.
 */
export function UploadButton({ organizationId, variant = "shadcn" }: {
  organizationId: string;
  variant?: "shadcn" | "kora";
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const { upload, isUploading, progress } = useUploadDocument(organizationId);
  const router = useRouter();

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

  const input = (
    <input
      ref={inputRef}
      type="file"
      accept={ACCEPTED_TYPES}
      className="hidden"
      onChange={handleFileChange}
    />
  );

  if (variant === "kora") {
    return (
      <div className="flex items-center gap-3">
        {isUploading && (
          <div className="flex w-40 flex-col gap-1">
            <Meter percent={progress} tone="accent" />
            <span className="font-mono text-[10px] text-fg-dim">{progress}%</span>
          </div>
        )}
        <PrimaryButton onClick={() => inputRef.current?.click()} className={isUploading ? "pointer-events-none opacity-50" : ""}>
          {isUploading ? "UPLOADING…" : "↑ UPLOAD DOCUMENT"}
        </PrimaryButton>
        {input}
      </div>
    );
  }

  return (
    <div className="flex items-center gap-3">
      {isUploading && (
        <div className="flex w-40 items-center gap-2">
          <Progress value={progress} className="h-2" />
          <span className="text-xs text-muted-foreground">{progress}%</span>
        </div>
      )}
      <button
        type="button"
        disabled={isUploading}
        onClick={() => inputRef.current?.click()}
        className="flex h-9 items-center gap-2 rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary/90 disabled:opacity-50"
      >
        <Upload className="h-4 w-4" />
        {isUploading ? "Uploading…" : "Upload Document"}
      </button>
      {input}
    </div>
  );
}
