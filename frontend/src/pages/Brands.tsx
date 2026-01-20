import { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router';
import {
  Loader2,
  Plus,
  Trash2,
  ChevronDown,
  ChevronRight,
  TrendingUp,
  TrendingDown,
  Minus,
  X,
  AlertCircle,
} from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, ResponsiveContainer, Tooltip } from 'recharts';
import { Header } from '../components/layout/Header';
import { useBrandsDetails } from '../hooks/useApi';
import { createBrand, type BrandCreateRequest } from '../api/client';
import type { BrandDetail } from '../types';

const TREND_ICONS = {
  up: TrendingUp,
  down: TrendingDown,
  stable: Minus,
};

const TREND_COLORS = {
  up: 'text-green-400',
  down: 'text-red-400',
  stable: 'text-gray-400',
};

const SENTIMENT_COLORS = {
  positive: { bg: 'rgba(34, 197, 94, 0.15)', text: '#22c55e' },
  neutral: { bg: 'rgba(148, 163, 184, 0.15)', text: '#94a3b8' },
  negative: { bg: 'rgba(239, 68, 68, 0.15)', text: '#ef4444' },
};

interface AddBrandModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAdd: (brand: BrandCreateRequest) => Promise<void>;
}

function AddBrandModal({ isOpen, onClose, onAdd }: AddBrandModalProps) {
  const [name, setName] = useState('');
  const [id, setId] = useState('');
  const [color, setColor] = useState('#8b5cf6');
  const [type, setType] = useState<'primary' | 'competitor'>('competitor');
  const [variations, setVariations] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleNameChange = (value: string) => {
    setName(value);
    setId(value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/-+$/, ''));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const variationsList = variations
        .split(',')
        .map((v) => v.trim())
        .filter((v) => v.length > 0);

      if (variationsList.length === 0) {
        variationsList.push(name);
      }

      await onAdd({
        id,
        name,
        type,
        color,
        variations: variationsList,
      });

      setName('');
      setId('');
      setColor('#8b5cf6');
      setType('competitor');
      setVariations('');
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add brand');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="glass-card w-full max-w-md p-6 m-4 animate-fade-in-up">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-[var(--text-primary)]">Add New Brand</h2>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--glass-bg)] transition-all"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {error && (
          <div className="flex items-center gap-2 p-3 mb-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400">
            <AlertCircle className="w-4 h-4" />
            <span className="text-sm">{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-2">
              Brand Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => handleNameChange(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg bg-[var(--bg-tertiary)] border border-[var(--border-subtle)] text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-[var(--accent-primary)] transition-colors"
              placeholder="e.g., Adobe Commerce"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-2">
              Brand ID
            </label>
            <input
              type="text"
              value={id}
              onChange={(e) => setId(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg bg-[var(--bg-tertiary)] border border-[var(--border-subtle)] text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-[var(--accent-primary)] transition-colors font-mono text-sm"
              placeholder="e.g., adobe-commerce"
              required
            />
            <p className="text-xs text-[var(--text-muted)] mt-1">
              Lowercase, no spaces. Auto-generated from name.
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-[var(--text-secondary)] mb-2">
              Search Variations
            </label>
            <input
              type="text"
              value={variations}
              onChange={(e) => setVariations(e.target.value)}
              className="w-full px-4 py-2.5 rounded-lg bg-[var(--bg-tertiary)] border border-[var(--border-subtle)] text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-[var(--accent-primary)] transition-colors"
              placeholder="e.g., Adobe Commerce, Magento, magento.com"
            />
            <p className="text-xs text-[var(--text-muted)] mt-1">
              Comma-separated terms to search in AI responses.
            </p>
          </div>

          <div className="flex gap-4">
            <div className="flex-1">
              <label className="block text-sm font-medium text-[var(--text-secondary)] mb-2">
                Type
              </label>
              <select
                value={type}
                onChange={(e) => setType(e.target.value as 'primary' | 'competitor')}
                className="w-full px-4 py-2.5 rounded-lg bg-[var(--bg-tertiary)] border border-[var(--border-subtle)] text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent-primary)] transition-colors"
              >
                <option value="competitor">Competitor</option>
                <option value="primary">Primary</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-[var(--text-secondary)] mb-2">
                Color
              </label>
              <input
                type="color"
                value={color}
                onChange={(e) => setColor(e.target.value)}
                className="w-12 h-10 rounded-lg cursor-pointer border border-[var(--border-subtle)]"
              />
            </div>
          </div>

          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2.5 rounded-lg border border-[var(--border-subtle)] text-[var(--text-secondary)] hover:bg-[var(--glass-bg)] transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !name || !id}
              className="flex-1 px-4 py-2.5 rounded-lg bg-[var(--accent-primary)] text-white font-medium hover:bg-[var(--accent-primary)]/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Adding...
                </>
              ) : (
                <>
                  <Plus className="w-4 h-4" />
                  Add Brand
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

interface BrandRowProps {
  brand: BrandDetail;
  isExpanded: boolean;
  onToggle: () => void;
}

function BrandRow({ brand, isExpanded, onToggle }: BrandRowProps) {
  const TrendIcon = TREND_ICONS[brand.trend];
  const trendColor = TREND_COLORS[brand.trend];
  const sentimentStyle = SENTIMENT_COLORS[brand.sentiment as keyof typeof SENTIMENT_COLORS] || SENTIMENT_COLORS.neutral;

  return (
    <>
      <tr
        className="border-b border-[var(--border-subtle)] hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer"
        onClick={onToggle}
      >
        <td className="py-4 px-4">
          {brand.topPrompts.length > 0 ? (
            isExpanded ? (
              <ChevronDown className="w-4 h-4 text-[var(--text-muted)]" />
            ) : (
              <ChevronRight className="w-4 h-4 text-[var(--text-muted)]" />
            )
          ) : (
            <span className="w-4 h-4 block" />
          )}
        </td>
        <td className="py-4 px-4">
          <div className="flex items-center gap-3">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: brand.color, boxShadow: `0 0 8px ${brand.color}40` }}
            />
            <div>
              <span className="font-medium text-[var(--text-primary)]">{brand.name}</span>
              {brand.type === 'primary' && (
                <span className="ml-2 text-xs px-2 py-0.5 rounded-full bg-[var(--accent-primary)]/20 text-[var(--accent-primary)]">
                  You
                </span>
              )}
            </div>
          </div>
        </td>
        <td className="py-4 px-4 text-center">
          <span className="text-data font-semibold">{brand.visibility}%</span>
        </td>
        <td className="py-4 px-4 text-center">
          <span className="text-[var(--text-secondary)] font-mono">
            {brand.avgPosition > 0 ? `#${brand.avgPosition.toFixed(1)}` : '-'}
          </span>
        </td>
        <td className="py-4 px-4 text-center">
          <TrendIcon className={`w-4 h-4 mx-auto ${trendColor}`} />
        </td>
        <td className="py-4 px-4 text-center">
          <span className="text-[var(--text-secondary)]">{brand.totalMentions}</span>
        </td>
        <td className="py-4 px-4 text-center">
          <span
            className="px-2 py-1 rounded-md text-xs font-medium capitalize"
            style={{ backgroundColor: sentimentStyle.bg, color: sentimentStyle.text }}
          >
            {brand.sentiment}
          </span>
        </td>
        <td className="py-4 px-4 text-center">
          {brand.type !== 'primary' && (
            <div className="relative group inline-block">
              <button
                className="p-2 rounded-lg text-[var(--text-muted)] cursor-not-allowed opacity-50"
              >
                <Trash2 className="w-4 h-4" />
              </button>
              <div className="absolute right-0 top-full mt-2 px-3 py-1.5 bg-[var(--bg-secondary)] border border-[var(--border-subtle)] rounded-lg text-xs text-[var(--text-muted)] whitespace-nowrap opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-10">
                Hands off my database!
              </div>
            </div>
          )}
        </td>
      </tr>
      {isExpanded && (
        <tr>
          <td colSpan={8} className="bg-[var(--bg-tertiary)] px-8 py-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Top Prompts */}
              <div>
                <h4 className="text-sm font-medium text-[var(--text-muted)] uppercase tracking-wide mb-3">
                  Top Prompts for {brand.name}
                </h4>
                <div className="space-y-2">
                  {brand.topPrompts.slice(0, 5).map((prompt, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between p-3 rounded-lg bg-[var(--bg-secondary)]"
                    >
                      <Link
                        to={`/prompts?query=${encodeURIComponent(prompt.query)}`}
                        onClick={(e) => e.stopPropagation()}
                        className="text-[var(--text-secondary)] text-sm flex-1 truncate mr-4 hover:text-[var(--accent-primary)] transition-colors"
                      >
                        "{prompt.query}"
                      </Link>
                      <div className="flex items-center gap-3">
                        {prompt.position && (
                          <span className="text-xs font-mono text-[var(--text-muted)]">
                            #{prompt.position}
                          </span>
                        )}
                        {prompt.sentiment && (
                          <span
                            className="text-xs px-2 py-0.5 rounded capitalize"
                            style={{
                              backgroundColor: SENTIMENT_COLORS[prompt.sentiment as keyof typeof SENTIMENT_COLORS]?.bg || SENTIMENT_COLORS.neutral.bg,
                              color: SENTIMENT_COLORS[prompt.sentiment as keyof typeof SENTIMENT_COLORS]?.text || SENTIMENT_COLORS.neutral.text,
                            }}
                          >
                            {prompt.sentiment}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                  {brand.topPrompts.length === 0 && (
                    <p className="text-[var(--text-muted)] text-sm">No prompts found</p>
                  )}
                </div>
              </div>

              {/* Visibility Trend Mini Chart */}
              <div>
                <h4 className="text-sm font-medium text-[var(--text-muted)] uppercase tracking-wide mb-3">
                  Visibility Trend
                </h4>
                <div className="h-40 bg-[var(--bg-secondary)] rounded-lg p-4">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={brand.visibilityByMonth}>
                      <defs>
                        <linearGradient id={`gradient-${brand.id}`} x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor={brand.color} stopOpacity={0.3} />
                          <stop offset="100%" stopColor={brand.color} stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <XAxis
                        dataKey="month"
                        tick={{ fill: '#94a3b8', fontSize: 10 }}
                        tickLine={false}
                        axisLine={false}
                      />
                      <YAxis
                        domain={[0, 100]}
                        tick={{ fill: '#94a3b8', fontSize: 10 }}
                        tickLine={false}
                        axisLine={false}
                        tickFormatter={(v) => `${v}%`}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#1a1f2e',
                          border: '1px solid rgba(255, 255, 255, 0.1)',
                          borderRadius: '8px',
                        }}
                        itemStyle={{ color: '#e2e8f0' }}
                        formatter={(value: number) => [`${value}%`, 'Visibility']}
                      />
                      <Area
                        type="monotone"
                        dataKey="visibility"
                        stroke={brand.color}
                        strokeWidth={2}
                        fill={`url(#gradient-${brand.id})`}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
                <div className="mt-3 flex items-center gap-2 text-xs text-[var(--text-muted)]">
                  <span>Variations:</span>
                  {brand.variations.map((v, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-0.5 rounded-full bg-[var(--bg-secondary)] text-[var(--text-secondary)]"
                    >
                      {v}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

export function Brands() {
  const { data, loading, error, refetch } = useBrandsDetails();
  const [searchParams] = useSearchParams();
  const [expandedBrands, setExpandedBrands] = useState<Set<string>>(new Set());
  const [showAddModal, setShowAddModal] = useState(false);

  // Auto-expand selected brand from query param
  useEffect(() => {
    const selected = searchParams.get('selected');
    if (selected && data?.brands.some((b) => b.id === selected)) {
      setExpandedBrands(new Set([selected]));
    }
  }, [searchParams, data]);

  const toggleBrand = (brandId: string) => {
    setExpandedBrands((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(brandId)) {
        newSet.delete(brandId);
      } else {
        newSet.add(brandId);
      }
      return newSet;
    });
  };

  const handleAddBrand = async (brandData: BrandCreateRequest) => {
    await createBrand(brandData);
    refetch();
  };

  if (loading) {
    return (
      <div className="min-h-screen">
        <Header title="Brand Management" subtitle="Track and manage brands in AI responses" />
        <div className="p-8 flex items-center justify-center">
          <div className="text-center">
            <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4 text-[var(--accent-primary)]" />
            <p className="text-[var(--text-muted)]">Loading brands data...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen">
        <Header title="Brand Management" subtitle="Track and manage brands in AI responses" />
        <div className="p-8">
          <div className="glass-card p-12 text-center">
            <p className="text-red-400 mb-2">Failed to load brands data</p>
            <p className="text-sm text-[var(--text-muted)]">
              Make sure the backend is running at localhost:8000
            </p>
          </div>
        </div>
      </div>
    );
  }

  const totalBrands = data.brands.length;

  return (
    <div className="min-h-screen">
      <Header title="Brand Management" subtitle="Track and manage brands in AI responses" />

      <div className="p-4 md:p-8">
        {/* Add Brand Button */}
        <div className="flex justify-end mb-6">
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-[var(--accent-primary)] text-white font-medium hover:bg-[var(--accent-primary)]/90 transition-colors"
          >
            <Plus className="w-4 h-4" />
            Add Brand
          </button>
        </div>

        {/* Brands Table */}
        <div
          className="glass-card p-6 animate-fade-in-up"
          style={{ animationDelay: '450ms' }}
        >
          <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-6">
            All Brands ({totalBrands})
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-[var(--border-subtle)]">
                  <th className="text-left text-sm font-medium text-[var(--text-muted)] pb-3 w-8"></th>
                  <th className="text-left text-sm font-medium text-[var(--text-muted)] pb-3">
                    Brand
                  </th>
                  <th className="text-center text-sm font-medium text-[var(--text-muted)] pb-3">
                    Visibility
                  </th>
                  <th className="text-center text-sm font-medium text-[var(--text-muted)] pb-3">
                    Avg. Position
                  </th>
                  <th className="text-center text-sm font-medium text-[var(--text-muted)] pb-3">
                    Trend
                  </th>
                  <th className="text-center text-sm font-medium text-[var(--text-muted)] pb-3">
                    Mentions
                  </th>
                  <th className="text-center text-sm font-medium text-[var(--text-muted)] pb-3">
                    Sentiment
                  </th>
                  <th className="text-center text-sm font-medium text-[var(--text-muted)] pb-3 w-16"></th>
                </tr>
              </thead>
              <tbody>
                {data.brands.map((brand) => (
                  <BrandRow
                    key={brand.id}
                    brand={brand}
                    isExpanded={expandedBrands.has(brand.id)}
                    onToggle={() => toggleBrand(brand.id)}
                  />
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Info Note */}
        <div
          className="glass-card p-6 mt-8 text-center animate-fade-in-up"
          style={{ animationDelay: '600ms' }}
        >
          <p className="text-[var(--text-muted)] text-sm">
            Add new brands to track their mentions in AI responses. The system will automatically
            scan existing prompts and highlight mentions based on the search variations you provide.
          </p>
        </div>
      </div>

      {/* Add Brand Modal */}
      <AddBrandModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onAdd={handleAddBrand}
      />
    </div>
  );
}
