import type { Competitor, EventFilters } from '../types'

interface EventFiltersBarProps {
  competitors: Competitor[]
  filters: EventFilters
  onChange: (f: EventFilters) => void
}

export function EventFiltersBar({
  competitors,
  filters,
  onChange,
}: EventFiltersBarProps) {
  function set<K extends keyof EventFilters>(key: K, value: EventFilters[K]) {
    onChange({ ...filters, [key]: value })
  }

  return (
    <div className="filters-bar">
      <label>
        Competitor
        <select
          value={filters.competitor_id ?? ''}
          onChange={(e) =>
            set(
              'competitor_id',
              e.target.value === '' ? undefined : Number(e.target.value)
            )
          }
        >
          <option value="">All</option>
          {competitors.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        Severity
        <select
          value={filters.severity ?? ''}
          onChange={(e) =>
            set('severity', e.target.value || undefined)
          }
        >
          <option value="">All</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
      </label>
      <label>
        Type
        <select
          value={filters.event_type ?? ''}
          onChange={(e) =>
            set('event_type', e.target.value || undefined)
          }
        >
          <option value="">All</option>
          <option value="pricing_change">Pricing</option>
          <option value="messaging_change">Messaging</option>
          <option value="hiring_change">Hiring</option>
          <option value="news_signal">News</option>
          <option value="agent_intel">Agent intel</option>
        </select>
      </label>
      <label>
        Source
        <select
          value={filters.origin ?? ''}
          onChange={(e) => set('origin', e.target.value || undefined)}
        >
          <option value="">All</option>
          <option value="pipeline">Pipeline</option>
          <option value="agent">Agent</option>
        </select>
      </label>
    </div>
  )
}
