export type NavSection =
  | 'overview'
  | 'agent'
  | 'events'
  | 'competitors'
  | 'alerts'
  | 'settings'

interface SidebarProps {
  active: NavSection
  onNavigate: (section: NavSection) => void
  apiOnline: boolean | null
  competitorCount: number
  eventCount: number
  schedulerActive: boolean
  schedulerHours?: number
  collapsed: boolean
  onToggleCollapse: () => void
  mobileOpen?: boolean
}

const NAV: { id: NavSection; label: string; hint: string }[] = [
  { id: 'overview', label: 'Overview', hint: 'Metrics & pulse' },
  { id: 'agent', label: 'Forge Scout', hint: 'AI research' },
  { id: 'events', label: 'Events', hint: 'Change feed' },
  { id: 'competitors', label: 'Competitors', hint: 'Track & collect' },
  { id: 'alerts', label: 'Alerts', hint: 'Rules & logs' },
  { id: 'settings', label: 'Settings', hint: 'Collection schedule' },
]

export function Sidebar({
  active,
  onNavigate,
  apiOnline,
  competitorCount,
  eventCount,
  schedulerActive,
  schedulerHours,
  collapsed,
  onToggleCollapse,
  mobileOpen = false,
}: SidebarProps) {
  return (
    <aside
      className={`app-sidebar ${collapsed ? 'collapsed' : ''} ${
        mobileOpen ? 'mobile-open' : ''
      }`}
    >
      <div className="sidebar-brand">
        <div className="sidebar-logo">
          <img
            src="/signalforge-icon.svg"
            alt=""
            width={40}
            height={40}
            className="sidebar-logo-img"
          />
        </div>
        {!collapsed && (
          <div className="sidebar-brand-text">
            <span className="sidebar-title">SignalForge</span>
            <span className="sidebar-tagline">AI · Live web intel</span>
          </div>
        )}
        <button
          type="button"
          className="sidebar-collapse-btn"
          onClick={onToggleCollapse}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          title={collapsed ? 'Expand' : 'Collapse'}
        >
          {collapsed ? '»' : '«'}
        </button>
      </div>

      {!collapsed && (
        <div className="ai-pill">
          <span className="ai-pill-dot" />
          Neural pipeline
        </div>
      )}

      {!collapsed && (
        <div className="sidebar-status">
          {apiOnline === true && <span className="status-ok">Online</span>}
          {apiOnline === false && <span className="status-down">Offline</span>}
          {apiOnline === null && (
            <span className="status-pending">Connecting…</span>
          )}
        </div>
      )}

      <nav className="sidebar-nav" aria-label="Main navigation">
        {NAV.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`sidebar-nav-item ${
              item.id === 'agent' ? 'sidebar-nav-item--agent' : ''
            } ${active === item.id ? 'active' : ''}`}
            onClick={() => onNavigate(item.id)}
            title={collapsed ? item.label : undefined}
          >
            <span className="sidebar-nav-icon" aria-hidden>
              {item.id === 'overview' && '◎'}
              {item.id === 'agent' && '✦'}
              {item.id === 'events' && '⚡'}
              {item.id === 'competitors' && '◆'}
              {item.id === 'alerts' && '◉'}
              {item.id === 'settings' && '⚙'}
            </span>
            {!collapsed && (
              <span className="sidebar-nav-label">
                <span className="sidebar-nav-title">{item.label}</span>
                <span className="sidebar-nav-hint">{item.hint}</span>
              </span>
            )}
          </button>
        ))}
      </nav>

      {!collapsed && (
        <div className="sidebar-footer">
          <div className="sidebar-stat">
            <span className="sidebar-stat-value">{competitorCount}</span>
            <span className="sidebar-stat-label">Competitors</span>
          </div>
          <div className="sidebar-stat">
            <span className="sidebar-stat-value">{eventCount}</span>
            <span className="sidebar-stat-label">Events</span>
          </div>
          {schedulerActive && (
            <p className="sidebar-scheduler">
              Auto-collect every {schedulerHours ?? '—'}h
            </p>
          )}
        </div>
      )}
    </aside>
  )
}
