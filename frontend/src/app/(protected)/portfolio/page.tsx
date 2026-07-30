"use client";

import { useActiveOrg } from "@/features/organizations/active-org-context";
import { usePortfolio } from "@/features/portfolio/hooks";
import { PortfolioSummaryCards } from "@/features/portfolio/components/portfolio-summary-cards";
import { RiskCards } from "@/features/portfolio/components/risk-cards";
import { CompanyRankingTable } from "@/features/portfolio/components/company-ranking-table";
import { DistributionCharts } from "@/features/portfolio/components/distribution-charts";
import { EmptyState } from "@/components/shared/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { PieChart } from "lucide-react";
import { formatCurrency, formatNumber, formatPercent } from "@/lib/utils";

export default function PortfolioPage() {
  const { activeOrg } = useActiveOrg();
  const { data, isLoading, isError } = usePortfolio(activeOrg?.id ?? null);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="grid gap-4 md:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
        <Skeleton className="h-64" />
      </div>
    );
  }

  if (!activeOrg || isError || !data) {
    return (
      <EmptyState
        icon={PieChart}
        title="Portfolio unavailable"
        description="Select an organization with analyzed documents to see portfolio analytics."
      />
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Portfolio</h1>
        <p className="text-sm text-muted-foreground">{activeOrg.name}</p>
      </div>

      <PortfolioSummaryCards summary={data.summary} />
      <RiskCards risk={data.risk} />
      <DistributionCharts distribution={data.distribution} />

      <div className="grid gap-4 lg:grid-cols-2">
        <CompanyRankingTable
          title="Top 10 Companies"
          companies={data.overview.top_10_companies}
          metric="overall_score"
          metricLabel="Score"
          formatValue={(c) => (c.overall_score !== null ? c.overall_score.toFixed(1) : "—")}
        />
        <CompanyRankingTable
          title="Worst 10 Companies"
          companies={data.overview.worst_10_companies}
          metric="overall_score"
          metricLabel="Score"
          formatValue={(c) => (c.overall_score !== null ? c.overall_score.toFixed(1) : "—")}
        />
        <CompanyRankingTable
          title="Highest Growth"
          companies={data.overview.highest_growth_companies}
          metric="growth_rate"
          metricLabel="Growth"
          formatValue={(c) => formatPercent(c.growth_rate)}
        />
        <CompanyRankingTable
          title="Highest ARR"
          companies={data.overview.highest_arr_companies}
          metric="arr"
          metricLabel="ARR"
          formatValue={(c) => formatCurrency(c.arr, c.currency ?? "USD")}
        />
        <CompanyRankingTable
          title="Highest Valuation"
          companies={data.overview.highest_valuation_companies}
          metric="valuation"
          metricLabel="Valuation"
          formatValue={(c) => formatCurrency(c.valuation, c.currency ?? "USD")}
        />
        <CompanyRankingTable
          title="Lowest Runway"
          companies={data.overview.lowest_runway_companies}
          metric="runway_months"
          metricLabel="Runway"
          formatValue={(c) => (c.runway_months !== null ? `${c.runway_months} mo` : "—")}
        />
        <CompanyRankingTable
          title="Highest Burn"
          companies={data.overview.highest_burn_companies}
          metric="burn_rate"
          metricLabel="Burn Rate"
          formatValue={(c) => formatCurrency(c.burn_rate, c.currency ?? "USD")}
        />
      </div>
    </div>
  );
}