import type { Event } from '../types'

export const SEVERITY_COLORS: Record<string, string> = {
  high: '#f87171',
  medium: '#fbbf24',
  low: '#34d399',
}

export const EVENT_TYPE_LABELS: Record<string, string> = {
  pricing_change: 'Pricing',
  messaging_change: 'Messaging',
  hiring_change: 'Hiring',
  news_signal: 'News',
  agent_intel: 'Agent intel',
}

export function labelEventType(type: string): string {
  return EVENT_TYPE_LABELS[type] ?? type.replace(/_/g, ' ')
}

export function buildDailySeries(events: Event[], days = 14) {
  const now = new Date()
  const buckets: { date: string; label: string; count: number }[] = []

  for (let i = days - 1; i >= 0; i--) {
    const d = new Date(now)
    d.setHours(0, 0, 0, 0)
    d.setDate(d.getDate() - i)
    const date = d.toISOString().slice(0, 10)
    const label = d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
    buckets.push({ date, label, count: 0 })
  }

  const byDate = new Map(buckets.map((b) => [b.date, b]))
  for (const e of events) {
    const key = e.detected_at.slice(0, 10)
    const bucket = byDate.get(key)
    if (bucket) bucket.count += 1
  }

  return buckets
}

export function buildSeveritySeries(events: Event[]) {
  const counts = { high: 0, medium: 0, low: 0 }
  for (const e of events) {
    const key = e.severity as keyof typeof counts
    if (key in counts) counts[key] += 1
  }
  return (['high', 'medium', 'low'] as const).map((severity) => ({
    name: severity.charAt(0).toUpperCase() + severity.slice(1),
    severity,
    value: counts[severity],
    fill: SEVERITY_COLORS[severity],
  }))
}

export function buildTypeSeries(events: Event[]) {
  const counts = new Map<string, number>()
  for (const e of events) {
    counts.set(e.event_type, (counts.get(e.event_type) ?? 0) + 1)
  }
  return [...counts.entries()]
    .map(([type, value]) => ({
      name: labelEventType(type),
      type,
      value,
    }))
    .sort((a, b) => b.value - a.value)
}

export function buildCompetitorSeries(events: Event[], limit = 6) {
  const counts = new Map<string, number>()
  for (const e of events) {
    const name = e.competitor_name ?? `Competitor #${e.competitor_id}`
    counts.set(name, (counts.get(name) ?? 0) + 1)
  }
  return [...counts.entries()]
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, limit)
}
