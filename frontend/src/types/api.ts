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

export interface InvestmentScoreResponse {
  id: string;
  document_id: string;
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

export interface PortfolioResponse {
  summary: {
    company_count: number;
    average_investment_score: number | null;
    average_arr: number | null;
    average_valuation: number | null;
    average_runway: number | null;
    average_growth: number | null;
    average_burn_rate: number | null;
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