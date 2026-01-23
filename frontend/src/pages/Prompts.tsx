import { useState, useMemo, useEffect } from 'react';
import { useSearchParams } from 'react-router';
import { Search, ChevronDown, ChevronRight, ChevronUp, ExternalLink, Loader2, Calendar, Plus } from 'lucide-react';
import { PromptsSkeleton } from '../components/ui/Skeleton';
import { EmptyState } from '../components/ui/EmptyState';
import { Header } from '../components/layout/Header';
import { SentimentBadge } from '../components/ui/Badge';
import { AISourceSelector } from '../components/ui/AISourceSelector';
import { type AISource } from '../components/ui/AISourceIcons';
import { usePrompts, useBrands, usePromptDetail } from '../hooks/useApi';
import { config } from '../config';
import type { PromptResponse } from '../api/client';

interface PromptBrandMention {
  brandId: string;
  brandName: string;
  position: number;
  mentioned: boolean;
  sentiment: string;
}

interface Brand {
  id: string;
  name: string;
  color: string;
}

function PromptRow({
  prompt,
  isExpanded,
  onToggle,
  index,
  brands
}: {
  prompt: PromptResponse;
  isExpanded: boolean;
  onToggle: () => void;
  index: number;
  brands: Brand[];
}) {
  const mentionedBrands = prompt.brands.filter((b) => b.mentioned);

  return (
    <>
      <tr
        onClick={onToggle}
        className="table-row-highlight cursor-pointer animate-fade-in"
        style={{ animationDelay: `${200 + index * 40}ms` }}
      >
        <td className="px-5 py-4 whitespace-nowrap">
          <div className="flex items-center gap-2">
            <div className={`transition-transform duration-200 ${isExpanded ? 'rotate-90' : ''}`}>
              {isExpanded ? (
                <ChevronDown className="w-4 h-4 text-[var(--accent-primary)]" />
              ) : (
                <ChevronRight className="w-4 h-4 text-[var(--text-muted)]" />
              )}
            </div>
            <span className="text-sm text-[var(--text-primary)] font-medium">{prompt.query}</span>
          </div>
        </td>
        <td className="px-5 py-4 whitespace-nowrap">
          <div className="flex items-center gap-3">
            <div className="progress-bar w-20">
              <div
                className="progress-bar-fill"
                style={{ width: `${prompt.visibility}%` }}
              />
            </div>
            <span className="text-sm font-semibold font-mono text-[var(--text-data)]">
              {prompt.visibility}%
            </span>
          </div>
        </td>
        <td className="px-5 py-4 whitespace-nowrap text-center">
          <span className="text-sm font-mono text-[var(--text-secondary)]">
            {prompt.avgPosition > 0 ? `#${prompt.avgPosition}` : '-'}
          </span>
        </td>
        <td className="px-5 py-4 whitespace-nowrap text-center">
          <span className="text-sm font-mono text-[var(--text-secondary)]">{prompt.totalMentions}</span>
        </td>
        <td className="px-5 py-4 whitespace-nowrap text-center">
          <span className="text-sm font-mono text-[var(--accent-primary)]">{prompt.totalRuns}</span>
        </td>
        <td className="px-5 py-4 whitespace-nowrap text-center">
          <div className="flex items-center -space-x-2 justify-center">
            {mentionedBrands.slice(0, 4).map((mention) => {
              const brand = brands.find((b) => b.id === mention.brandId);
              return (
                <div
                  key={mention.brandId}
                  className="w-7 h-7 rounded-full border-2 border-[var(--bg-primary)] flex items-center justify-center text-[10px] font-semibold text-white transition-transform hover:scale-110 hover:z-10"
                  style={{
                    backgroundColor: brand?.color || '#6B7280',
                    boxShadow: `0 0 8px ${brand?.color || '#6B7280'}40`,
                  }}
                  title={mention.brandName}
                >
                  {mention.brandName.charAt(0)}
                </div>
              );
            })}
            {mentionedBrands.length > 4 && (
              <div className="w-7 h-7 rounded-full border-2 border-[var(--bg-primary)] bg-[var(--bg-elevated)] flex items-center justify-center text-[10px] font-semibold text-[var(--text-muted)]">
                +{mentionedBrands.length - 4}
              </div>
            )}
          </div>
        </td>
      </tr>
      {isExpanded && (
        <ExpandedPromptDetail
          queryId={prompt.id}
          brands={brands}
        />
      )}
    </>
  );
}

function highlightBrands(text: string, brands: Brand[]): React.ReactNode {
  if (!text || brands.length === 0) return text;

  // Create regex pattern for all brand names (escape special regex characters)
  const escapedNames = brands.map(b => b.name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  const pattern = new RegExp(`(${escapedNames.join('|')})`, 'gi');

  const parts = text.split(pattern);

  return parts.map((part, index) => {
    const brand = brands.find(b => b.name.toLowerCase() === part.toLowerCase());
    if (brand) {
      return (
        <span key={index} style={{ color: brand.color, fontWeight: 600 }}>
          {part}
        </span>
      );
    }
    return part;
  });
}

function ExpandedPromptDetail({ queryId, brands }: { queryId: string; brands: Brand[] }) {
  const idx = parseInt(queryId.replace('query-', '').replace('prompt-', ''));
  const { data: detail, loading, error } = usePromptDetail(idx);
  const [selectedRunIndex, setSelectedRunIndex] = useState<number>(0);

  if (loading) {
    return (
      <tr className="animate-fade-in">
        <td colSpan={6} className="px-5 py-8 bg-[var(--bg-elevated)]/50">
          <div className="flex items-center justify-center gap-2 text-[var(--text-muted)]">
            <Loader2 className="w-4 h-4 animate-spin" />
            Loading details...
          </div>
        </td>
      </tr>
    );
  }

  if (error || !detail) {
    return (
      <tr className="animate-fade-in">
        <td colSpan={6} className="px-5 py-8 bg-[var(--bg-elevated)]/50">
          <div className="text-center text-red-400">Failed to load details</div>
        </td>
      </tr>
    );
  }

  const runs = detail.runs || [];
  const selectedRun = runs[selectedRunIndex] || runs[0];

  return (
    <tr className="animate-fade-in">
      <td colSpan={6} className="px-5 py-4 bg-[var(--bg-elevated)]/50">
        <div className="pl-6 space-y-6">
          {/* Aggregated Stats */}
          <div className="flex items-center gap-6 text-sm">
            <div className="flex items-center gap-2">
              <span className="text-[var(--text-muted)]">Avg Visibility:</span>
              <span className="font-semibold text-[var(--text-data)]">{detail.visibility}%</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[var(--text-muted)]">Avg Position:</span>
              <span className="font-semibold text-[var(--text-secondary)]">
                {detail.avgPosition > 0 ? `#${detail.avgPosition}` : '-'}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[var(--text-muted)]">Total Runs:</span>
              <span className="font-semibold text-[var(--accent-primary)]">{detail.totalRuns}</span>
            </div>
          </div>

          {/* Run Selector */}
          {runs.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-[var(--text-primary)] mb-3">Runs</h4>
              <div className="flex flex-wrap gap-2">
                {runs.map((run, index) => {
                  const runDate = new Date(run.scrapedAt);
                  const monthLabel = runDate.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
                  return (
                    <button
                      key={run.id}
                      onClick={() => setSelectedRunIndex(index)}
                      className={`px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                        selectedRunIndex === index
                          ? 'bg-[var(--accent-primary)] text-white'
                          : 'bg-[var(--bg-card)] text-[var(--text-secondary)] hover:bg-[var(--bg-elevated)] border border-[var(--border-subtle)]'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <Calendar className="w-3 h-3" />
                        <span>{monthLabel}</span>
                        <span className="text-xs opacity-75">({run.visibility}%)</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Selected Run Details */}
          {selectedRun && (
            <div className="space-y-6 border-t border-[var(--border-subtle)] pt-4">
              {/* Run Stats */}
              <div className="flex items-center gap-6 text-sm">
                <div className="flex items-center gap-2 text-[var(--text-muted)]">
                  <Calendar className="w-4 h-4" />
                  <span>{new Date(selectedRun.scrapedAt).toLocaleDateString()}</span>
                </div>
                <div>
                  <span className="text-[var(--text-muted)]">Visibility: </span>
                  <span className="font-semibold text-[var(--text-data)]">{selectedRun.visibility}%</span>
                </div>
                <div>
                  <span className="text-[var(--text-muted)]">Position: </span>
                  <span className="font-semibold text-[var(--text-secondary)]">
                    {selectedRun.avgPosition > 0 ? `#${selectedRun.avgPosition}` : '-'}
                  </span>
                </div>
              </div>

              {/* Brand Breakdown */}
              <div>
                <h4 className="text-sm font-semibold text-[var(--text-primary)] mb-4">Brand Breakdown</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {selectedRun.brands.map((mention) => (
                    <BrandMentionCard key={mention.brandId} mention={mention} brands={brands} />
                  ))}
                </div>
              </div>

              {/* AI Response */}
              {selectedRun.responseText && (
                <div>
                  <h4 className="text-sm font-semibold text-[var(--text-primary)] mb-3">AI Response</h4>
                  <div className="bg-[var(--bg-card)] rounded-xl p-4 border border-[var(--border-subtle)] max-h-96 overflow-y-auto">
                    <pre className="text-sm text-[var(--text-secondary)] whitespace-pre-wrap font-sans leading-relaxed">
                      {highlightBrands(selectedRun.responseText, brands)}
                    </pre>
                  </div>
                </div>
              )}

              {/* Sources */}
              {selectedRun.sources && selectedRun.sources.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-[var(--text-primary)] mb-3">
                    Sources ({selectedRun.sources.length})
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 max-h-64 overflow-y-auto">
                    {selectedRun.sources.map((source, idx) => (
                      <a
                        key={idx}
                        href={source.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-start gap-3 p-3 rounded-lg bg-[var(--bg-card)] border border-[var(--border-subtle)] hover:border-[var(--border-accent)] transition-colors group"
                      >
                        <span className="text-xs font-mono text-[var(--text-muted)] mt-0.5">
                          [{source.citationOrder}]
                        </span>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-medium text-[var(--text-primary)] truncate group-hover:text-[var(--accent-primary)] transition-colors">
                              {source.title || source.domain}
                            </span>
                            <ExternalLink className="w-3 h-3 text-[var(--text-muted)] flex-shrink-0" />
                          </div>
                          <div className="text-xs text-[var(--text-muted)] mt-1">
                            {source.domain}
                            {source.publishedDate && ` • ${source.publishedDate}`}
                          </div>
                        </div>
                      </a>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </td>
    </tr>
  );
}

function BrandMentionCard({ mention, brands }: { mention: PromptBrandMention; brands: Brand[] }) {
  const brand = brands.find((b) => b.id === mention.brandId);

  return (
    <div
      className={`p-4 rounded-xl border transition-all duration-200 ${
        mention.mentioned
          ? 'bg-[var(--bg-card)] border-[var(--border-subtle)] hover:border-[var(--border-accent)]'
          : 'bg-[var(--bg-elevated)]/50 border-transparent opacity-60'
      }`}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div
            className="w-3 h-3 rounded-full"
            style={{
              backgroundColor: brand?.color || '#6B7280',
              boxShadow: mention.mentioned ? `0 0 8px ${brand?.color || '#6B7280'}40` : 'none',
            }}
          />
          <span className="text-sm font-medium text-[var(--text-primary)]">{mention.brandName}</span>
        </div>
        {mention.mentioned && <SentimentBadge sentiment={mention.sentiment as 'positive' | 'neutral' | 'negative'} />}
      </div>
      <div className="flex items-center gap-4 text-xs">
        <span className="text-[var(--text-muted)]">
          Position:{' '}
          <span className="font-semibold font-mono text-[var(--text-secondary)]">
            {mention.mentioned ? `#${mention.position}` : '-'}
          </span>
        </span>
        <span className="text-[var(--text-muted)]">
          Status:{' '}
          <span className={`font-semibold ${mention.mentioned ? 'text-[#4ade80]' : 'text-[var(--text-muted)]'}`}>
            {mention.mentioned ? 'Mentioned' : 'Not mentioned'}
          </span>
        </span>
      </div>
    </div>
  );
}

type SortKey = 'query' | 'visibility' | 'avgPosition' | 'totalMentions' | 'totalRuns';
type SortDirection = 'asc' | 'desc' | null;

export function Prompts() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<SortKey | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>(null);
  const [selectedAISource, setSelectedAISource] = useState<AISource>('ai-overview');

  const { data: prompts, loading: promptsLoading, error: promptsError } = usePrompts();
  const { data: brandsData, loading: brandsLoading } = useBrands();

  // Auto-expand prompt from URL parameters
  useEffect(() => {
    const highlightId = searchParams.get('highlight');
    const queryText = searchParams.get('query');

    if (highlightId && prompts) {
      setExpandedId(highlightId);
      setSearchParams({}, { replace: true });
    } else if (queryText && prompts) {
      // Find prompt by query text and expand it
      const matchingPrompt = prompts.find(
        p => p.query.toLowerCase() === queryText.toLowerCase()
      );
      if (matchingPrompt) {
        setExpandedId(matchingPrompt.id);
      }
      setSearchParams({}, { replace: true });
    }
  }, [searchParams, prompts, setSearchParams]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      // Toggle between asc and desc
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDirection('asc');
    }
  };

  const brands: Brand[] = useMemo(() => {
    if (!brandsData) return [];
    return brandsData.map(b => ({ id: b.id, name: b.name, color: b.color }));
  }, [brandsData]);

  // Check if selected AI source has data (only AI Overview has data currently)
  const sourceHasData = selectedAISource === 'all' || selectedAISource === 'ai-overview';

  const filteredPrompts = useMemo(() => {
    // If source has no data, return empty array
    if (!sourceHasData) return [];
    if (!prompts) return [];

    let filtered = [...prompts];

    // Apply search filter
    if (searchQuery) {
      filtered = filtered.filter((p) =>
        p.query.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    // Apply sorting
    if (sortKey && sortDirection) {
      filtered.sort((a, b) => {
        const aVal = a[sortKey];
        const bVal = b[sortKey];

        if (aVal === bVal) return 0;
        if (aVal === null || aVal === undefined) return 1;
        if (bVal === null || bVal === undefined) return -1;

        const comparison = aVal < bVal ? -1 : 1;
        return sortDirection === 'asc' ? comparison : -comparison;
      });
    }

    // Move expanded prompt to top of list (after sorting)
    if (expandedId) {
      const expandedIndex = filtered.findIndex(p => p.id === expandedId);
      if (expandedIndex > 0) {
        const expandedPrompt = filtered[expandedIndex];
        filtered = [expandedPrompt, ...filtered.slice(0, expandedIndex), ...filtered.slice(expandedIndex + 1)];
      }
    }
    return filtered;
  }, [prompts, searchQuery, expandedId, sortKey, sortDirection, sourceHasData]);

  const toggleExpanded = (id: string) => {
    setExpandedId(expandedId === id ? null : id);
  };

  const isLoading = promptsLoading || brandsLoading;

  return (
    <div className="min-h-screen">
      <Header
        title="Prompts"
        subtitle="View brand mentions across AI-generated responses"
      />

      <div className="p-8">
        {/* AI Source Selector, Search and Add Button */}
        <div className="flex items-center justify-between gap-4 mb-6 animate-fade-in-up delay-100 relative z-[100]">
          <div className="flex items-center gap-4 flex-1">
            {/* AI Source Selector */}
            <AISourceSelector
              selectedSource={selectedAISource}
              onSourceChange={setSelectedAISource}
            />

            {/* Search Input */}
            <div className="relative max-w-md flex-1">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]" />
              <input
                type="text"
                placeholder="Search prompts..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="input-dark w-full pr-4 py-2.5 text-sm"
                style={{ paddingLeft: '2.5rem' }}
              />
            </div>
          </div>
          <div className="relative group/addprompt">
            <button
              className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-[var(--accent-primary)] text-white font-medium opacity-50 cursor-not-allowed"
            >
              <Plus className="w-4 h-4" />
              Add Prompt
            </button>
            <div className="absolute right-0 bottom-full mb-2 px-3 py-1.5 bg-[var(--bg-secondary)] border border-[var(--border-subtle)] rounded-lg text-xs text-[var(--text-muted)] whitespace-nowrap opacity-0 invisible group-hover/addprompt:opacity-100 group-hover/addprompt:visible transition-all duration-200 z-50 shadow-lg">
              Coming soon!
            </div>
          </div>
        </div>

        {/* Loading State */}
        {isLoading && <PromptsSkeleton />}

        {/* Error State */}
        {promptsError && (
          <div className="glass-card p-12 text-center animate-fade-in">
            <p className="text-red-400 mb-2">Failed to load data</p>
            <p className="text-sm text-[var(--text-muted)]">Make sure the backend is running at {config.apiHost}</p>
          </div>
        )}

        {/* Table */}
        {!isLoading && !promptsError && (
          <div className="glass-card overflow-hidden animate-fade-in-up delay-150 relative z-[10]">
            <div className="overflow-x-auto">
              <table className="table-dark">
                <thead>
                  <tr>
                    <th
                      onClick={() => handleSort('query')}
                      className="cursor-pointer select-none hover:text-[var(--text-primary)] transition-colors"
                    >
                      <div className="flex items-center gap-1">
                        <span>Query</span>
                        {sortKey === 'query' && sortDirection === 'asc' && <ChevronUp className="w-3 h-3 text-[var(--accent-primary)]" />}
                        {sortKey === 'query' && sortDirection === 'desc' && <ChevronDown className="w-3 h-3 text-[var(--accent-primary)]" />}
                        {sortKey !== 'query' && <ChevronUp className="w-3 h-3 opacity-30" />}
                      </div>
                    </th>
                    <th
                      onClick={() => handleSort('visibility')}
                      className="cursor-pointer select-none hover:text-[var(--text-primary)] transition-colors text-center"
                    >
                      <div className="flex items-center gap-1 justify-center">
                        <span>Visibility</span>
                        {sortKey === 'visibility' && sortDirection === 'asc' && <ChevronUp className="w-3 h-3 text-[var(--accent-primary)]" />}
                        {sortKey === 'visibility' && sortDirection === 'desc' && <ChevronDown className="w-3 h-3 text-[var(--accent-primary)]" />}
                        {sortKey !== 'visibility' && <ChevronUp className="w-3 h-3 opacity-30" />}
                      </div>
                    </th>
                    <th
                      onClick={() => handleSort('avgPosition')}
                      className="cursor-pointer select-none hover:text-[var(--text-primary)] transition-colors text-center"
                    >
                      <div className="flex items-center gap-1 justify-center">
                        <span>Avg Position</span>
                        {sortKey === 'avgPosition' && sortDirection === 'asc' && <ChevronUp className="w-3 h-3 text-[var(--accent-primary)]" />}
                        {sortKey === 'avgPosition' && sortDirection === 'desc' && <ChevronDown className="w-3 h-3 text-[var(--accent-primary)]" />}
                        {sortKey !== 'avgPosition' && <ChevronUp className="w-3 h-3 opacity-30" />}
                      </div>
                    </th>
                    <th
                      onClick={() => handleSort('totalMentions')}
                      className="cursor-pointer select-none hover:text-[var(--text-primary)] transition-colors text-center"
                    >
                      <div className="flex items-center gap-1 justify-center">
                        <span>Mentions</span>
                        {sortKey === 'totalMentions' && sortDirection === 'asc' && <ChevronUp className="w-3 h-3 text-[var(--accent-primary)]" />}
                        {sortKey === 'totalMentions' && sortDirection === 'desc' && <ChevronDown className="w-3 h-3 text-[var(--accent-primary)]" />}
                        {sortKey !== 'totalMentions' && <ChevronUp className="w-3 h-3 opacity-30" />}
                      </div>
                    </th>
                    <th
                      onClick={() => handleSort('totalRuns')}
                      className="cursor-pointer select-none hover:text-[var(--text-primary)] transition-colors text-center"
                    >
                      <div className="flex items-center gap-1 justify-center">
                        <span>Runs</span>
                        {sortKey === 'totalRuns' && sortDirection === 'asc' && <ChevronUp className="w-3 h-3 text-[var(--accent-primary)]" />}
                        {sortKey === 'totalRuns' && sortDirection === 'desc' && <ChevronDown className="w-3 h-3 text-[var(--accent-primary)]" />}
                        {sortKey !== 'totalRuns' && <ChevronUp className="w-3 h-3 opacity-30" />}
                      </div>
                    </th>
                    <th className="text-center">Brands</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredPrompts.map((prompt, index) => (
                    <PromptRow
                      key={prompt.id}
                      prompt={prompt}
                      isExpanded={expandedId === prompt.id}
                      onToggle={() => toggleExpanded(prompt.id)}
                      index={index}
                      brands={brands}
                    />
                  ))}
                </tbody>
              </table>

              {filteredPrompts.length === 0 && (
                <EmptyState
                  title={
                    !sourceHasData
                      ? `No data for ${selectedAISource === 'chatgpt' ? 'ChatGPT' : selectedAISource === 'claude' ? 'Claude' : selectedAISource === 'gemini' ? 'Gemini' : selectedAISource === 'perplexity' ? 'Perplexity' : selectedAISource}`
                      : searchQuery
                      ? "No prompts found"
                      : "No prompts yet"
                  }
                  description={
                    !sourceHasData
                      ? `Tracking for this AI source is coming soon. Currently only Google AI Overview data is available.`
                      : searchQuery
                      ? `No prompts matching "${searchQuery}"`
                      : "Run your first AI search analysis to see prompts here."
                  }
                />
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
