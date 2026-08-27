"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { format } from "date-fns";
import { useActiveOrg } from "@/features/organizations/active-org-context";
import { usePortfolio } from "@/features/portfolio/hooks";
import { useDocuments } from "@/features/documents/hooks";
import { UploadButton } from "@/features/documents/components/upload-button";
import { CreateOrgDialog } from "@/features/organizations/components/create-org-dialog";
import { Portfolio, NoOrganizations } from "@/components/kora/screens/Portfolio";
import { EmptyState } from "@/components/kora/primitives";
import { formatCurrency } from "@/lib/utils";
import type { PortfolioMetrics, PortfolioRow, HealthBucket } from "@/components/kora/screens/Portfolio";
import type { PortfolioDocumentRow, PortfolioResponse } from "@/types/api";

function toPortfolioRow(doc: PortfolioDocumentRow): PortfolioRow {
  return {
    id: doc.document_id,
    filename: doc.filename,
    companyName: doc.company_name ?? undefined,
    status: doc.status,
    sizeLabel: `${(doc.size_bytes / 1024).toFixed(0)} KB`,
    uploadedAt: format(new Date(doc.created_at), "MMM d, yyyy HH:mm"),
    score: doc.overall_score,
    coverage: doc.coverage_percent,
    openFindings: (Object.entries(doc.open_findings) as ["high" | "medium" | "low", number][]).map(
      ([severity, count]) => ({ severity, count })
    ),
  };
}

function toMetrics(portfolio: PortfolioResponse, documentsTotal: number): PortfolioMetrics {
  return {
    documentsAnalyzed: portfolio.summary.company_count,
    documentsTotal,
    averageRevenue: portfolio.summary.average_arr !== null ? formatCurrency(portfolio.summary.average_arr) : null,
    averageScore: portfolio.summary.average_investment_score !== null
      ? Math.round(portfolio.summary.average_investment_score)
      : null,
    averageCoverage: portfolio.summary.average_coverage !== null ? Math.round(portfolio.summary.average_coverage) : null,
  };
}

function toHealth(portfolio: PortfolioResponse): HealthBucket[] {
  return [
    { label: "At Risk", count: portfolio.risk.companies_at_risk },
    { label: "Negative Growth", count: portfolio.risk.companies_with_negative_growth },
    { label: "Low Runway", count: portfolio.risk.companies_with_low_runway },
    { label: "High Confidence", count: portfolio.risk.high_confidence_companies },
  ];
}

export default function PortfolioPage() {
  const router = useRouter();
  const { activeOrg, organizations, isLoading: orgsLoading } = useActiveOrg();
  const { data: portfolio, isLoading } = usePortfolio(activeOrg?.id ?? null);
  const { data: documents } = useDocuments(activeOrg?.id ?? null);
  const [createOpen, setCreateOpen] = useState(false);

  if (orgsLoading) {
    return <div className="relative z-10 p-9 text-sm text-fg-dim">Loading…</div>;
  }

  if (organizations.length === 0) {
    return (
      <>
        <div className="relative z-10">
          <NoOrganizations onCreate={() => setCreateOpen(true)} />
        </div>
        <CreateOrgDialog open={createOpen} onOpenChange={setCreateOpen} />
      </>
    );
  }

  if (!activeOrg || (isLoading && !portfolio)) {
    return <div className="relative z-10 p-9 text-sm text-fg-dim">Loading…</div>;
  }

  if (!portfolio) {
    return (
      <div className="relative z-10 max-w-[1360px] px-9 pb-24 pt-10">
        <EmptyState title="Couldn't load portfolio" blurb="Please try again shortly." />
      </div>
    );
  }

  if (portfolio.summary.company_count === 0) {
    return (
      <div className="relative z-10 max-w-[1360px] px-9 pb-24 pt-10">
        <EmptyState
          title="No companies analyzed yet"
          blurb="Kora turns uploaded documents into structured, evidence-backed due-diligence profiles. Upload one to see it here."
          action={<UploadButton organizationId={activeOrg.id} variant="kora" />}
        />
      </div>
    );
  }

  return (
    <Portfolio
      orgName={activeOrg.name}
      metrics={toMetrics(portfolio, documents?.items.length ?? portfolio.summary.company_count)}
      rows={portfolio.documents.map(toPortfolioRow)}
      health={toHealth(portfolio)}
      topScored={portfolio.overview.top_10_companies
        .filter((c) => c.overall_score !== null)
        .map((c) => ({ id: c.document_id, name: c.company_name ?? "Unnamed", score: c.overall_score as number }))}
      onOpenDocument={(id) => router.push(`/documents/${id}`)}
    />
  );
}
