import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

interface KpiCardProps {
  label: string;
  value: string;
  icon: LucideIcon;
  trend?: "up" | "down" | "neutral";
  subtext?: string;
}

export function KpiCard({ label, value, icon: Icon, trend, subtext }: KpiCardProps) {
  return (
    <Card className="border-border/50">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{label}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-semibold tracking-tight">{value}</div>
        {subtext && (
          <p
            className={cn(
              "mt-1 text-xs",
              trend === "up" && "text-emerald-500",
              trend === "down" && "text-destructive",
              (!trend || trend === "neutral") && "text-muted-foreground"
            )}
          >
            {subtext}
          </p>
        )}
      </CardContent>
    </Card>
  );
}