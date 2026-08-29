"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { format } from "date-fns";
import { formatFileSize } from "@/lib/utils";
import { toast } from "sonner";
import {
  useDocument, useProcessDocument, useIndexDocument, useAnalysis, useAnalyzeWithCitations,
  useScore, useCalculateScore, useDocumentFindings, useDocumentCoverage, useMissingInformation,
  useFinancialMetrics, useRunFinancialAnalysis, useExtractFinancialFacts,
  useGenerateDueDiligence, useGenerateDueDiligenceV2,
} from "@/features/documents/hooks";
import { documentsApi } from "@/features/documents/api";
import { useChatWidget } from "@/features/chat/chat-widget-context";
import { DocumentDetail } from "@/components/kora/screens/DocumentDetail";
import { OverviewTab } from "@/components/kora/screens/tabs/OverviewTab";
import { AnalysisTab } from "@/components/kora/screens/tabs/AnalysisTab";
import { FinancialsTab } from "@/components/kora/screens/tabs/FinancialsTab";
import { ChecksTab } from "@/components/kora/screens/tabs/ChecksTab";
import { CoverageTab } from "@/components/kora/screens/tabs/CoverageTab";
import { ScoreTab } from "@/components/kora/screens/tabs/ScoreTab";
import { DueDiligenceTab } from "@/components/kora/screens/tabs/DueDiligenceTab";
import { DueDiligenceV2Tab } from "@/components/kora/screens/tabs/DueDiligenceV2Tab";
import { EmptyState, PageLoading } from "@/components/kora/primitives";
import type { DetailTabId, DocumentSummary } from "@/components/kora/types";
import type { DocumentRead } from "@/types/api";

function toDocumentSummary(doc: DocumentRead): DocumentSummary {
  return {
    id: doc.id,
    filename: doc.original_filename,
    status: doc.status,
    sizeLabel: formatFileSize(doc.size_bytes),
    uploadedAt: format(new Date(doc.created_at), "MMM d, yyyy HH:mm"),
    contentType: doc.content_type,
    pages: doc.page_count,
    processedAt: doc.processed_at ? format(new Date(doc.processed_at), "MMM d, yyyy HH:mm") : null,
  };
}

export default function DocumentDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { data: document, isLoading, isError } = useDocument(params.id);
  const [activeTab, setActiveTab] = useState<DetailTabId>("overview");

  const processDocument = useProcessDocument(params.id);
  const indexDocument = useIndexDocument(params.id);

  const { data: analysis } = useAnalysis(params.id);
  const analyzeDocument = useAnalyzeWithCitations(params.id);
  const { data: score } = useScore(params.id);
  const calculateScore = useCalculateScore(params.id);
  const { data: findingsData } = useDocumentFindings(params.id);
  const { data: coverage } = useDocumentCoverage(params.id);
  const { data: missingInfo } = useMissingInformation(params.id);

  const { data: financialMetrics } = useFinancialMetrics(params.id);
  const runFinancialAnalysis = useRunFinancialAnalysis(params.id);
  const extractFacts = useExtractFinancialFacts(params.id);

  const generateDueDiligence = useGenerateDueDiligence(params.id);
  const generateDueDiligenceV2 = useGenerateDueDiligenceV2(params.id);

  const { setOpen: setChatOpen } = useChatWidget();

  if (isLoading) {
    return <PageLoading />;
  }

  if (isError || !document) {
    return (
      <div className="relative z-10 max-w-[1360px] px-9 pb-24 pt-10">
        <EmptyState
          title="Document not found"
          blurb="It may not exist, or you may not have access to it."
        />
      </div>
    );
  }

  const handleProcess = () => {
    processDocument.mutate(undefined, {
      onSuccess: (updated) => {
        if (updated.status === "failed") {
          toast.error(updated.processing_error || "Processing failed.");
        } else {
          toast.success("Document processed.");
        }
      },
      onError: (error) => toast.error(error.message),
    });
  };

  const handleIndex = () => {
    indexDocument.mutate(undefined, {
      onSuccess: (result) =>
        toast.success(`${result.chunks_indexed} chunk${result.chunks_indexed === 1 ? "" : "s"} indexed for chat.`),
      onError: (error) => toast.error(error.message),
    });
  };

  const handleAnalyze = () => {
    analyzeDocument.mutate(undefined, {
      onSuccess: () => toast.success("Analysis complete."),
      onError: (error) => toast.error(error.message),
    });
  };

  const handleRunFinancials = () => {
    runFinancialAnalysis.mutate(undefined, {
      onSuccess: () => toast.success("Financial metrics extracted."),
      onError: (error) => toast.error(error.message),
    });
  };

  const handleExtractFacts = () => {
    extractFacts.mutate(undefined, {
      onSuccess: (result) =>
        toast.success(`${result.facts_extracted} cited financial fact${result.facts_extracted === 1 ? "" : "s"} extracted.`),
      onError: (error) => toast.error(error.message),
    });
  };

  const handleCalculateScore = () => {
    calculateScore.mutate(undefined, {
      onSuccess: () => toast.success("Investment score calculated."),
      onError: (error) => toast.error(error.message),
    });
  };

  const handleGenerateDueDiligence = () => {
    generateDueDiligence.mutate(undefined, {
      onSuccess: () => toast.success("Due diligence report generated."),
      onError: (error) => toast.error(error.message),
    });
  };

  const handleGenerateDueDiligenceV2 = () => {
    generateDueDiligenceV2.mutate(undefined, {
      onSuccess: () => toast.success("Due diligence report generated."),
      onError: (error) => toast.error(error.message),
    });
  };

  // Exports render the report already generated and on screen -- each
  // needs that exact report object, so v1 and v2 each get their own
  // handler rather than sharing one keyed only by file format.
  const handleExport = async (format: "md" | "pdf") => {
    const report = generateDueDiligence.data;
    if (!report) return;
    try {
      if (format === "md") {
        await documentsApi.exportMarkdown(document.id, report, `due-diligence-${document.original_filename}.md`);
      } else {
        await documentsApi.exportPdf(document.id, report, `due-diligence-${document.original_filename}.pdf`);
      }
      toast.success(`Exported as ${format.toUpperCase()}.`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Export failed.");
    }
  };

  const handleExportV2 = async (format: "md" | "pdf") => {
    const report = generateDueDiligenceV2.data;
    if (!report) return;
    try {
      if (format === "md") {
        await documentsApi.exportMarkdownV2(document.id, report, `due-diligence-${document.original_filename}.md`);
      } else {
        await documentsApi.exportPdfV2(document.id, report, `due-diligence-${document.original_filename}.pdf`);
      }
      toast.success(`Exported as ${format.toUpperCase()}.`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Export failed.");
    }
  };

  const findings = findingsData?.findings ?? [];

  return (
    <DocumentDetail
      document={toDocumentSummary(document)}
      activeTab={activeTab}
      onSelectTab={setActiveTab}
      onBack={() => router.push("/documents")}
    >
      {activeTab === "overview" && (
        <OverviewTab
          document={toDocumentSummary(document)}
          processingError={document.status === "failed" ? document.processing_error : null}
          onProcess={handleProcess}
          isProcessing={processDocument.isPending}
          onIndex={handleIndex}
          isIndexing={indexDocument.isPending}
        />
      )}

      {activeTab === "analysis" && (
        <AnalysisTab
          status={document.status}
          analysis={analysis ?? null}
          score={score ?? null}
          findings={findings}
          totalConcerns={findings.length}
          coverage={coverage ?? null}
          isAnalyzing={analyzeDocument.isPending}
          onRerun={handleAnalyze}
          onAskKora={() => setChatOpen(true)}
          onViewAllFindings={() => setActiveTab("checks")}
        />
      )}

      {activeTab === "financials" && (
        <FinancialsTab
          metrics={financialMetrics ?? null}
          canRun={!!analysis}
          canExtractFacts={document.status === "completed"}
          isRunning={runFinancialAnalysis.isPending}
          isExtractingFacts={extractFacts.isPending}
          onRun={handleRunFinancials}
          onExtractFacts={handleExtractFacts}
        />
      )}

      {activeTab === "checks" && (
        <ChecksTab
          findings={findings}
          deterministicCount={findingsData?.deterministic_count ?? 0}
          documentStatedCount={findingsData?.document_stated_count ?? 0}
          aiInferredCount={findingsData?.ai_inferred_count ?? 0}
          hasFinancialEvidence={(coverage?.coverage.financial?.found ?? 0) > 0}
        />
      )}

      {activeTab === "coverage" && (
        coverage ? (
          <CoverageTab coverage={coverage} missingInfo={missingInfo ?? null} />
        ) : (
          <EmptyState title="Coverage not available" blurb="Extract financial facts first, from the Financials tab." />
        )
      )}

      {activeTab === "score" && (
        <ScoreTab
          score={score ?? null}
          coverage={coverage ?? null}
          canScore={!!financialMetrics}
          isCalculating={calculateScore.isPending}
          onCalculate={handleCalculateScore}
        />
      )}

      {activeTab === "dd" && (
        <DueDiligenceTab
          report={generateDueDiligence.data ?? null}
          isGenerating={generateDueDiligence.isPending}
          onGenerate={handleGenerateDueDiligence}
          onExportMarkdown={() => handleExport("md")}
          onExportPdf={() => handleExport("pdf")}
        />
      )}

      {activeTab === "ddv2" && (
        <DueDiligenceV2Tab
          report={generateDueDiligenceV2.data ?? null}
          isGenerating={generateDueDiligenceV2.isPending}
          onGenerate={handleGenerateDueDiligenceV2}
          onExportMarkdown={() => handleExportV2("md")}
          onExportPdf={() => handleExportV2("pdf")}
        />
      )}
    </DocumentDetail>
  );
}
