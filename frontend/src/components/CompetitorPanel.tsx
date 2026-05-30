import type { Competitor } from '../types'

interface CompetitorPanelProps {
  competitors: Competitor[]
  busyId: number | null
  canManage: boolean
  onCollect: (id: number) => void
  onSimulate: (id: number) => void
  onEdit: (competitor: Competitor) => void
  onDelete: (competitor: Competitor) => void
}

export function CompetitorPanel({
  competitors,
  busyId,
  canManage,
  onCollect,
  onSimulate,
  onEdit,
  onDelete,
}: CompetitorPanelProps) {
  return (
    <section className="panel">
      <div className="panel-header">Competitors</div>
      <div className="panel-body" style={{ padding: 0 }}>
        {competitors.length === 0 ? (
          <p className="empty">No competitors. Add one to start monitoring.</p>
        ) : (
          competitors.map((c) => (
            <div key={c.id} className="competitor-card">
              <div className="competitor-card-top">
                <div>
                  <h3>{c.name}</h3>
                  <div className="domain">{c.domain}</div>
                </div>
                {canManage && (
                  <div className="competitor-card-menu">
                    <button
                      type="button"
                      className="btn btn-sm"
                      disabled={busyId === c.id}
                      onClick={() => onEdit(c)}
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      className="btn btn-sm btn-danger"
                      disabled={busyId === c.id}
                      onClick={() => onDelete(c)}
                    >
                      Delete
                    </button>
                  </div>
                )}
              </div>
              <div className="competitor-actions">
                <button
                  type="button"
                  className="btn btn-sm btn-primary"
                  disabled={busyId === c.id}
                  onClick={() => onCollect(c.id)}
                >
                  {busyId === c.id ? '…' : 'Collect'}
                </button>
                <button
                  type="button"
                  className="btn btn-sm"
                  disabled={busyId === c.id}
                  onClick={() => onSimulate(c.id)}
                >
                  Simulate change
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </section>
  )
}
