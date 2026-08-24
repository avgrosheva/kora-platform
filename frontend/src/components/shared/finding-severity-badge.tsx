import { AlertCircle, AlertTriangle, Info } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { FindingSeverity } from "@/types/api";

const CONFIG: Record<FindingSeverity, { label: string; variant: "destructive" | "secondary" | "outline"; icon: typeof AlertCircle }> = {
  critical: { label: "Critical", variant: "destructive", icon: AlertCircle },
  warning: { label: "Warning", variant: "secondary", icon: AlertTriangle },
  info: { label: "Info", variant: "outline", icon: Info },
};

export function FindingSeverityBadge({ severity }: { severity: FindingSeverity }) {
  const { label, variant, icon: Icon } = CONFIG[severity];
  return (
    <Badge variant={variant} className="gap-1">
      <Icon className="h-3 w-3" />
      {label}
    </Badge>
  );
}