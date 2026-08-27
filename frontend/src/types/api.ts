/** Types mirroring the backend's actual API response schemas. */

export type MembershipRole = "owner" | "admin" | "member";

export type DocumentStatus = "uploaded" | "processing" | "completed" | "failed";

export interface UserRead {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
  updated_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface OrganizationRead {
  id: string;
  name: string;
  slug: string;
  created_at: string;
  updated_at: string;
}

export interface MembershipRead {
  id: string;
  organization_id: string;
  user_id: string;
  email: string;
  role: MembershipRole;
  created_at: string;
}

export interface DocumentRead {
  id: string;
  organization_id: string;
  uploaded_by: string;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  status: DocumentStatus;
  page_count: number | null;
  processing_error: string | null;
  processed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  items: DocumentRead[];
  total: number;
}

export interface DocumentAnalysisRead {
  id: string;
  document_id: string;
  summary: string | null;
  company_name: string | null;
  industry: string | null;
  business_model: string | null;
  key_products: string[] | null;
  risks: string[] | null;
  opportunities: string[] | null;
  revenue_streams: string[] | null;
  customers: string[] | null;
  competitors: string[] | null;
  created_at: string;
}

export interface FinancialMetricsRead {
  id: string;
  document_id: string;
  currency: string | null;
  revenue: number | null;
  arr: number | null;
  mrr: number | null;
  gross_margin: number | null;
  ebitda: number | null;
  burn_rate: number | null;
  runway_months: number | null;
  cash: number | null;
  customers: number | null;
  growth_rate: number | null;
  cac: number | null;
  ltv: number | null;
  valuation: number | null;
  confidence_score: number | null;
  created_at: string;
}

// null for score records calculated before this status existed, until
// the next recalculation.
export type AssessmentStatus = "sufficient_evidence" | "insufficient_evidence" | null;

export interface InvestmentScoreResponse {
  id: string;
  document_id: string;
  // Either no sub-scores were computable at all, OR assessment_status
  // is "insufficient_evidence" -- a null here is never a low score, it
  // means no single composite number is being asserted. Never render a
  // fallback numeric value (e.g. 0) in its place.
  overall_score: number | null;
  financial_score: number | null;
  growth_score: number | null;
  risk_score: number | null;
  market_score: number | null;
  team_score: number | null;
  confidence_score: number | null;
  reasoning: string | null;
  created_at: string;
  updated_at: string;
  methodology_version: string | null;
  category_breakdown: Record<string, CategoryBreakdownEntry> | null;
  assessment_status: AssessmentStatus;
}

export interface DashboardResponse {
  total_companies: number;
  total_documents: number;
  companies_analyzed: number;
  average_arr: number | null;
  average_growth_rate: number | null;
  average_burn_rate: number | null;
  average_runway: number | null;
  average_valuation: number | null;
  top_company: { document_id: string; company_name: string | null; arr: number; currency: string | null } | null;
  recent_documents: Array<{
    id: string;
    filename: string;
    status: DocumentStatus;
    created_at: string;
    organization_id: string;
  }>;
  portfolio_stats: {
    companies_with_positive_growth: number;
    companies_with_negative_growth: number;
    companies_low_runway: number;
    average_confidence_score: number | null;
  };
  top_scored_companies: Array<{ document_id: string; company_name: string | null; overall_score: number }>;
  average_investment_score: number | null;
  highest_growth_company: { document_id: string; company_name: string | null; growth_rate: number } | null;
  highest_risk_company: { document_id: string; company_name: string | null; risk_score: number } | null;
}

export interface PortfolioCompany {
  document_id: string;
  company_name: string | null;
  industry: string | null;
  overall_score: number | null;
  arr: number | null;
  valuation: number | null;
  runway_months: number | null;
  growth_rate: number | null;
  burn_rate: number | null;
  confidence_score: number | null;
  currency: string | null;
}

export interface PortfolioDocumentRow {
  document_id: string;
  filename: string;
  company_name: string | null;
  status: DocumentStatus;
  size_bytes: number;
  created_at: string;
  overall_score: number | null;
  coverage_percent: number | null;
  /** Only nonzero severities are present as keys; e.g. {} means no open findings. */
  open_findings: Partial<Record<"high" | "medium" | "low", number>>;
}

export interface PortfolioResponse {
  summary: {
    company_count: number;
    average_investment_score: number | null;
    average_arr: number | null;
    average_valuation: number | null;
    average_runway: number | null;
    average_growth: number | null;
    average_burn_rate: number | null;
    average_coverage: number | null;
  };
  overview: {
    top_10_companies: PortfolioCompany[];
    worst_10_companies: PortfolioCompany[];
    highest_growth_companies: PortfolioCompany[];
    highest_arr_companies: PortfolioCompany[];
    highest_valuation_companies: PortfolioCompany[];
    lowest_runway_companies: PortfolioCompany[];
    highest_burn_companies: PortfolioCompany[];
  };
  risk: {
    companies_at_risk: number;
    companies_with_negative_growth: number;
    companies_with_low_runway: number;
    companies_without_recent_documents: number;
    high_confidence_companies: number;
  };
  distribution: {
    score_buckets: Record<string, number>;
    valuation_buckets: Record<string, number>;
    arr_buckets: Record<string, number>;
    industry_distribution: Record<string, number>;
    country_distribution: Record<string, number>;
  };
  documents: PortfolioDocumentRow[];
}

export interface ChatSource {
  document_id: string;
  chunk_index: number;
  similarity_score: number;
  snippet: string;
}

export interface ChatResponse {
  answer: string;
  sources: ChatSource[];
  model_used: string;
}

export interface DueDiligenceSection {
  title: string;
  content: string;
}

export interface DueDiligenceResponse {
  document_id: string;
  sections: DueDiligenceSection[];
  sources: ChatSource[];
  model_used: string;
}

export interface ApiErrorBody {
  detail: string | Array<{ msg: string; loc: (string | number)[] }>;
  error_type?: string;
  request_id?: string;
}

export type FinancialMetricType =
  | "revenue" | "arr" | "mrr" | "gross_profit" | "gross_margin" | "ebitda" | "net_income"
  | "operating_expenses" | "cash" | "debt" | "burn_rate" | "cac" | "ltv"
  | "aov" | "orders" | "registered_customers" | "monthly_active_users"
  | "churn_rate" | "retention_rate" | "funding_amount"
  | "valuation_pre_money" | "valuation_post_money";

export type PeriodType = "month" | "quarter" | "year" | "point_in_time" | "unknown";
export type FinancialValueType = "actual" | "forecast" | "target" | "estimate" | "derived";
export type MetricStatus = "calculated" | "reported" | "missing_inputs" | "period_mismatch" | "ambiguous" | "invalid";

export interface RawFinancialFact {
  metric: FinancialMetricType;
  value: number;
  currency: string | null;
  period_type: PeriodType;
  period: string | null;
  value_type: FinancialValueType;
}

export interface MetricInputRef {
  name: string;
  value: number;
  period: string | null;
  source_citation_id: string | null;
}

export interface DerivedMetricRead {
  id: string;
  document_id: string;
  metric: string;
  period: string | null;
  value: number | null;
  display_value: string | null;
  formula: string;
  inputs: MetricInputRef[];
  status: MetricStatus;
  confidence: number | null;
  notes: string | null;
}

export interface MetricsResponse {
  financial_facts: RawFinancialFact[];
  derived_metrics: DerivedMetricRead[];
}

// ============================================================
// Validation Findings / Checks
// ============================================================

export type FindingSeverity = "info" | "warning" | "critical";

export interface ValidationFindingRead {
  id: string;
  document_id: string;
  severity: FindingSeverity;
  category: string;
  title: string;
  description: string;
  affected_metrics: string[];
  sources: string[];
  suggested_question: string | null;
  created_at: string;
}

export interface ValidationChecksResponse {
  findings: ValidationFindingRead[];
  critical_count: number;
  warning_count: number;
  info_count: number;
}

// ============================================================
// Unified Findings (deterministic + document-stated + Kora-inferred)
// ============================================================
//
// Distinct from ValidationFindingRead/FindingSeverity above (those stay
// as the deterministic-only /checks endpoint's shape). This is the
// richer facade from GET /documents/{id}/findings: it also carries
// document-stated qualitative risk claims and Kora's own inferences, on
// a 5-level severity scale rather than the 3-level one above.

export type UnifiedFindingType = "deterministic" | "document_stated" | "derived" | "ai_inferred";
export type UnifiedFindingSeverity = "critical" | "high" | "medium" | "low" | "informational";

export interface UnifiedFinding {
  title: string;
  category: string;
  severity: UnifiedFindingSeverity;
  type: UnifiedFindingType;
  evidence: string | null;
  explanation: string | null;
  implication: string | null;
  recommended_next_step: string | null;
}

export interface FindingsResponse {
  document_id: string;
  findings: UnifiedFinding[];
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  informational_count: number;
  deterministic_count: number;
  document_stated_count: number;
  ai_inferred_count: number;
}

// ============================================================
// Coverage Assessment
// ============================================================

export interface CategoryCoverage {
  found: number;
  required: number;
  score: number;
}

export interface CoverageAssessmentRead {
  document_id: string;
  overall_confidence: number;
  coverage: Record<string, CategoryCoverage>;
  source_coverage: number;
  ambiguities_count: number;
  critical_missing_fields: string[];
}

// ============================================================
// Missing Information Checklist
// ============================================================

export type FieldStatus = "found" | "missing" | "ambiguous" | "contradictory" | "not_applicable";

export interface ChecklistItemResult {
  category: string;
  field_name: string;
  status: FieldStatus;
  // What to ask for and why it matters, for a non-FOUND field; null when found.
  recommended_request: string | null;
}

export interface MissingInformationByCategory {
  category: string;
  missing: string[];
  ambiguous: string[];
  contradictory: string[];
}

export interface MissingInformationResponse {
  items: ChecklistItemResult[];
  by_category: MissingInformationByCategory[];
  total_required: number;
  total_found: number;
}

// ============================================================
// Investment Score v2 (category breakdown)
// ============================================================

export interface CategoryBreakdownEntry {
  status: "assessed" | "not_assessable";
  score: number | null;
  weight: number;
  contribution: number | null;
}

// Extends the existing InvestmentScoreResponse shape with the two new
// optional fields added in Step 7. Not a separate interface — the
// backend returns these on the SAME /score endpoint response.
export interface InvestmentScoreResponseV2 extends InvestmentScoreResponse {
  methodology_version: string | null;
  category_breakdown: Record<string, CategoryBreakdownEntry> | null;
}

// ============================================================
// Due Diligence v2
// ============================================================

export type RecommendationStatus =
  | "strong_candidate" | "worth_exploring" | "needs_more_info" | "concerns_identified";

export interface VerifiedFact {
  label: string;
  value_display: string;
  source_citation_id: string | null;
}

export interface FounderQuestion {
  question: string;
  category: string;
  priority: "high" | "medium";
}

export interface DueDiligenceV2Response {
  document_id: string;
  recommendation_status: RecommendationStatus;
  executive_summary: string;
  verified_facts: VerifiedFact[];
  sections: DueDiligenceSection[];
  red_flags: ValidationFindingRead[];
  founder_questions: FounderQuestion[];
  sources: ChatSource[];
  model_used: string;
}

// ============================================================
// Chat v2 (tool calling)
// ============================================================

export interface ToolCallRecord {
  tool_name: string;
  arguments: Record<string, unknown>;
  result_summary: string;
}

export interface ChatV2Response {
  answer: string;
  sources: ChatSource[];
  tool_calls: ToolCallRecord[];
  model_used: string;
}