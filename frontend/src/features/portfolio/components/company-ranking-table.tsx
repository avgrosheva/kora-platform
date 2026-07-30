import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { EmptyState } from "@/components/shared/empty-state";
import { BarChart3 } from "lucide-react";
import type { PortfolioCompany } from "@/types/api";

interface CompanyRankingTableProps {
  title: string;
  companies: PortfolioCompany[];
  metric: "overall_score" | "growth_rate" | "arr" | "valuation" | "runway_months" | "burn_rate";
  metricLabel: string;
  formatValue: (company: PortfolioCompany) => string;
}

export function CompanyRankingTable({
  title,
  companies,
  metricLabel,
  formatValue,
}: CompanyRankingTableProps) {
  return (
    <Card className="border-border/50">
      <CardHeader>
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {companies.length === 0 ? (
          <EmptyState icon={BarChart3} title="No data available" />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Company</TableHead>
                <TableHead>Industry</TableHead>
                <TableHead className="text-right">{metricLabel}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {companies.map((company) => (
                <TableRow key={company.document_id}>
                  <TableCell>
                    <Link
                      href={`/documents/${company.document_id}`}
                      className="font-medium hover:text-primary"
                    >
                      {company.company_name ?? "Unnamed"}
                    </Link>
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground">
                    {company.industry ?? "—"}
                  </TableCell>
                  <TableCell className="text-right text-sm font-medium">
                    {formatValue(company)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}