"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { DashboardResponse } from "@/types/api";

interface DashboardChartsProps {
  data: DashboardResponse;
}

export function DashboardCharts({ data }: DashboardChartsProps) {
  const growthData = [
    { name: "Positive Growth", value: data.portfolio_stats.companies_with_positive_growth },
    { name: "Negative Growth", value: data.portfolio_stats.companies_with_negative_growth },
    { name: "Low Runway", value: data.portfolio_stats.companies_low_runway },
  ];

  const scoreData = data.top_scored_companies.map((c) => ({
    name: c.company_name ?? "Unnamed",
    score: c.overall_score,
  }));

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Card className="border-border/50">
        <CardHeader>
          <CardTitle className="text-sm font-medium">Portfolio Health</CardTitle>
        </CardHeader>
        <CardContent className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={growthData}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(217 19% 20%)" />
              <XAxis dataKey="name" tick={{ fill: "hsl(215 16% 60%)", fontSize: 12 }} />
              <YAxis tick={{ fill: "hsl(215 16% 60%)", fontSize: 12 }} allowDecimals={false} />
              <Tooltip
                contentStyle={{
                  background: "hsl(222 18% 11%)",
                  border: "1px solid hsl(217 19% 20%)",
                  borderRadius: 8,
                }}
              />
              <Bar dataKey="value" fill="hsl(217 91% 60%)" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card className="border-border/50">
        <CardHeader>
          <CardTitle className="text-sm font-medium">Top Scored Companies</CardTitle>
        </CardHeader>
        <CardContent className="h-64">
          {scoreData.length === 0 ? (
            <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
              No scored companies yet.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={scoreData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(217 19% 20%)" />
                <XAxis type="number" domain={[0, 100]} tick={{ fill: "hsl(215 16% 60%)", fontSize: 12 }} />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={100}
                  tick={{ fill: "hsl(215 16% 60%)", fontSize: 12 }}
                />
                <Tooltip
                  contentStyle={{
                    background: "hsl(222 18% 11%)",
                    border: "1px solid hsl(217 19% 20%)",
                    borderRadius: 8,
                  }}
                />
                <Bar dataKey="score" fill="hsl(217 91% 60%)" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>
    </div>
  );
}