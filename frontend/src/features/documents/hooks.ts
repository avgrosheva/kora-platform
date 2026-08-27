"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { documentsApi } from "./api";

export function useDocuments(organizationId: string | null) {
  return useQuery({
    queryKey: ["documents", organizationId],
    queryFn: () => documentsApi.list(organizationId as string),
    enabled: !!organizationId,
    refetchInterval: (query) => {
      const hasInFlight = query.state.data?.items.some(
        (d) => d.status === "uploaded" || d.status === "processing"
      );
      return hasInFlight ? 3000 : false;
    },
  });
}

export function useDocument(documentId: string | undefined) {
  return useQuery({
    queryKey: ["documents", "detail", documentId],
    queryFn: () => documentsApi.get(documentId as string),
    enabled: !!documentId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "uploaded" || status === "processing" ? 3000 : false;
    },
  });
}

export function useUploadDocument(organizationId: string) {
  const queryClient = useQueryClient();
  const [progress, setProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);

  const upload = async (file: File): Promise<string> => {
    setIsUploading(true);
    setProgress(0);
    try {
      const doc = await documentsApi.upload(organizationId, file, setProgress);
      queryClient.invalidateQueries({ queryKey: ["documents", organizationId] });
      return doc.id;
    } finally {
      setIsUploading(false);
    }
  };

  return { upload, progress, isUploading };
}

export function useDeleteDocument(organizationId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (documentId: string) => documentsApi.remove(documentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", organizationId] });
    },
  });
}

export function useProcessDocument(documentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => documentsApi.process(documentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", "detail", documentId] });
    },
  });
}

export function useAnalysis(documentId: string | undefined) {
  return useQuery({
    queryKey: ["documents", "detail", documentId, "analysis"],
    queryFn: () => documentsApi.getAnalysis(documentId as string),
    enabled: !!documentId,
  });
}

export function useFinancialMetrics(documentId: string | undefined) {
  return useQuery({
    queryKey: ["documents", "detail", documentId, "financials"],
    queryFn: () => documentsApi.getFinancialMetrics(documentId as string),
    enabled: !!documentId,
  });
}

export function useRunFinancialAnalysis(documentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => documentsApi.runFinancialAnalysis(documentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", "detail", documentId, "financials"] });
    },
  });
}

export function useScore(documentId: string | undefined) {
  return useQuery({
    queryKey: ["documents", "detail", documentId, "score"],
    queryFn: () => documentsApi.getScore(documentId as string),
    enabled: !!documentId,
  });
}

export function useCalculateScore(documentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => documentsApi.calculateScore(documentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", "detail", documentId, "score"] });
    },
  });
}

export function useIndexDocument(documentId: string) {
  return useMutation({
    mutationFn: () => documentsApi.indexDocument(documentId),
  });
}

export function useGenerateDueDiligence(documentId: string) {
  return useMutation({
    mutationFn: () => documentsApi.generateDueDiligence(documentId),
  });
}

export function useDocumentMetrics(documentId: string | undefined) {
  return useQuery({
    queryKey: ["documents", "detail", documentId, "metrics"],
    queryFn: () => documentsApi.getMetrics(documentId as string),
    enabled: !!documentId,
  });
}

export function useDocumentChecks(documentId: string | undefined) {
  return useQuery({
    queryKey: ["documents", "detail", documentId, "checks"],
    queryFn: () => documentsApi.getChecks(documentId as string),
    enabled: !!documentId,
  });
}

export function useDocumentFindings(documentId: string | undefined) {
  return useQuery({
    queryKey: ["documents", "detail", documentId, "findings"],
    queryFn: () => documentsApi.getFindings(documentId as string),
    enabled: !!documentId,
  });
}

export function useDocumentCoverage(documentId: string | undefined) {
  return useQuery({
    queryKey: ["documents", "detail", documentId, "coverage"],
    queryFn: () => documentsApi.getCoverage(documentId as string),
    enabled: !!documentId,
  });
}

export function useMissingInformation(documentId: string | undefined) {
  return useQuery({
    queryKey: ["documents", "detail", documentId, "missing-information"],
    queryFn: () => documentsApi.getMissingInformation(documentId as string),
    enabled: !!documentId,
  });
}

export function useExtractFinancialFacts(documentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => documentsApi.extractFinancialFacts(documentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", "detail", documentId, "metrics"] });
      queryClient.invalidateQueries({ queryKey: ["documents", "detail", documentId, "checks"] });
      queryClient.invalidateQueries({ queryKey: ["documents", "detail", documentId, "coverage"] });
      queryClient.invalidateQueries({ queryKey: ["documents", "detail", documentId, "missing-information"] });
    },
  });
}

export function useAnalyzeWithCitations(documentId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => documentsApi.analyzeWithCitations(documentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", "detail", documentId, "analysis"] });
      queryClient.invalidateQueries({ queryKey: ["documents", "detail", documentId, "coverage"] });
    },
  });
}

export function useGenerateDueDiligenceV2(documentId: string) {
  return useMutation({
    mutationFn: () => documentsApi.generateDueDiligenceV2(documentId),
  });
}