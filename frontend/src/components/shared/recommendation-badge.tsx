import { TrendingUp, Search, HelpCircle, AlertOctagon } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { RecommendationStatus } from "@/types/api";

const CONFIG: Record<
  RecommendationStatus,
  {
    label: string;
    variant: "default" | "secondary" | "outline" | "destructive";
    icon: typeof TrendingUp;
  }
> = {
  strong_candidate: {
    label: "Strong Candidate",
    variant: "default",
    icon: TrendingUp,
  },
  worth_exploring: {
    label: "Worth Exploring",
    variant: "secondary",
    icon: Search,
  },
  needs_more_info: {
    label: "Needs More Info",
    variant: "outline",
    icon: HelpCircle,
  },
  concerns_identified: {
    label: "Concerns Identified",
    variant: "destructive",
    icon: AlertOctagon,
  },
};

export function RecommendationBadge({
  status,
}: {
  status: RecommendationStatus;
}) {
  const { label, variant, icon: Icon } = CONFIG[status];

  return (
    <Badge variant={variant} className="gap-1.5 px-3 py-1 text-sm">
      <Icon className="h-3.5 w-3.5" />
      {label}
    </Badge>
  );
}