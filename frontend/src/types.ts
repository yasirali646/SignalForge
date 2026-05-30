export interface AuthConfig {
  auth_enabled: boolean
  product_name: string
  demo_username: string | null
}

export interface LoginResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: UserProfile
}

export interface UserProfile {
  username: string
  role: 'admin' | 'demo' | string
  can_manage_competitors: boolean
  agent_requests_used: number
  agent_requests_limit: number | null
  agent_requests_remaining: number | null
}

export interface Competitor {
  id: number
  name: string
  domain: string
  created_at: string
}

export interface Event {
  id: number
  competitor_id: number
  competitor_name: string | null
  source_id: number | null
  origin: string
  agent_run_id: number | null
  event_type: string
  severity: 'low' | 'medium' | 'high' | string
  title: string
  diff_summary: string
  evidence_url: string
  before_snapshot_id: number | null
  after_snapshot_id: number | null
  detected_at: string
}

export interface EventFilters {
  competitor_id?: number
  severity?: string
  event_type?: string
  origin?: string
  limit?: number
  offset?: number
}

export interface DailyBrief {
  generated_at: string
  event_count: number
  high_severity_count: number
  events: Event[]
  summary: string
}

export interface CollectResult {
  competitor_id: number
  sources_processed: number
  snapshots_created: number
  events_created: number
  errors: string[]
}

export interface CompetitorCreate {
  name: string
  domain: string
  pricing_url?: string
  homepage_url?: string
  careers_url?: string
}

export interface CompetitorUpdate extends CompetitorCreate {}

export interface Source {
  id: number
  competitor_id: number
  url: string
  source_type: string
  use_unlocker: boolean
  label: string | null
}

export interface AgentRun {
  id: number
  competitor_id: number | null
  competitor_name: string | null
  query: string
  reply_preview: string
  events_created: number
  collection_triggered: boolean
  created_at: string
}

export interface AgentChatResult {
  reply: string
  tool_count: number
  tools_available: string[]
  agent_run_id?: number
  events_created?: number
  collection_triggered?: boolean
}

export interface AlertRule {
  id: number
  name: string
  enabled: boolean
  event_types: string
  min_severity: string
  competitor_id: number | null
  webhook_url: string | null
}

export interface AlertLog {
  id: number
  rule_id: number
  event_id: number
  message: string
  delivered: boolean
  created_at: string
  event_title: string | null
  competitor_name: string | null
}

export interface SchedulerStatus {
  enabled: boolean
  running: boolean
  interval_hours: number
}

export interface SchedulerIntervalPreset {
  label: string
  hours: number
}

export interface SchedulerSettings {
  scheduler_enabled: boolean
  scheduler_interval_hours: number
  scheduler_running: boolean
  next_run_at: string | null
  interval_presets: SchedulerIntervalPreset[]
}
