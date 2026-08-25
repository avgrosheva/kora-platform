"use client";

import { useParams } from "next/navigation";
import { FileText } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/shared/empty-state";
import { DocumentStatusBadge } from "@/components/shared/document-status-badge";
import { useDocument } from "@/features/documents/hooks";
import { OverviewTab } from "@/features/documents/components/overview-tab";
import { AnalysisTab } from "@/features/documents/components/analysis-tab";
import { FinancialsTab } from "@/features/documents/components/financials-tab";
import { ScoreTab } from "@/features/documents/components/score-tab";
import { DueDiligenceTab } from "@/features/documents/components/due-diligence-tab";

import { ChecksTab } from "@/features/documents/components/checks-tab";
import { CoverageTab } from "@/features/documents/components/coverage-tab";
import { DueDiligenceV2Tab } from "@/features/documents/components/due-diligence-v2-tab";

export default function DocumentDetailPage() {
  const params = useParams<{ id: string }>();
  const { data: document, isLoading, isError } = useDocument(params.id);

  if (isLoading) return <Skeleton className="h-96" />;

  if (isError || !document) {
    return (
      <EmptyState
        icon={FileText}
        title="Document not found"
        description="It may not exist, or you may not have access to it."
      />
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <FileText className="h-5 w-5 text-muted-foreground" />
        <h1 className="truncate text-xl font-semibold tracking-tight">{document.original_filename}</h1>
        <DocumentStatusBadge status={document.status} />
      </div>

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="analysis">Analysis</TabsTrigger>
          <TabsTrigger value="financials">Financials</TabsTrigger>
          <TabsTrigger value="checks">Checks</TabsTrigger>
          <TabsTrigger value="coverage">Coverage</TabsTrigger>
          <TabsTrigger value="score">Score</TabsTrigger>
          <TabsTrigger value="due-diligence">Due Diligence</TabsTrigger>
          <TabsTrigger value="due-diligence-v2">Due Diligence v2</TabsTrigger>
        </TabsList>
        <TabsContent value="overview" className="mt-4">
          <OverviewTab document={document} />
        </TabsContent>
        <TabsContent value="analysis" className="mt-4">
          <AnalysisTab document={document} />
        </TabsContent>
        <TabsContent value="financials" className="mt-4">
          <FinancialsTab document={document} />
        </TabsContent>
        <TabsContent value="score" className="mt-4">
          <ScoreTab document={document} />
        </TabsContent>
        <TabsContent value="due-diligence" className="mt-4">
          <DueDiligenceTab document={document} />
        </TabsContent>
        <TabsContent value="checks" className="mt-4">
          <ChecksTab document={document} />
        </TabsContent>
        <TabsContent value="coverage" className="mt-4">
          <CoverageTab document={document} />
        </TabsContent>
        <TabsContent value="due-diligence-v2" className="mt-4">
          <DueDiligenceV2Tab document={document} />
        </TabsContent>
      </Tabs>
    </div>
  );
}