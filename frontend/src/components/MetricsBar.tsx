interface MetricsBarProps {
  competitors: number
  eventCount: number
  highSeverity: number
  briefTime: string
}

export function MetricsBar({
  competitors,
  eventCount,
  highSeverity,
  briefTime,
}: MetricsBarProps) {
  return (
    <div className="metrics">
      <div className="metric-card">
        <div className="label">Competitors</div>
        <div className="value">{competitors}</div>
      </div>
      <div className="metric-card">
        <div className="label">Recent events</div>
        <div className="value">{eventCount}</div>
      </div>
      <div className="metric-card">
        <div className="label">High severity</div>
        <div className="value">{highSeverity}</div>
      </div>
      <div className="metric-card">
        <div className="label">Brief updated</div>
        <div className="value" style={{ fontSize: '1rem' }}>
          {briefTime}
        </div>
      </div>
    </div>
  )
}
