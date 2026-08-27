export type Severity = 'high' | 'medium' | 'low';
export type FindingSource = 'document-stated' | 'kora-inferred' | 'deterministic';
export type DocStatus = 'uploaded' | 'processing' | 'completed' | 'failed';

export type ScreenId =
  | 'portfolio' | 'no-org' | 'documents' | 'members' | 'settings' | 'document';

export type DetailTabId =
  | 'overview' | 'analysis' | 'financials' | 'checks'
  | 'coverage' | 'score' | 'dd' | 'ddv2';

export interface Organization { id: string; name: string; slug: string; }

export interface Member {
  id: string;
  email: string;
  role: 'owner' | 'admin' | 'member';
  joinedAt: string;
  isCurrentUser?: boolean;
}

export interface DocumentSummary {
  id: string;
  filename: string;
  companyName?: string;
  status: DocStatus;
  sizeLabel: string;
  uploadedAt: string;
  contentType?: string;
  pages?: number | null;
  processedAt?: string | null;
}

export interface Finding {
  id: string;
  title: string;
  detail: string;
  severity: Severity;
  source: FindingSource;
  category?: string;
  /** e.g. "gross_margin · 2025" */
  metricRef?: string;
}

export interface CoverageCategory {
  name: string;
  filled: number;
  total: number;
}

export interface MissingField {
  key: string;
  guidance: string;
}

export interface MissingByCategory {
  category: string;
  fields: MissingField[];
}

export interface CoverageReport {
  percent: number;
  fieldsFilled: number;
  fieldsTotal: number;
  threshold: number;
  categories: CoverageCategory[];
  criticalGaps: string[];
  missingByCategory: MissingByCategory[];
}

export interface ScoreBreakdown { label: string; value: number | null; note?: string; }

export interface ScoreReport {
  /** null = insufficient evidence; render the withheld state, never a fake number. */
  composite: number | null;
  confidence?: number;
  breakdown: ScoreBreakdown[];
  criticalGaps: string[];
}

export interface MetricRow { key: string; value: string | null; flagged?: boolean; }

export interface FinancialsReport { confidence: number; metrics: MetricRow[]; }

export interface ExtractedFacts {
  company?: string;
  industry?: string;
  summary?: string;
  businessModel?: string;
  keyProducts: string[];
  revenueStreams: string[];
  targetCustomers: string[];
  competitors: string[];
  risks: string[];
  opportunities: string[];
}

export interface SignalScore { label: string; value: number; }

export interface SnapshotReport {
  score: number | null;
  coverage: number;
  threshold: number;
  positiveSignals: SignalScore[];
  topConcerns: Finding[];
  totalConcerns: number;
  criticalGaps: string[];
  recommendedNextStep: string;
  facts: ExtractedFacts;
}

export interface DiligenceReport {
  verdict: string;
  executiveSummary: string;
  headlineMetrics: { key: string; value: string }[];
  redFlags: { title: string; detail: string; level: 'warning' | 'critical' }[];
  founderQuestions: { severity: Severity; question: string }[];
}

export interface ChatSource { label: string; }

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  sources?: ChatSource[];
}
