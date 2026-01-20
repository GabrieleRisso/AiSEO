import { NavLink } from 'react-router';
import { LayoutDashboard, MessageSquareText, Globe, Tag, Lightbulb, Settings, X, ChevronLeft, ChevronRight } from 'lucide-react';

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/prompts', icon: MessageSquareText, label: 'Prompts' },
  { to: '/sources', icon: Globe, label: 'Sources' },
  { to: '/brands', icon: Tag, label: 'Brands' },
  { to: '/suggestions', icon: Lightbulb, label: 'Suggestions' },
];

interface SidebarProps {
  variant?: 'static' | 'overlay';
  isOpen?: boolean;
  onClose?: () => void;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

export function Sidebar({
  variant = 'static',
  isOpen = true,
  onClose,
  isCollapsed = false,
  onToggleCollapse
}: SidebarProps) {
  const isOverlay = variant === 'overlay';

  const sidebarClasses = [
    'sticky top-0 h-screen flex flex-col border-r border-[var(--border-subtle)] bg-[var(--bg-secondary)]/95 backdrop-blur-xl transition-all duration-300 ease-out overflow-y-auto',
    isCollapsed ? 'w-16' : 'w-64',
    isOverlay && 'fixed top-0 left-0 z-50 transform shadow-2xl',
    isOverlay && !isOpen && '-translate-x-full',
    isOverlay && isOpen && 'translate-x-0',
    !isOverlay && !isCollapsed && 'animate-slide-in-left',
  ].filter(Boolean).join(' ');

  return (
    <aside className={sidebarClasses}>
      {/* Logo Section with Collapse Button */}
      <div className={`p-4 border-b border-[var(--border-subtle)] flex items-center ${isCollapsed ? 'justify-center' : 'justify-between'}`}>
        <div className={`flex items-center ${isCollapsed ? '' : 'gap-3'}`}>
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[var(--accent-primary)] to-[var(--accent-secondary)] flex items-center justify-center animate-pulse-glow flex-shrink-0">
            <span className="text-white font-bold text-sm tracking-tight">Wix</span>
          </div>
          {!isCollapsed && (
            <div className="flex flex-col">
              <span className="font-semibold text-[var(--text-primary)] text-base tracking-tight">SEO Tracker</span>
              <span className="text-[10px] text-[var(--text-muted)] uppercase tracking-wider">Analytics</span>
            </div>
          )}
        </div>

        {/* Collapse button at top for desktop */}
        {!isOverlay && onToggleCollapse && !isCollapsed && (
          <button
            onClick={onToggleCollapse}
            className="p-2 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--glass-bg)] transition-all"
            title="Collapse sidebar"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>
        )}

        {/* Close button for overlay mode */}
        {isOverlay && (
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--glass-bg)] transition-all"
            aria-label="Close navigation menu"
          >
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* Expand button when collapsed */}
      {!isOverlay && onToggleCollapse && isCollapsed && (
        <div className="p-2">
          <button
            onClick={onToggleCollapse}
            className="sidebar-nav-item w-full justify-center px-3"
            title="Expand sidebar"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      )}

      {/* Navigation */}
      <nav className="p-2">
        <ul className="space-y-1">
          {navItems.map((item, index) => (
            <li key={item.to} className="animate-fade-in-up" style={{ animationDelay: `${150 + index * 50}ms` }}>
              <NavLink
                to={item.to}
                onClick={isOverlay ? onClose : undefined}
                className={({ isActive }) =>
                  `sidebar-nav-item ${isActive ? 'active' : ''} ${isCollapsed ? 'justify-center px-3' : ''}`
                }
                title={isCollapsed ? item.label : undefined}
              >
                <item.icon className="w-5 h-5 flex-shrink-0" />
                {!isCollapsed && item.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      {/* Settings - below navigation with separator */}
      <div className="p-2 border-t border-[var(--border-subtle)]">
        <NavLink
          to="/settings"
          onClick={isOverlay ? onClose : undefined}
          className={({ isActive }) =>
            `sidebar-nav-item w-full ${isActive ? 'active' : ''} ${isCollapsed ? 'justify-center px-3' : ''}`
          }
          title={isCollapsed ? 'Settings' : undefined}
        >
          <Settings className="w-5 h-5 flex-shrink-0" />
          {!isCollapsed && 'Settings'}
        </NavLink>
      </div>

      {/* Spacer to push content up */}
      <div className="flex-1" />
    </aside>
  );
}
