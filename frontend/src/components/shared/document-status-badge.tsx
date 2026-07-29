import { Badge } from "@/components/ui/badge";
import type { DocumentStatus } from "@/types/api";

const VARIANTS: Record<DocumentStatus, "default" | "secondary" | "destructive" | "outline"> = {
  uploaded: "outline",
  processing: "secondary",
  completed: "default",
  failed: "destructive",
};

export function DocumentStatusBadge({ status }: { status: DocumentStatus }) {
  return <Badge variant={VARIANTS[status]}>{status}</Badge>;
}