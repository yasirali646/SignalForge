import { clearAccessToken, getAccessToken } from '../auth/session'
import type {
  AgentChatResult,
  AgentRun,
  AlertLog,
  AlertRule,
  AuthConfig,
  CollectResult,
  Competitor,
  CompetitorCreate,
  CompetitorUpdate,
  Source,
  DailyBrief,
  Event,
  EventFilters,
  LoginResponse,
  SchedulerSettings,
  SchedulerStatus,
  UserProfile,
} from '../types'

const API = import.meta.env.VITE_API_URL?.replace(/\/$/, '') || '/api/v1'
const UNAUTHORIZED_EVENT = 'signalforge:unauthorized'

function parseApiError(text: string, status: number): string {
  try {
    const body = JSON.parse(text) as { detail?: string | { msg?: string }[] }
    if (typeof body.detail === 'string') return body.detail
    if (Array.isArray(body.detail) && body.detail[0]?.msg) {
      return body.detail[0].msg
    }
  } catch {
    /* plain text */
  }
  return text || `Request failed: ${status}`
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getAccessToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init?.headers as Record<string, string> | undefined),
  }
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  const res = await fetch(`${API}${path}`, { ...init, headers })
  if (res.status === 401 && !path.startsWith('/auth/login')) {
    clearAccessToken()
    window.dispatchEvent(new Event(UNAUTHORIZED_EVENT))
  }
  if (!res.ok) {
    const text = await res.text()
    throw new Error(parseApiError(text, res.status))
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

function buildQuery(params: Record<string, string | number | undefined>): string {
  const q = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== '') q.set(k, String(v))
  }
  const s = q.toString()
  return s ? `?${s}` : ''
}

export const api = {
  getAuthConfig: () => request<AuthConfig>('/auth/config'),

  login: (username: string, password: string) =>
    request<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    }),

  getMe: () => request<UserProfile>('/auth/me'),

  health: () => request<{ status: string }>('/health'),

  getCompetitors: () => request<Competitor[]>('/competitors'),

  createCompetitor: (body: { name: string; domain: string }) =>
    request<Competitor>('/competitors', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  updateCompetitor: (id: number, body: CompetitorUpdate) =>
    request<Competitor>(`/competitors/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),

  deleteCompetitor: (id: number) =>
    request<void>(`/competitors/${id}`, { method: 'DELETE' }),

  getCompetitorSources: (id: number) =>
    request<Source[]>(`/competitors/${id}/sources`),

  addSource: (
    competitorId: number,
    body: { url: string; source_type: string; use_unlocker?: boolean }
  ) =>
    request<unknown>(`/competitors/${competitorId}/sources`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  getEvents: (filters: EventFilters = {}) =>
    request<Event[]>(
      `/events${buildQuery({
        limit: filters.limit ?? 50,
        offset: filters.offset ?? 0,
        competitor_id: filters.competitor_id,
        severity: filters.severity,
        event_type: filters.event_type,
        origin: filters.origin,
      })}`
    ),

  getDailyBrief: () => request<DailyBrief>('/brief/daily'),

  collectAll: () =>
    request<CollectResult[]>('/collect', { method: 'POST' }),

  collectOne: (id: number) =>
    request<CollectResult>(`/collect/${id}`, { method: 'POST' }),

  simulateChange: (id: number) =>
    request<Event[]>(`/demo/simulate-change/${id}`, { method: 'POST' }),

  getSchedulerStatus: () => request<SchedulerStatus>('/scheduler/status'),

  getSchedulerSettings: () =>
    request<SchedulerSettings>('/settings/scheduler'),

  updateSchedulerSettings: (body: {
    scheduler_enabled?: boolean
    scheduler_interval_hours?: number
  }) =>
    request<SchedulerSettings>('/settings/scheduler', {
      method: 'PUT',
      body: JSON.stringify(body),
    }),

  getAgentStatus: () =>
    request<{
      configured: boolean
      mcp_configured: boolean
      brightdata_agent: boolean
      agent_mode: string
      model: string
      agent_requests_used: number
      agent_requests_limit: number | null
      agent_requests_remaining: number | null
    }>('/agent/status'),

  getAgentRuns: (competitorId?: number) =>
    request<AgentRun[]>(
      `/agent/runs${buildQuery({ competitor_id: competitorId, limit: 15 })}`
    ),

  getAgentRun: (id: number) =>
    request<AgentRun & { reply_md: string }>(`/agent/runs/${id}`),

  agentChat: (message: string, competitorId?: number, triggerCollection = true) =>
    request<AgentChatResult>('/agent/chat', {
      method: 'POST',
      body: JSON.stringify({
        message,
        competitor_id: competitorId ?? null,
        trigger_collection: triggerCollection,
      }),
    }),

  agentResearch: (competitorId: number) =>
    request<AgentChatResult>(`/agent/research/${competitorId}`, {
      method: 'POST',
    }),

  getAlertRules: () => request<AlertRule[]>('/alerts/rules'),

  createAlertRule: (body: Omit<AlertRule, 'id'>) =>
    request<AlertRule>('/alerts/rules', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  updateAlertRule: (id: number, body: Omit<AlertRule, 'id'>) =>
    request<AlertRule>(`/alerts/rules/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),

  deleteAlertRule: (id: number) =>
    request<void>(`/alerts/rules/${id}`, { method: 'DELETE' }),

  getAlertLogs: () => request<AlertLog[]>('/alerts/logs?limit=30'),
}

export async function agentChatStream(
  message: string,
  competitorId: number | undefined,
  onChunk: (event: string, data: unknown) => void
): Promise<void> {
  const token = getAccessToken()
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  const res = await fetch(`${API}/agent/chat/stream`, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      message,
      competitor_id: competitorId ?? null,
      trigger_collection: true,
    }),
  })
  if (res.status === 401) {
    clearAccessToken()
    window.dispatchEvent(new Event(UNAUTHORIZED_EVENT))
  }
  if (!res.ok || !res.body) {
    const text = await res.text()
    throw new Error(parseApiError(text, res.status))
  }
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      try {
        const parsed = JSON.parse(line.slice(6)) as { event: string; data: unknown }
        onChunk(parsed.event, parsed.data)
      } catch {
        /* skip malformed */
      }
    }
  }
}

function buildSourcePayloads(data: CompetitorCreate) {
  const sources: Array<{ url: string; source_type: string; use_unlocker?: boolean }> = []
  if (data.pricing_url) {
    sources.push({ url: data.pricing_url, source_type: 'pricing', use_unlocker: true })
  }
  if (data.homepage_url) {
    sources.push({ url: data.homepage_url, source_type: 'homepage' })
  }
  if (data.careers_url) {
    sources.push({ url: data.careers_url, source_type: 'careers' })
  }
  sources.push({ url: `serp://${data.name}/news`, source_type: 'news' })
  return sources
}

export async function createCompetitorWithSources(data: CompetitorCreate) {
  const competitor = await api.createCompetitor({
    name: data.name,
    domain: data.domain,
  })
  for (const s of buildSourcePayloads(data)) {
    await api.addSource(competitor.id, s)
  }
  return competitor
}

export async function updateCompetitorWithSources(id: number, data: CompetitorUpdate) {
  return api.updateCompetitor(id, {
    name: data.name,
    domain: data.domain,
    pricing_url: data.pricing_url,
    homepage_url: data.homepage_url,
    careers_url: data.careers_url,
  })
}

export function sourcesToFormUrls(sources: Source[]) {
  const byType = Object.fromEntries(sources.map((s) => [s.source_type, s.url]))
  return {
    pricing_url: byType.pricing?.startsWith('http') ? byType.pricing : '',
    homepage_url: byType.homepage ?? '',
    careers_url: byType.careers ?? '',
  }
}
