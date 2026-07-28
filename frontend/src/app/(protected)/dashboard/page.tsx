"use client";

import { DollarSign, TrendingUp, Building2, FileCheck } from "lucide-react";
import { useActiveOrg } from "@/features/organizations/active-org-context";
import { useDashboard } from "@/features/dashboard/hooks";
import { KpiCard } from "@/components/shared/kpi-card";
import { DashboardCharts } from "@/features/dashboard/components/dashboard-charts";
import { RecentDocumentsList } from "@/features/dashboard/components/recent-documents-list";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { formatCurrency, formatPercent, formatNumber } from "@/lib/utils";

export default function DashboardPage() {
  const { activeOrg, isLoading: orgsLoading } = useActiveOrg();
  const { data, isLoading, isError } = useDashboard(activeOrg?.id ?? null);

  if (orgsLoading || (activeOrg && isLoading)) {
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

  if (!activeOrg) {
    return (
      <EmptyState
        icon={Building2}
        title="No organization selected"
        description="Create or join an organization to see your dashboard."
      />
    );
  }

  if (isError || !data) {
    return (
      <EmptyState icon={Building2} title="Couldn't load dashboard" description="Please try again shortly." />
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="text-sm text-muted-foreground">{activeOrg.name}</p>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <KpiCard
          label="Companies Analyzed"
          value={`${data.companies_analyzed} / ${data.total_documents}`}
          icon={FileCheck}
        />
        <KpiCard
          label="Average ARR"
          value={formatCurrency(data.average_arr)}
          icon={DollarSign}
        />
        <KpiCard
          label="Average Investment Score"
          value={data.average_investment_score !== null ? formatNumber(data.average_investment_score) : "—"}
          icon={TrendingUp}
        />
        <KpiCard
          label="Average Growth Rate"
          value={formatPercent(data.average_growth_rate)}
          icon={TrendingUp}
        />
      </div>

      <DashboardCharts data={data} />

      <RecentDocumentsList documents={data.recent_documents} />
    </div>
  );
}