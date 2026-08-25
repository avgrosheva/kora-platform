import { apiClient, ApiError } from "@/lib/api-client";
import { downloadBlob, parseFilename } from "@/lib/download";
import type {
  DocumentAnalysisRead,
  DocumentListResponse,
  DocumentRead,
  DueDiligenceResponse,
  DueDiligenceV2Response,
  FinancialMetricsRead,
  FindingsResponse,
  InvestmentScoreResponse,
  MetricsResponse,
  ValidationChecksResponse,
  CoverageAssessmentRead,
  MissingInformationResponse,
} from "@/types/api";

async function fetchOrNull<T>(fn: () => Promise<T>): Promise<T | null> {
  try {
    return await fn();
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}

export const documentsApi = {
  list: async (organizationId: string): Promise<DocumentListResponse> => {
    const { data } = await apiClient.get<DocumentListResponse>("/documents", {
      params: { organization_id: organizationId },
    });
    return data;
  },

  get: async (documentId: string): Promise<DocumentRead> => {
    const { data } = await apiClient.get<DocumentRead>(`/documents/${documentId}`);
    return data;
  },

  upload: async (
    organizationId: string,
    file: File,
    onProgress?: (percent: number) => void
  ): Promise<DocumentRead> => {
    const formData = new FormData();
    formData.append("organization_id", organizationId);
    formData.append("file", file);

    const { data } = await apiClient.post<DocumentRead>("/documents", formData, {
      onUploadProgress: (event) => {
        if (event.total && onProgress) {
          onProgress(Math.round((event.loaded / event.total) * 100));
        }
      },
    });
    return data;
  },

  remove: async (documentId: string): Promise<void> => {
    await apiClient.delete(`/documents/${documentId}`);
  },

  process: async (documentId: string): Promise<DocumentRead> => {
    const { data } = await apiClient.post<DocumentRead>(`/documents/${documentId}/process`);
    return data;
  },

  analyze: async (documentId: string): Promise<DocumentAnalysisRead> => {
    const { data } = await apiClient.post<DocumentAnalysisRead>(`/documents/${documentId}/analyze`);
    return data;
  },

  getAnalysis: (documentId: string) =>
    fetchOrNull(async () => {
      const { data } = await apiClient.get<DocumentAnalysisRead>(`/documents/${documentId}/analysis`);
      return data;
    }),

  runFinancialAnalysis: async (documentId: string): Promise<FinancialMetricsRead> => {
    const { data } = await apiClient.post<FinancialMetricsRead>(
      `/documents/${documentId}/financial-analysis`
    );
    return data;
  },

  getFinancialMetrics: (documentId: string) =>
    fetchOrNull(async () => {
      const { data } = await apiClient.get<FinancialMetricsRead>(
        `/documents/${documentId}/financial-analysis`
      );
      return data;
    }),

  calculateScore: async (documentId: string): Promise<InvestmentScoreResponse> => {
    const { data } = await apiClient.post<InvestmentScoreResponse>(`/documents/${documentId}/score`);
    return data;
  },

  getScore: (documentId: string) =>
    fetchOrNull(async () => {
      const { data } = await apiClient.get<InvestmentScoreResponse>(`/documents/${documentId}/score`);
      return data;
    }),

  indexDocument: async (documentId: string): Promise<{ document_id: string; chunks_indexed: number }> => {
    const { data } = await apiClient.post(`/documents/${documentId}/index`);
    return data;
  },

  generateDueDiligence: async (documentId: string): Promise<DueDiligenceResponse> => {
    const { data } = await apiClient.post<DueDiligenceResponse>(`/documents/${documentId}/due-diligence`);
    return data;
  },

  exportMarkdown: async (documentId: string, fallbackName: string): Promise<void> => {
    const response = await apiClient.get(`/documents/${documentId}/report.md`, {
      responseType: "blob",
    });
    downloadBlob(response.data, parseFilename(response.headers["content-disposition"], fallbackName));
  },

  exportPdf: async (documentId: string, fallbackName: string): Promise<void> => {
    const response = await apiClient.get(`/documents/${documentId}/report.pdf`, {
      responseType: "blob",
    });
    downloadBlob(response.data, parseFilename(response.headers["content-disposition"], fallbackName));
  },

  getMetrics: async (documentId: string): Promise<MetricsResponse> => {
    const { data } = await apiClient.get<MetricsResponse>(`/documents/${documentId}/metrics`);
    return data;
  },

  getChecks: async (documentId: string): Promise<ValidationChecksResponse> => {
    const { data } = await apiClient.get<ValidationChecksResponse>(`/documents/${documentId}/checks`);
    return data;
  },

  getFindings: async (documentId: string): Promise<FindingsResponse> => {
    const { data } = await apiClient.get<FindingsResponse>(`/documents/${documentId}/findings`);
    return data;
  },

  getCoverage: async (documentId: string): Promise<CoverageAssessmentRead> => {
    const { data } = await apiClient.get<CoverageAssessmentRead>(`/documents/${documentId}/coverage`);
    return data;
  },

  getMissingInformation: async (documentId: string): Promise<MissingInformationResponse> => {
    const { data } = await apiClient.get<MissingInformationResponse>(
      `/documents/${documentId}/missing-information`
    );
    return data;
  },

  extractFinancialFacts: async (documentId: string): Promise<{ document_id: string; facts_extracted: number }> => {
    const { data } = await apiClient.post(`/documents/${documentId}/extract-financial-facts`);
    return data;
  },

  analyzeWithCitations: async (documentId: string): Promise<DocumentAnalysisRead> => {
    const { data } = await apiClient.post<DocumentAnalysisRead>(
      `/documents/${documentId}/analyze-with-citations`
    );
    return data;
  },

  generateDueDiligenceV2: async (documentId: string): Promise<DueDiligenceV2Response> => {
    const { data } = await apiClient.post<DueDiligenceV2Response>(
      `/documents/${documentId}/due-diligence-v2`
    );
    return data;
  },
  
};