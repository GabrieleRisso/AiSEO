import { useState, useRef, useEffect } from 'react';
import { ChevronDown, Check } from 'lucide-react';
import { AI_SOURCES, AISourceIconRenderer, type AISource, type AISourceInfo } from './AISourceIcons';

interface AISourceSelectorProps {
  selectedSource: AISource;
  onSourceChange: (source: AISource) => void;
}

export function AISourceSelector({ selectedSource, onSourceChange }: AISourceSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const selectedSourceInfo = AI_SOURCES.find(s => s.id === selectedSource) || AI_SOURCES[0];

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (source: AISourceInfo) => {
    onSourceChange(source.id);
    setIsOpen(false);
  };

  return (
    <div className="relative z-[200]" ref={dropdownRef}>
      {/* Trigger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2.5 px-4 py-2.5 rounded-lg bg-[var(--bg-card)] border border-[var(--border-subtle)] hover:border-[var(--border-accent)] transition-all duration-200 min-w-[180px]"
      >
        <AISourceIconRenderer source={selectedSource} size={20} />
        <span className="text-sm font-medium text-[var(--text-primary)] flex-1 text-left">
          {selectedSourceInfo.name}
        </span>
        <ChevronDown
          className={`w-4 h-4 text-[var(--text-muted)] transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
        />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute top-full left-0 mt-2 w-full min-w-[220px] bg-[#171719] border border-[var(--border-subtle)] rounded-xl shadow-2xl overflow-visible z-[9999] animate-fade-in">
          <div className="py-1">
            {AI_SOURCES.map((source) => {
              const isSelected = source.id === selectedSource;
              const hasData = source.id === 'all' || source.id === 'ai-overview';

              return (
                <button
                  key={source.id}
                  onClick={() => handleSelect(source)}
                  className={`w-full flex items-center gap-3 px-4 py-3 text-left transition-colors duration-150 ${
                    isSelected
                      ? 'bg-[var(--accent-primary)]/10'
                      : 'hover:bg-[var(--bg-elevated)]'
                  }`}
                >
                  <AISourceIconRenderer source={source.id} size={20} />
                  <div className="flex-1 flex items-center gap-2">
                    <span className={`text-sm font-medium ${
                      isSelected ? 'text-[var(--accent-primary)]' : 'text-[var(--text-primary)]'
                    }`}>
                      {source.name}
                    </span>
                    {!hasData && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--bg-elevated)] text-[var(--text-muted)] border border-[var(--border-subtle)]">
                        No data
                      </span>
                    )}
                  </div>
                  {isSelected && (
                    <Check className="w-4 h-4 text-[var(--accent-primary)]" />
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
