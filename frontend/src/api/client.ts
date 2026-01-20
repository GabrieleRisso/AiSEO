const API_BASE = 'http://localhost:8000/api';

export interface BrandResponse {
  id: string;
  name: string;
  type: string;
  color: string;
  visibility: number;
  avgPosition: number;
  trend: string;
  sentiment: string;
}

export interface PromptBrandMentionResponse {
  brandId: string;
  brandName: string;
  position: number;
  mentioned: boolean;
  sentiment: string;
}

export interface SourceInPromptResponse {
  domain: string;
  url: string;
  title: string | null;
  description: string | null;
  publishedDate: string | null;
  citationOrder: number;
}

export interface RunResponse {
  id: number;
  runNumber: number;
  scrapedAt: string;
  visibility: number;
  avgPosition: number;
  totalMentions: number;
  brands: PromptBrandMentionResponse[];
  responseText: string | null;
  sources: SourceInPromptResponse[];
}

export interface PromptResponse {
  id: string;
  query: string;
  visibility: number;
  avgPosition: number;
  totalMentions: number;
  totalRuns: number;
  brands: PromptBrandMentionResponse[];
}

export interface PromptDetailResponse extends PromptResponse {
  runs: RunResponse[];
}

export interface SourceResponse {
  domain: string;
  usage: number;
  avgCitations: number;
}

export interface MetricResponse {
  value: number;
  change: number;
  total?: number;
}

export interface DashboardMetricsResponse {
  visibility: MetricResponse;
  totalPrompts: MetricResponse;
  totalSources: MetricResponse;
  avgPosition: MetricResponse;
}

export interface DailyVisibilityResponse {
  date: string;
  shopify: number | null;
  woocommerce: number | null;
  bigcommerce: number | null;
  wix: number | null;
  squarespace: number | null;
}

async function fetchJson<T>(endpoint: string): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`);
  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json();
}

export async function fetchBrands(): Promise<BrandResponse[]> {
  return fetchJson<BrandResponse[]>('/brands');
}

export async function fetchPrompts(): Promise<PromptResponse[]> {
  return fetchJson<PromptResponse[]>('/prompts');
}

export async function fetchPromptDetail(promptId: number): Promise<PromptDetailResponse> {
  return fetchJson<PromptDetailResponse>(`/prompts/${promptId}`);
}

export async function fetchSources(): Promise<SourceResponse[]> {
  return fetchJson<SourceResponse[]>('/sources');
}

export async function fetchMetrics(): Promise<DashboardMetricsResponse> {
  return fetchJson<DashboardMetricsResponse>('/metrics');
}

export async function fetchVisibilityData(): Promise<DailyVisibilityResponse[]> {
  return fetchJson<DailyVisibilityResponse[]>('/visibility');
}

// Sources Analytics types
export interface DomainBreakdownResponse {
  domain: string;
  citations: number;
  percentage: number;
  type: string;
}

export interface SourceTypeResponse {
  type: string;
  count: number;
  percentage: number;
}

export interface TopSourceResponse {
  id: number;
  domain: string;
  url: string;
  title: string | null;
  citations: number;
  prompts: string[];
}

export interface SourcesSummaryResponse {
  totalSources: number;
  totalDomains: number;
  totalCitations: number;
  avgCitationsPerSource: number;
}

export interface SourcesAnalyticsResponse {
  summary: SourcesSummaryResponse;
  domainBreakdown: DomainBreakdownResponse[];
  sourceTypes: SourceTypeResponse[];
  topSources: TopSourceResponse[];
}

// Suggestions types
export interface SuggestionExampleResponse {
  type: string;
  domain?: string;
  title?: string;
  query?: string;
}

export interface SuggestionResponse {
  id: number;
  priority: string;
  category: string;
  title: string;
  description: string;
  stat: string;
  statLabel: string;
  action: string;
  examples: SuggestionExampleResponse[];
}

export interface SuggestionsDataResponse {
  score: number;
  suggestions: SuggestionResponse[];
}

export async function fetchSourcesAnalytics(): Promise<SourcesAnalyticsResponse> {
  return fetchJson<SourcesAnalyticsResponse>('/sources/analytics');
}

export async function fetchSuggestions(): Promise<SuggestionsDataResponse> {
  return fetchJson<SuggestionsDataResponse>('/suggestions');
}

// Brand Management types
export interface BrandPromptDetailResponse {
  query: string;
  position: number | null;
  sentiment: string | null;
  scrapedAt: string;
}

export interface BrandMonthlyVisibilityResponse {
  month: string;
  visibility: number;
}

export interface BrandDetailResponse {
  id: string;
  name: string;
  type: string;
  color: string;
  variations: string[];
  visibility: number;
  avgPosition: number;
  trend: string;
  sentiment: string;
  totalMentions: number;
  totalPrompts: number;
  topPrompts: BrandPromptDetailResponse[];
  visibilityByMonth: BrandMonthlyVisibilityResponse[];
}

export interface BrandsListResponse {
  brands: BrandDetailResponse[];
}

export interface BrandCreateRequest {
  id: string;
  name: string;
  type: string;
  color: string;
  variations: string[];
}

export async function fetchBrandsDetails(): Promise<BrandsListResponse> {
  return fetchJson<BrandsListResponse>('/brands/details');
}

export async function createBrand(brand: BrandCreateRequest): Promise<BrandDetailResponse> {
  const response = await fetch(`${API_BASE}/brands`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(brand),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || `API error: ${response.status}`);
  }
  return response.json();
}

export async function deleteBrand(brandId: string): Promise<{ success: boolean; message: string }> {
  const response = await fetch(`${API_BASE}/brands/${brandId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || `API error: ${response.status}`);
  }
  return response.json();
}
