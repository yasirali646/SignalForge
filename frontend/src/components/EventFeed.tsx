import type { ReactNode } from 'react'
import type { Event } from '../types'
import { AgentMarkdown } from './AgentMarkdown'
import { looksLikeMarkdown } from '../utils/markdown'

function severityClass(severity: string) {
  if (severity === 'high') return 'high'
  if (severity === 'medium') return 'medium'
  return 'low'
}

function formatType(type: string) {
  return type.replace(/_/g, ' ')
}

interface EventFeedProps {
  events: Event[]
  footer?: ReactNode
}

export function EventFeed({ events, footer }: EventFeedProps) {
  return (
    <section className="panel">
      <div className="panel-header">Change event feed</div>
      <div className="panel-body">
        {events.length === 0 ? (
          <p className="empty">
            No events match filters. Run collection or use Forge Scout.
          </p>
        ) : (
          <ul className="event-list">
            {events.map((e) => (
              <li key={e.id}>
                <details className="event-item">
                  <summary>
                    <span className={`severity-dot ${severityClass(e.severity)}`} />
                    <span>
                      {e.competitor_name ?? 'Unknown'} — {e.title}
                    </span>
                    {e.origin === 'agent' && (
                      <span className="badge badge-agent">agent</span>
                    )}
                  </summary>
                  <div className="event-body">
                    <div className="meta">
                      <span className={`badge badge-${e.severity}`}>{e.severity}</span>
                      <span className="badge badge-type">{formatType(e.event_type)}</span>
                      <span className="badge badge-origin">{e.origin}</span>
                    </div>
                    {looksLikeMarkdown(e.diff_summary) ||
                    e.event_type === 'agent_intel' ||
                    e.origin === 'agent' ? (
                      <AgentMarkdown
                        content={e.diff_summary}
                        className="event-markdown"
                      />
                    ) : (
                      <p className="event-plain">{e.diff_summary}</p>
                    )}
                    <p>
                      <a href={e.evidence_url} target="_blank" rel="noreferrer">
                        View evidence
                      </a>
                    </p>
                    <p style={{ marginTop: '0.5rem', fontSize: '0.8rem' }}>
                      Detected {new Date(e.detected_at).toLocaleString()}
                    </p>
                  </div>
                </details>
              </li>
            ))}
          </ul>
        )}
        {footer}
      </div>
    </section>
  )
}
