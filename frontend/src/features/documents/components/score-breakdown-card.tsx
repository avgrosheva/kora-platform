import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import type { CategoryBreakdownEntry } from "@/types/api";

const CATEGORY_LABELS: Record<string, string> = {
  financial_score: "Financial",
  growth_score: "Growth",
  risk_score: "Risk (Stability)",
  market_score: "Market",
  team_score: "Team",
};

export function ScoreBreakdownCard({
  breakdown,
  methodologyVersion,
}: {
  breakdown: Record<string, CategoryBreakdownEntry>;
  methodologyVersion: string | null;
}) {
  const entries = Object.entries(breakdown);

  return (
    <Card className="border-border/50">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-sm font-medium">Score Breakdown</CardTitle>
        {methodologyVersion && (
          <span className="text-[10px] text-muted-foreground">v{methodologyVersion.replace("kora_score_", "")}</span>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        {entries.map(([key, entry]) => (
          <div key={key}>
            <div className="mb-1 flex items-center justify-between text-xs">
              <span className="text-muted-foreground">{CATEGORY_LABELS[key] ?? key}</span>
              <div className="flex items-center gap-2">
                {entry.status === "not_assessable" ? (
                  <Badge variant="outline" className="text-[10px]">Not assessable</Badge>
                ) : (
                  <>
                    <span className="text-muted-foreground">
                      weight {(entry.weight * 100).toFixed(0)}%
                    </span>
                    <span className="font-medium">
                      {entry.score !== null ? entry.score.toFixed(0) : "—"}
                    </span>
                  </>
                )}
              </div>
            </div>
            <Progress value={entry.score ?? 0} className="h-1.5" />
            {entry.contribution !== null && (
              <p className="mt-0.5 text-[10px] text-muted-foreground">
                Contributes {entry.contribution.toFixed(1)} pts to overall score
              </p>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}