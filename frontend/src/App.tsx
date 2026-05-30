import { useCallback, useEffect, useState } from 'react'
import { useAuth } from './auth/AuthContext'
import { api, createCompetitorWithSources, updateCompetitorWithSources } from './api/client'
import { LoginPage } from './components/LoginPage'
import { AddCompetitorModal } from './components/AddCompetitorModal'
import { AgentPanel } from './components/AgentPanel'
import { AlertRulesPanel } from './components/AlertRulesPanel'
import { CollectProgressModal } from './components/CollectProgressModal'
import { CompetitorPanel } from './components/CompetitorPanel'
import { ConfirmDialog } from './components/ConfirmDialog'
import { EditCompetitorModal } from './components/EditCompetitorModal'
import { EventFeed } from './components/EventFeed'
import { EventsSection } from './components/EventsSection'
import { Header } from './components/Header'
import { MetricsBar } from './components/MetricsBar'
import { OverviewCharts } from './components/OverviewCharts'
import { SettingsPanel } from './components/SettingsPanel'
import { Sidebar, type NavSection } from './components/Sidebar'
import type {
  Competitor,
  CompetitorCreate,
  CompetitorUpdate,
  DailyBrief,
  Event,
  SchedulerStatus,
} from './types'

function formatBriefTime(iso: string) {
  try {
    return new Date(iso).toLocaleTimeString(undefined, {
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return '—'
  }
}

const SECTION_META: Record<
  NavSection,
  { title: string; subtitle: string }
> = {
  overview: {
    title: 'Overview',
    subtitle: 'Daily pulse, metrics, and competitive summary',
  },
  agent: {
    title: 'Forge Scout',
    subtitle: 'AI research with live web access via Bright Data',
  },
  events: {
    title: 'Change events',
    subtitle: 'Filtered feed of pricing, news, and agent intelligence',
  },
  competitors: {
    title: 'Competitors',
    subtitle: 'Collect snapshots and simulate changes for demos',
  },
  alerts: {
    title: 'Alerts',
    subtitle: 'Rules and notification log for high-signal changes',
  },
  settings: {
    title: 'Settings',
    subtitle: 'Control how often background data collection runs',
  },
}

export default function App() {
  const { user, loading: authLoading, authEnabled, logout } = useAuth()
  const canManageCompetitors = user?.can_manage_competitors ?? false
  const [apiOnline, setApiOnline] = useState<boolean | null>(null)
  const [competitors, setCompetitors] = useState<Competitor[]>([])
  const [events, setEvents] = useState<Event[]>([])
  const [brief, setBrief] = useState<DailyBrief | null>(null)
  const [scheduler, setScheduler] = useState<SchedulerStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [eventsRefresh, setEventsRefresh] = useState(0)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingCompetitor, setEditingCompetitor] = useState<Competitor | null>(null)
  const [deletingCompetitor, setDeletingCompetitor] = useState<Competitor | null>(null)
  const [deleteLoading, setDeleteLoading] = useState(false)
  const [collectModalOpen, setCollectModalOpen] = useState(false)
  const [collectModalKind, setCollectModalKind] = useState<'collect' | 'simulate'>('collect')
  const [collectModalMode, setCollectModalMode] = useState<'one' | 'all'>('all')
  const [collectModalCompetitor, setCollectModalCompetitor] = useState<string | undefined>(
    undefined
  )
  const [collectModalDone, setCollectModalDone] = useState(false)
  const [collectModalError, setCollectModalError] = useState<string | null>(null)
  const [activeSection, setActiveSection] = useState<NavSection>('overview')
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [mobileNavOpen, setMobileNavOpen] = useState(false)

  const load = useCallback(async () => {
    setError(null)
    try {
      await api.health()
      setApiOnline(true)
      const [comps, evts, br, sched] = await Promise.all([
        api.getCompetitors(),
        api.getEvents({ limit: 150 }),
        api.getDailyBrief(),
        api.getSchedulerStatus(),
      ])
      setCompetitors(comps)
      setEvents(evts)
      setBrief(br)
      setScheduler(sched)
      setEventsRefresh((n) => n + 1)
    } catch {
      setApiOnline(false)
      setError('Unable to connect right now. Please try again in a moment.')
    }
  }, [])

  // Load dashboard data only when authenticated. An initial load while still on
  // the login screen (no token) would fail and leave a stale error until refresh.
  useEffect(() => {
    if (authLoading) return
    if (authEnabled && !user) {
      setApiOnline(null)
      setError(null)
      setCompetitors([])
      setEvents([])
      setBrief(null)
      setScheduler(null)
      return
    }
    void load()
  }, [load, authLoading, authEnabled, user])

  function navigate(section: NavSection) {
    setActiveSection(section)
    setMobileNavOpen(false)
  }

  async function handleCollectAll() {
    setCollectModalKind('collect')
    setCollectModalMode('all')
    setCollectModalCompetitor(undefined)
    setCollectModalDone(false)
    setCollectModalError(null)
    setCollectModalOpen(true)
    setLoading(true)
    setError(null)
    try {
      await api.collectAll()
      await load()
      setCollectModalDone(true)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Collection failed')
      setCollectModalError(e instanceof Error ? e.message : 'Collection failed')
    } finally {
      setLoading(false)
    }
  }

  async function handleCollectOne(id: number) {
    const name = competitors.find((c) => c.id === id)?.name
    setCollectModalKind('collect')
    setCollectModalMode('one')
    setCollectModalCompetitor(name)
    setCollectModalDone(false)
    setCollectModalError(null)
    setCollectModalOpen(true)
    setBusyId(id)
    setError(null)
    try {
      await api.collectOne(id)
      await load()
      setCollectModalDone(true)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Collection failed')
      setCollectModalError(e instanceof Error ? e.message : 'Collection failed')
    } finally {
      setBusyId(null)
    }
  }

  async function handleSimulate(id: number) {
    const name = competitors.find((c) => c.id === id)?.name
    setCollectModalKind('simulate')
    setCollectModalMode('one')
    setCollectModalCompetitor(name)
    setCollectModalDone(false)
    setCollectModalError(null)
    setCollectModalOpen(true)
    setBusyId(id)
    setError(null)
    try {
      await api.simulateChange(id)
      await load()
      setCollectModalDone(true)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Need pricing baseline first — run Collect')
      setCollectModalError(
        e instanceof Error ? e.message : 'Need pricing baseline first — run Collect'
      )
    } finally {
      setBusyId(null)
    }
  }

  async function handleAddCompetitor(data: CompetitorCreate) {
    await createCompetitorWithSources(data)
    await load()
  }

  async function handleEditCompetitor(id: number, data: CompetitorUpdate) {
    await updateCompetitorWithSources(id, data)
    await load()
  }

  async function handleConfirmDelete() {
    if (!deletingCompetitor) return
    setDeleteLoading(true)
    setError(null)
    try {
      await api.deleteCompetitor(deletingCompetitor.id)
      setDeletingCompetitor(null)
      await load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to delete competitor')
    } finally {
      setDeleteLoading(false)
    }
  }

  const meta = SECTION_META[activeSection]

  if (authLoading) {
    return <div className="login-loading">Loading…</div>
  }

  if (!user) {
    return <LoginPage />
  }

  return (
    <div className="app-shell">
      <div className="ai-ambient" aria-hidden>
        <div className="ai-orb ai-orb-1" />
        <div className="ai-orb ai-orb-2" />
        <div className="ai-orb ai-orb-3" />
      </div>
      {mobileNavOpen && (
        <button
          type="button"
          className="sidebar-backdrop"
          aria-label="Close menu"
          onClick={() => setMobileNavOpen(false)}
        />
      )}

      <Sidebar
        active={activeSection}
        onNavigate={navigate}
        apiOnline={apiOnline}
        competitorCount={competitors.length}
        eventCount={brief?.event_count ?? events.length}
        schedulerActive={scheduler?.running ?? false}
        schedulerHours={scheduler?.interval_hours}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed((c) => !c)}
        mobileOpen={mobileNavOpen}
      />

      <div
        className={`app-main ${sidebarCollapsed ? 'sidebar-collapsed' : ''} ${
          mobileNavOpen ? 'mobile-nav-open' : ''
        } ${activeSection === 'agent' ? 'page-agent' : ''}`}
      >
        <Header
          title={meta.title}
          subtitle={meta.subtitle}
          loading={loading}
          onRefresh={load}
          onCollectAll={handleCollectAll}
          onAddCompetitor={() => setModalOpen(true)}
          showAddCompetitor={canManageCompetitors}
          showMenuButton
          onMenuToggle={() => setMobileNavOpen((o) => !o)}
          username={user.username}
          userRole={user.role}
          showLogout={authEnabled}
          onLogout={logout}
        />

        {error && <div className="error-banner">{error}</div>}

        <div className="page-content">
          {activeSection === 'overview' && (
            <>
              {scheduler?.running && (
                <div className="brief-banner">
                  Autonomous monitoring active — collecting every{' '}
                  {scheduler.interval_hours}h
                </div>
              )}
              <MetricsBar
                competitors={competitors.length}
                eventCount={brief?.event_count ?? events.length}
                highSeverity={brief?.high_severity_count ?? 0}
                briefTime={brief ? formatBriefTime(brief.generated_at) : '—'}
              />
              {brief && <div className="brief-banner">{brief.summary}</div>}
              <OverviewCharts events={events} />
              <div className="overview-grid">
                <EventFeed events={events.slice(0, 8)} />
                <div className="overview-aside">
                  <CompetitorPanel
                    competitors={competitors}
                    busyId={busyId}
                    canManage={canManageCompetitors}
                    onCollect={handleCollectOne}
                    onSimulate={handleSimulate}
                    onEdit={setEditingCompetitor}
                    onDelete={setDeletingCompetitor}
                  />
                </div>
              </div>
            </>
          )}

          {activeSection === 'agent' && (
            <AgentPanel competitors={competitors} onPipelineUpdate={load} />
          )}

          {activeSection === 'events' && (
            <EventsSection competitors={competitors} refreshSignal={eventsRefresh} />
          )}

          {activeSection === 'competitors' && (
            <CompetitorPanel
              competitors={competitors}
              busyId={busyId}
              canManage={canManageCompetitors}
              onCollect={handleCollectOne}
              onSimulate={handleSimulate}
              onEdit={setEditingCompetitor}
              onDelete={setDeletingCompetitor}
            />
          )}

          {activeSection === 'alerts' && (
            <AlertRulesPanel competitors={competitors} />
          )}

          {activeSection === 'settings' && (
            <SettingsPanel
              onSaved={() => {
                load()
              }}
            />
          )}
        </div>
      </div>

      {canManageCompetitors && (
        <AddCompetitorModal
          open={modalOpen}
          onClose={() => setModalOpen(false)}
          onSubmit={handleAddCompetitor}
        />
      )}

      {canManageCompetitors && (
        <EditCompetitorModal
          competitor={editingCompetitor}
          onClose={() => setEditingCompetitor(null)}
          onSubmit={handleEditCompetitor}
        />
      )}

      {canManageCompetitors && (
      <ConfirmDialog
        open={deletingCompetitor !== null}
        title="Delete competitor?"
        message={
          deletingCompetitor
            ? `Remove ${deletingCompetitor.name} and all related sources, snapshots, events, agent runs, and alert rules. This cannot be undone.`
            : ''
        }
        confirmLabel="Delete"
        variant="danger"
        loading={deleteLoading}
        onConfirm={handleConfirmDelete}
        onCancel={() => !deleteLoading && setDeletingCompetitor(null)}
      />
      )}

      <CollectProgressModal
        open={collectModalOpen}
        kind={collectModalKind}
        mode={collectModalMode}
        competitorName={collectModalCompetitor}
        finished={collectModalDone}
        error={collectModalError}
        onClose={() => setCollectModalOpen(false)}
      />
    </div>
  )
}
