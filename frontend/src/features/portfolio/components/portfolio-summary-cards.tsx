import { Building2, TrendingUp, DollarSign, Wallet } from "lucide-react";
import { KpiCard } from "@/components/shared/kpi-card";
import { formatCurrency, formatNumber, formatPercent } from "@/lib/utils";
import type { PortfolioResponse } from "@/types/api";

export function PortfolioSummaryCards({ summary }: { summary: PortfolioResponse["summary"] }) {
  return (
    <div className="grid gap-4 md:grid-cols-4">
      <KpiCard label="Companies" value={formatNumber(summary.company_count)} icon={Building2} />
      <KpiCard
        label="Avg. Investment Score"
        value={summary.average_investment_score !== null ? formatNumber(summary.average_investment_score) : "—"}
        icon={TrendingUp}
      />
      <KpiCard label="Avg. ARR" value={formatCurrency(summary.average_arr)} icon={DollarSign} />
      <KpiCard label="Avg. Valuation" value={formatCurrency(summary.average_valuation)} icon={Wallet} />
    </div>
  );
}