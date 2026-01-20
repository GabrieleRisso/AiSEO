import { useState, useMemo, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router';
import { Globe, Database, Link2, BarChart3, Loader2, ChevronDown, ChevronRight, ExternalLink } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { Header } from '../components/layout/Header';
import { MetricCard } from '../components/ui/MetricCard';
import { useSourcesAnalytics } from '../hooks/useApi';

const TYPE_COLORS: Record<string, string> = {
  brand: '#f59e0b',
  blog: '#06b6d4',
  community: '#8b5cf6',
  news: '#ec4899',
  review: '#10b981',
  other: '#6b7280',
};

const TYPE_LABELS: Record<string, string> = {
  brand: 'Brand Sites',
  blog: 'Blog Posts',
  community: 'Community',
  news: 'News/Media',
  review: 'Review Sites',
  other: 'Other',
};

interface ExpandedSources {
  [key: number]: boolean;
}

export function Sources() {
  const { data, loading, error } = useSourcesAnalytics();
  const [searchParams] = useSearchParams();
  const [expandedSources, setExpandedSources] = useState<ExpandedSources>({});
  const sourceRefs = useRef<{ [key: number]: HTMLTableRowElement | null }>({});
  const hasScrolledRef = useRef(false);

  const chartData = useMemo(() => {
    if (!data?.sourceTypes) return [];
    return data.sourceTypes.map(st => ({
      name: TYPE_LABELS[st.type] || st.type,
      value: st.count,
      percentage: st.percentage,
      color: TYPE_COLORS[st.type] || TYPE_COLORS.other,
    }));
  }, [data]);

  // Auto-expand and scroll to selected domain from query param
  useEffect(() => {
    const selectedDomain = searchParams.get('domain');
    if (selectedDomain && data?.topSources && !hasScrolledRef.current) {
      const source = data.topSources.find(
        (s) => s.domain.toLowerCase() === selectedDomain.toLowerCase()
      );
      if (source) {
        setExpandedSources({ [source.id]: true });
        // Scroll to the row after a short delay to let the DOM update
        setTimeout(() => {
          const row = sourceRefs.current[source.id];
          if (row) {
            row.scrollIntoView({ behavior: 'smooth', block: 'center' });
            // Add highlight animation
            row.classList.add('ring-2', 'ring-[var(--accent-primary)]');
            setTimeout(() => {
              row.classList.remove('ring-2', 'ring-[var(--accent-primary)]');
            }, 2000);
          }
        }, 100);
        hasScrolledRef.current = true;
      }
    }
  }, [searchParams, data]);

  const toggleSource = (id: number) => {
    setExpandedSources(prev => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  if (loading) {
    return (
      <div className="min-h-screen">
        <Header
          title="Sources Analytics"
          subtitle="Analyze citation sources from AI responses"
        />
        <div className="p-8 flex items-center justify-center">
          <div className="text-center">
            <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4 text-[var(--accent-primary)]" />
            <p className="text-[var(--text-muted)]">Loading sources data...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen">
        <Header
          title="Sources Analytics"
          subtitle="Analyze citation sources from AI responses"
        />
        <div className="p-8">
          <div className="glass-card p-12 text-center">
            <p className="text-red-400 mb-2">Failed to load sources data</p>
            <p className="text-sm text-[var(--text-muted)]">Make sure the backend is running at localhost:8000</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <Header
        title="Sources Analytics"
        subtitle="Analyze citation sources from AI responses"
      />

      <div className="p-4 md:p-8">
        {/* Summary Metrics */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6 mb-8">
          <MetricCard
            label="Total Sources"
            value={data.summary.totalSources}
            icon={Globe}
            delay={250}
          />
          <MetricCard
            label="Unique Domains"
            value={data.summary.totalDomains}
            icon={Database}
            delay={300}
          />
          <MetricCard
            label="Total Citations"
            value={data.summary.totalCitations}
            icon={Link2}
            delay={350}
          />
          <MetricCard
            label="Avg Citations/Source"
            value={data.summary.avgCitationsPerSource.toFixed(1)}
            icon={BarChart3}
            delay={400}
          />
        </div>

        {/* Two Column Layout: Chart + Top Domains */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 md:gap-8 mb-8">
          {/* Source Types Chart */}
          <div className="glass-card p-6 animate-fade-in-up" style={{ animationDelay: '450ms' }}>
            <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-6">
              Source Types Distribution
            </h3>
            <div className="flex flex-col items-center">
              <div className="w-64 h-64 mb-6">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={chartData}
                      cx="50%"
                      cy="50%"
                      innerRadius={70}
                      outerRadius={110}
                      paddingAngle={2}
                      dataKey="value"
                      nameKey="name"
                    >
                      {chartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1a1f2e',
                        border: '1px solid rgba(255, 255, 255, 0.1)',
                        borderRadius: '8px',
                      }}
                      itemStyle={{
                        color: '#e2e8f0',
                      }}
                      formatter={(value, name) => [`${value} sources`, name]}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="w-full space-y-3">
                {chartData.map((item, idx) => (
                  <div key={idx} className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: item.color }}
                      />
                      <span className="text-[var(--text-secondary)]">{item.name}</span>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className="text-[var(--text-muted)] text-sm">{item.value}</span>
                      <span className="text-data font-medium w-12 text-right">{item.percentage}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Top Domains Table */}
          <div className="glass-card p-6 animate-fade-in-up" style={{ animationDelay: '500ms' }}>
            <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-6">
              Top Domains by Citations
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-[var(--border-subtle)]">
                    <th className="text-left text-sm font-medium text-[var(--text-muted)] pb-3">Domain</th>
                    <th className="text-center text-sm font-medium text-[var(--text-muted)] pb-3">Citations</th>
                    <th className="text-center text-sm font-medium text-[var(--text-muted)] pb-3">Share</th>
                    <th className="text-center text-sm font-medium text-[var(--text-muted)] pb-3">Type</th>
                  </tr>
                </thead>
                <tbody>
                  {data.domainBreakdown.slice(0, 10).map((domain) => (
                    <tr
                      key={domain.domain}
                      className="border-b border-[var(--border-subtle)] last:border-0 hover:bg-[var(--bg-tertiary)] transition-colors"
                    >
                      <td className="py-3">
                        <div className="flex items-center gap-2">
                          <Globe className="w-4 h-4 text-[var(--accent-primary)]" />
                          <span className="font-medium text-[var(--text-primary)]">{domain.domain}</span>
                        </div>
                      </td>
                      <td className="py-3 text-center">
                        <span className="text-data">{domain.citations}</span>
                      </td>
                      <td className="py-3 text-center">
                        <div className="flex items-center justify-center gap-2">
                          <div className="progress-bar w-16">
                            <div
                              className="progress-bar-fill"
                              style={{ width: `${Math.min(domain.percentage * 10, 100)}%` }}
                            />
                          </div>
                          <span className="text-sm text-[var(--text-muted)]">{domain.percentage}%</span>
                        </div>
                      </td>
                      <td className="py-3 text-center">
                        <span
                          className="px-2 py-1 rounded-md text-xs font-medium capitalize"
                          style={{
                            backgroundColor: `${TYPE_COLORS[domain.type] || TYPE_COLORS.other}20`,
                            color: TYPE_COLORS[domain.type] || TYPE_COLORS.other,
                          }}
                        >
                          {TYPE_LABELS[domain.type] || domain.type}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Full Sources Table */}
        <div className="glass-card p-6 animate-fade-in-up" style={{ animationDelay: '550ms' }}>
          <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-6">
            All Sources ({data.topSources.length})
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-[var(--border-subtle)]">
                  <th className="text-left text-sm font-medium text-[var(--text-muted)] pb-3 w-8"></th>
                  <th className="text-left text-sm font-medium text-[var(--text-muted)] pb-3">Source</th>
                  <th className="text-left text-sm font-medium text-[var(--text-muted)] pb-3">Title</th>
                  <th className="text-center text-sm font-medium text-[var(--text-muted)] pb-3">Citations</th>
                  <th className="text-center text-sm font-medium text-[var(--text-muted)] pb-3">Prompts</th>
                </tr>
              </thead>
              <tbody>
                {data.topSources.map((source) => (
                  <>
                    <tr
                      key={source.id}
                      ref={(el) => { sourceRefs.current[source.id] = el; }}
                      className="border-b border-[var(--border-subtle)] hover:bg-[var(--bg-tertiary)] transition-all cursor-pointer"
                      onClick={() => toggleSource(source.id)}
                    >
                      <td className="py-3">
                        {source.prompts.length > 0 && (
                          expandedSources[source.id] ? (
                            <ChevronDown className="w-4 h-4 text-[var(--text-muted)]" />
                          ) : (
                            <ChevronRight className="w-4 h-4 text-[var(--text-muted)]" />
                          )
                        )}
                      </td>
                      <td className="py-3">
                        <div className="flex items-center gap-2">
                          <Globe className="w-4 h-4 text-[var(--accent-primary)] flex-shrink-0" />
                          <span className="font-medium text-[var(--text-primary)]">{source.domain}</span>
                          <a
                            href={source.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="text-[var(--accent-primary)] hover:text-[var(--accent-secondary)] transition-colors"
                          >
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        </div>
                      </td>
                      <td className="py-3">
                        <span className="text-[var(--text-secondary)] text-sm truncate max-w-xs block">
                          {source.title || '-'}
                        </span>
                      </td>
                      <td className="py-3 text-center">
                        <span className="text-data">{source.citations}</span>
                      </td>
                      <td className="py-3 text-center">
                        <span className="text-[var(--text-muted)]">{source.prompts.length}</span>
                      </td>
                    </tr>
                    {expandedSources[source.id] && source.prompts.length > 0 && (
                      <tr key={`${source.id}-expanded`}>
                        <td colSpan={5} className="bg-[var(--bg-tertiary)] px-8 py-4">
                          <div className="text-sm">
                            <span className="text-[var(--text-muted)] mb-2 block">Appears in prompts:</span>
                            <ul className="space-y-1">
                              {source.prompts.map((prompt, idx) => (
                                <li key={idx} className="text-[var(--text-secondary)] flex items-start gap-2">
                                  <span className="text-[var(--accent-primary)]">•</span>
                                  <span>"{prompt}"</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
