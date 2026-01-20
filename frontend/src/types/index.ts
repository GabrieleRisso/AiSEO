export interface Brand {
  id: string;
  name: string;
  type: 'primary' | 'competitor';
  visibility: number;
  trend: 'up' | 'down' | 'stable';
  sentiment: 'positive' | 'neutral' | 'negative';
  avgPosition: number;
  color: string;
}

export interface DailyVisibility {
  date: string;
  [brandId: string]: number | string;
}

export interface Source {
  domain: string;
  usage: number;
  avgCitations: number;
}

export interface PromptBrandMention {
  brandId: string;
  brandName: string;
  position: number;
  mentioned: boolean;
  sentiment: 'positive' | 'neutral' | 'negative';
}

export interface Prompt {
  id: string;
  query: string;
  visibility: number;
  avgPosition: number;
  totalMentions: number;
  brands: PromptBrandMention[];
}

export interface MetricData {
  label: string;
  value: string | number;
  change?: number;
  changeLabel?: string;
}

// Search types
export type SearchCategory = 'prompts' | 'brands' | 'sources';

export interface SearchResult {
  id: string;
  category: SearchCategory;
  title: string;
  subtitle?: string;
  href: string;
  color?: string;
}

export interface SearchResultGroup {
  category: SearchCategory;
  label: string;
  results: SearchResult[];
}

// Sources Analytics types
export interface DomainBreakdown {
  domain: string;
  citations: number;
  percentage: number;
  type: 'brand' | 'blog' | 'community' | 'news' | 'review' | 'other';
}

export interface SourceType {
  type: string;
  count: number;
  percentage: number;
}

export interface TopSource {
  id: number;
  domain: string;
  url: string;
  title: string | null;
  citations: number;
  prompts: string[];
}

export interface SourcesSummary {
  totalSources: number;
  totalDomains: number;
  totalCitations: number;
  avgCitationsPerSource: number;
}

export interface SourcesAnalytics {
  summary: SourcesSummary;
  domainBreakdown: DomainBreakdown[];
  sourceTypes: SourceType[];
  topSources: TopSource[];
}

// Suggestions types
export interface SuggestionExample {
  type: 'source' | 'prompt';
  domain?: string;
  title?: string;
  query?: string;
}

export interface Suggestion {
  id: number;
  priority: 'high' | 'medium' | 'low';
  category: 'content' | 'community' | 'authority' | 'technical';
  title: string;
  description: string;
  stat: string;
  statLabel: string;
  action: string;
  examples: SuggestionExample[];
}

export interface SuggestionsData {
  score: number;
  suggestions: Suggestion[];
}

// Brand Management types
export interface BrandPromptDetail {
  query: string;
  position: number | null;
  sentiment: string | null;
  scrapedAt: string;
}

export interface BrandMonthlyVisibility {
  month: string;
  visibility: number;
}

export interface BrandDetail {
  id: string;
  name: string;
  type: 'primary' | 'competitor';
  color: string;
  variations: string[];
  visibility: number;
  avgPosition: number;
  trend: 'up' | 'down' | 'stable';
  sentiment: 'positive' | 'neutral' | 'negative';
  totalMentions: number;
  totalPrompts: number;
  topPrompts: BrandPromptDetail[];
  visibilityByMonth: BrandMonthlyVisibility[];
}

export interface BrandCreate {
  id: string;
  name: string;
  type: 'primary' | 'competitor';
  color: string;
  variations: string[];
}

export interface BrandsListData {
  brands: BrandDetail[];
}
