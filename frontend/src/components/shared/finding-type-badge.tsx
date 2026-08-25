import { Calculator, FileText, Sparkles, TrendingUp } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { UnifiedFindingType } from "@/types/api";

/**
 * Visibly distinguishes where a finding came from. This is the second
 * half of the double-labeling requirement for `ai_inferred` findings
 * (the other half is the "(Kora-inferred)" text already baked into
 * such findings' titles by the backend) — a Kora-inferred conclusion
 * must never be visually indistinguishable from a fact the document
 * itself states.
 */
const CONFIG: Record<UnifiedFindingType, { label: string; variant: "outline" | "secondary"; icon: typeof FileText }> = {
  deterministic: { label: "Automated check", variant: "outline", icon: Calculator },
  document_stated: { label: "From document", variant: "outline", icon: FileText },
  derived: { label: "Calculated", variant: "outline", icon: TrendingUp },
  ai_inferred: { label: "Kora-inferred", variant: "secondary", icon: Sparkles },
};

export function FindingTypeBadge({ type }: { type: UnifiedFindingType }) {
  const { label, variant, icon: Icon } = CONFIG[type];
  return (
    <Badge variant={variant} className="gap-1">
      <Icon className="h-3 w-3" />
      {label}
    </Badge>
  );
}
