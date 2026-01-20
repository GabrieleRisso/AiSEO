import { useMemo } from 'react';
import { Link } from 'react-router';
import { Eye, FileText, Globe, Hash, Loader2, ChevronRight } from 'lucide-react';
import { Header } from '../components/layout/Header';
import { MetricCard } from '../components/ui/MetricCard';
import { DataTable } from '../components/ui/DataTable';
import { TrendBadge, SentimentBadge } from '../components/ui/Badge';
import { VisibilityChart } from '../components/charts/VisibilityChart';
import { useBrands, useSources, useMetrics, useVisibilityData } from '../hooks/useApi';
import type { DailyVisibility } from '../types';

interface Brand {
  id: string;
  name: string;
  type: 'primary' | 'competitor';
  visibility: number;
  trend: 'up' | 'down' | 'stable';
  sentiment: 'positive' | 'neutral' | 'negative';
  avgPosition: number;
  color: string;
}

interface Source {
  domain: string;
  usage: number;
  avgCitations: number;
}

const brandColumns = [
  {
    key: 'name',
    header: 'Brand',
    sortable: true,
    render: (brand: Brand) => (
      <Link
        to={`/brands?selected=${brand.id}`}
        className="flex items-center gap-3 hover:opacity-80 transition-opacity"
      >
        <div
          className="w-3 h-3 rounded-full ring-2 ring-[var(--bg-primary)]"
          style={{ backgroundColor: brand.color, boxShadow: `0 0 8px ${brand.color}40` }}
        />
        <span className="font-medium text-[var(--text-primary)] hover:text-[var(--accent-primary)] transition-colors">{brand.name}</span>
        {brand.type === 'primary' && (
          <span className="badge-glow badge-primary text-[10px] px-2 py-0.5 rounded-md">
            You
          </span>
        )}
      </Link>
    ),
  },
  {
    key: 'visibility',
    header: 'Visibility',
    align: 'center' as const,
    sortable: true,
    render: (brand: Brand) => (
      <span className="text-data">{brand.visibility}%</span>
    ),
  },
  {
    key: 'trend',
    header: 'Trend',
    render: (brand: Brand) => <TrendBadge trend={brand.trend} />,
  },
  {
    key: 'sentiment',
    header: 'Sentiment',
    render: (brand: Brand) => <SentimentBadge sentiment={brand.sentiment} />,
  },
  {
    key: 'avgPosition',
    header: 'Avg Position',
    align: 'center' as const,
    sortable: true,
    render: (brand: Brand) => (
      <span className="text-[var(--text-secondary)] font-mono">#{brand.avgPosition.toFixed(1)}</span>
    ),
  },
];

const sourceColumns = [
  {
    key: 'domain',
    header: 'Source',
    sortable: true,
    render: (source: Source) => (
      <Link
        to={`/sources?domain=${encodeURIComponent(source.domain)}`}
        className="flex items-center gap-2 hover:opacity-80 transition-opacity"
      >
        <Globe className="w-4 h-4 text-[var(--accent-primary)]" />
        <span className="font-medium text-[var(--text-primary)] hover:text-[var(--accent-primary)] transition-colors">{source.domain}</span>
      </Link>
    ),
  },
  {
    key: 'usage',
    header: 'Usage',
    sortable: true,
    render: (source: Source) => (
      <div className="flex items-center gap-3">
        <div className="progress-bar w-24">
          <div
            className="progress-bar-fill"
            style={{ width: `${source.usage}%` }}
          />
        </div>
        <span className="text-sm font-mono text-[var(--text-secondary)]">{source.usage}%</span>
      </div>
    ),
  },
  {
    key: 'avgCitations',
    header: 'Avg Citations',
    align: 'center' as const,
    sortable: true,
    render: (source: Source) => (
      <span className="text-[var(--text-secondary)] font-mono">{source.avgCitations.toFixed(1)}</span>
    ),
  },
];

export function Dashboard() {
  // Fetch real data from API
  const { data: brandsData, loading: brandsLoading, error: brandsError } = useBrands();
  const { data: sourcesData, loading: sourcesLoading } = useSources();
  const { data: metricsData, loading: metricsLoading } = useMetrics();
  const { data: visibilityData, loading: visibilityLoading } = useVisibilityData();

  // Transform API data to match component expectations
  const brands: Brand[] = useMemo(() => {
    if (!brandsData) return [];
    return brandsData.map(b => ({
      id: b.id,
      name: b.name,
      type: b.type as 'primary' | 'competitor',
      visibility: b.visibility,
      trend: b.trend as 'up' | 'down' | 'stable',
      sentiment: b.sentiment as 'positive' | 'neutral' | 'negative',
      avgPosition: b.avgPosition,
      color: b.color,
    }));
  }, [brandsData]);

  const sources: Source[] = useMemo(() => {
    if (!sourcesData) return [];
    return sourcesData.map(s => ({
      domain: s.domain,
      usage: s.usage,
      avgCitations: s.avgCitations,
    }));
  }, [sourcesData]);

  const chartData: DailyVisibility[] = useMemo(() => {
    if (!visibilityData) return [];
    return visibilityData.map(d => ({
      date: d.date,
      shopify: d.shopify ?? 0,
      woocommerce: d.woocommerce ?? 0,
      bigcommerce: d.bigcommerce ?? 0,
      wix: d.wix ?? 0,
      squarespace: d.squarespace ?? 0,
    }));
  }, [visibilityData]);

  const isLoading = brandsLoading || sourcesLoading || metricsLoading || visibilityLoading;

  if (isLoading) {
    return (
      <div className="min-h-screen">
        <Header
          title="Dashboard"
          subtitle="Track how AI search engines cite your brand vs competitors"
        />
        <div className="p-8 flex items-center justify-center">
          <div className="text-center">
            <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4 text-[var(--accent-primary)]" />
            <p className="text-[var(--text-muted)]">Loading dashboard data...</p>
          </div>
        </div>
      </div>
    );
  }

  if (brandsError) {
    return (
      <div className="min-h-screen">
        <Header
          title="Dashboard"
          subtitle="Track how AI search engines cite your brand vs competitors"
        />
        <div className="p-8">
          <div className="glass-card p-12 text-center">
            <p className="text-red-400 mb-2">Failed to load data</p>
            <p className="text-sm text-[var(--text-muted)]">Make sure the backend is running at localhost:8000</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <Header
        title="Dashboard"
        subtitle="Track how AI search engines cite your brand vs competitors"
      />

      <div className="p-4 md:p-8">
        {/* Metric Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6 mb-8">
          <MetricCard
            label="Brand Visibility"
            value={`${metricsData?.visibility.value ?? 0}%`}
            change={metricsData?.visibility.change ?? 0}
            changeLabel="%"
            icon={Eye}
            delay={250}
          />
          <MetricCard
            label="Prompts Tracked"
            value={metricsData?.totalPrompts.value ?? 0}
            icon={FileText}
            delay={300}
            linkTo="/prompts"
            linkLabel="View Prompts"
          />
          <MetricCard
            label="Sources Cited"
            value={metricsData?.totalSources.value ?? 0}
            icon={Globe}
            delay={350}
            secondaryValue={metricsData?.totalSources.total ?? 0}
            secondaryLabel="total"
          />
          <MetricCard
            label="Avg Position"
            value={`#${metricsData?.avgPosition.value ?? 0}`}
            change={metricsData?.avgPosition.change ?? 0}
            icon={Hash}
            delay={400}
          />
        </div>

        {/* Visibility Chart */}
        <div className="mb-8">
          <VisibilityChart
            data={chartData}
            brands={brands}
            animationDelay={500}
          />
        </div>

        {/* Data Tables */}
        <div className="grid grid-cols-1 2xl:grid-cols-2 gap-6 md:gap-8">
          <div>
            <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-4 animate-fade-in-up" style={{ animationDelay: '700ms' }}>
              Top Brands
            </h3>
            <DataTable
              columns={brandColumns}
              data={brands}
              keyExtractor={(brand) => brand.id}
              animationDelay={750}
              isPinned={(brand) => brand.type === 'primary'}
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-4 animate-fade-in-up" style={{ animationDelay: '800ms' }}>
              <h3 className="text-lg font-semibold text-[var(--text-primary)]">
                Top Sources
              </h3>
              <Link
                to="/sources"
                className="flex items-center gap-1 text-sm text-[var(--accent-primary)] hover:text-[var(--accent-secondary)] transition-colors"
              >
                <span>View All</span>
                <ChevronRight className="w-4 h-4" />
              </Link>
            </div>
            <DataTable
              columns={sourceColumns}
              data={sources.slice(0, 5)}
              keyExtractor={(source) => source.domain}
              animationDelay={850}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
