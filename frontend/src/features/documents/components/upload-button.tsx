"use client";

import { useRef } from "react";
import { Upload } from "lucide-react";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import { Progress } from "@/components/ui/progress";
import { useUploadDocument } from "../hooks";

const ACCEPTED_TYPES = ".pdf,.docx,.txt";

export function UploadButton({ organizationId }: { organizationId: string }) {
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
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_TYPES}
        className="hidden"
        onChange={handleFileChange}
      />
    </div>
  );
}