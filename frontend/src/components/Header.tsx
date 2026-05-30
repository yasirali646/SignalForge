interface HeaderProps {
  title: string
  subtitle?: string
  loading: boolean
  onRefresh: () => void
  onCollectAll: () => void
  onAddCompetitor: () => void
  onMenuToggle?: () => void
  showMenuButton?: boolean
  username?: string
  userRole?: string
  showAddCompetitor?: boolean
  showLogout?: boolean
  onLogout?: () => void
}

export function Header({
  title,
  subtitle,
  loading,
  onRefresh,
  onCollectAll,
  onAddCompetitor,
  onMenuToggle,
  showMenuButton,
  username,
  userRole,
  showAddCompetitor = true,
  showLogout,
  onLogout,
}: HeaderProps) {
  return (
    <header className="page-header">
      <div className="page-header-text">
        {showMenuButton && (
          <button
            type="button"
            className="btn btn-icon mobile-menu-btn"
            onClick={onMenuToggle}
            aria-label="Open menu"
          >
            ☰
          </button>
        )}
        <div>
          <h1>{title}</h1>
          {subtitle && <p>{subtitle}</p>}
        </div>
      </div>
      <div className="header-actions">
        {username && (
          <span className="header-user" title="Signed in">
            {username}
            {userRole === 'demo' && <span className="header-role-badge">Demo</span>}
          </span>
        )}
        {showLogout && onLogout && (
          <button type="button" className="btn" onClick={onLogout}>
            Sign out
          </button>
        )}
        <button type="button" className="btn" onClick={onRefresh} disabled={loading}>
          Refresh
        </button>
        <button
          type="button"
          className="btn btn-primary"
          onClick={onCollectAll}
          disabled={loading}
        >
          {loading ? 'Collecting…' : 'Run collection'}
        </button>
        {showAddCompetitor && (
          <button type="button" className="btn" onClick={onAddCompetitor}>
            Add competitor
          </button>
        )}
      </div>
    </header>
  )
}
