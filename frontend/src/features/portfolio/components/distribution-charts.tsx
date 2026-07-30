"use client";

import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { PortfolioResponse } from "@/types/api";

const COLORS = ["hsl(217 91% 60%)", "hsl(160 84% 39%)", "hsl(38 92% 50%)", "hsl(0 72% 51%)", "hsl(280 65% 60%)"];

function bucketsToChartData(buckets: Record<string, number>) {
  return Object.entries(buckets)
    .filter(([, count]) => count > 0)
    .map(([name, value]) => ({ name, value }));
}

function DistributionPie({ title, data }: { title: string; data: { name: string; value: number }[] }) {
  return (
    <Card className="border-border/50">
      <CardHeader>
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
      </CardHeader>
      <CardContent className="h-64">
        {data.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
            No data available.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={data} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={70}>
                {data.map((entry, index) => (
                  <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  background: "hsl(222 18% 11%)",
                  border: "1px solid hsl(217 19% 20%)",
                  borderRadius: 8,
                }}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
            </PieChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}

export function DistributionCharts({ distribution }: { distribution: PortfolioResponse["distribution"] }) {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      <DistributionPie title="Score Distribution" data={bucketsToChartData(distribution.score_buckets)} />
      <DistributionPie title="Valuation Distribution" data={bucketsToChartData(distribution.valuation_buckets)} />
      <DistributionPie title="Industry Distribution" data={bucketsToChartData(distribution.industry_distribution)} />
    </div>
  );
}