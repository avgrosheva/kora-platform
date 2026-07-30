import { AlertTriangle, TrendingDown, Clock, ShieldCheck } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import type { PortfolioResponse } from "@/types/api";

interface RiskCardsProps {
  risk: PortfolioResponse["risk"];
}

const RISK_ITEMS = [
  { key: "companies_at_risk" as const, label: "At Risk", icon: AlertTriangle, tone: "text-destructive" },
  {
    key: "companies_with_negative_growth" as const,
    label: "Negative Growth",
    icon: TrendingDown,
    tone: "text-destructive",
  },
  { key: "companies_with_low_runway" as const, label: "Low Runway", icon: Clock, tone: "text-amber-500" },
  {
    key: "high_confidence_companies" as const,
    label: "High Confidence",
    icon: ShieldCheck,
    tone: "text-emerald-500",
  },
];

export function RiskCards({ risk }: RiskCardsProps) {
  return (
    <div className="grid gap-4 md:grid-cols-4">
      {RISK_ITEMS.map((item) => (
        <Card key={item.key} className="border-border/50">
          <CardContent className="flex items-center gap-3 py-5">
            <item.icon className={`h-5 w-5 shrink-0 ${item.tone}`} />
            <div>
              <p className="text-2xl font-semibold tracking-tight">{risk[item.key]}</p>
              <p className="text-xs text-muted-foreground">{item.label}</p>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}