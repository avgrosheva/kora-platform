import { AlertCircle, AlertTriangle, ArrowUpCircle, Info, Minus } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { UnifiedFindingSeverity } from "@/types/api";

const CONFIG: Record<
  UnifiedFindingSeverity,
  { label: string; variant: "destructive" | "secondary" | "outline"; icon: typeof AlertCircle }
> = {
  critical: { label: "Critical", variant: "destructive", icon: AlertCircle },
  high: { label: "High", variant: "destructive", icon: ArrowUpCircle },
  medium: { label: "Medium", variant: "secondary", icon: AlertTriangle },
  low: { label: "Low", variant: "outline", icon: Minus },
  informational: { label: "Informational", variant: "outline", icon: Info },
};

export function UnifiedFindingSeverityBadge({ severity }: { severity: UnifiedFindingSeverity }) {
  const { label, variant, icon: Icon } = CONFIG[severity];
  return (
    <Badge variant={variant} className="gap-1">
      <Icon className="h-3 w-3" />
      {label}
    </Badge>
  );
}
