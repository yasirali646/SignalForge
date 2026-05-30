import { useEffect, useMemo, useRef, useState } from 'react'

type CollectMode = 'one' | 'all'
type ProgressKind = 'collect' | 'simulate'

interface CollectProgressModalProps {
  open: boolean
  kind?: ProgressKind
  mode: CollectMode
  competitorName?: string
  finished: boolean
  error?: string | null
  onClose: () => void
}

type Step = { label: string; hint: string }

function stepsFor(kind: ProgressKind, mode: CollectMode, competitorName?: string): Step[] {
  const who =
    mode === 'all'
      ? 'all competitors'
      : competitorName
        ? competitorName
        : 'competitor'
  if (kind === 'simulate') {
    return [
      { label: 'Preparing demo change', hint: `Selecting a pricing baseline for ${who}.` },
      { label: 'Injecting fixture snapshot', hint: 'Creating a synthetic “after” snapshot.' },
      { label: 'Diffing snapshots', hint: 'Comparing the injected snapshot to the baseline.' },
      { label: 'Creating events', hint: 'Generating a pricing change event for the demo.' },
      { label: 'Refreshing dashboard', hint: 'Updating the events feed and charts.' },
    ]
  }
  return [
    { label: 'Preparing collection', hint: `Building a task plan for ${who}.` },
    { label: 'Scraping sources', hint: 'Fetching pricing, homepage, careers, and news.' },
    { label: 'Extracting signals', hint: 'Turning pages into structured snapshots.' },
    { label: 'Diffing snapshots', hint: 'Comparing the latest snapshot to the baseline.' },
    { label: 'Creating events', hint: 'Generating change events with severity + evidence.' },
    { label: 'Refreshing dashboard', hint: 'Pulling the latest events, charts, and brief.' },
  ]
}

export function CollectProgressModal({
  open,
  kind = 'collect',
  mode,
  competitorName,
  finished,
  error,
  onClose,
}: CollectProgressModalProps) {
  const steps = useMemo(
    () => stepsFor(kind, mode, competitorName),
    [kind, mode, competitorName]
  )
  const [activeIdx, setActiveIdx] = useState(0)
  const closeTimerRef = useRef<number | null>(null)

  useEffect(() => {
    if (!open) return
    setActiveIdx(0)
    return () => {
      if (closeTimerRef.current) window.clearTimeout(closeTimerRef.current)
      closeTimerRef.current = null
    }
  }, [open])

  useEffect(() => {
    if (!open) return
    if (finished || error) return
    const id = window.setInterval(() => {
      setActiveIdx((i) => (i < steps.length - 1 ? i + 1 : i))
    }, 850)
    return () => window.clearInterval(id)
  }, [open, finished, error, steps.length])

  useEffect(() => {
    if (!open) return
    if (!finished || error) return
    closeTimerRef.current = window.setTimeout(() => {
      onClose()
    }, 1200)
  }, [open, finished, error, onClose])

  if (!open) return null

  const title =
    kind === 'simulate'
      ? `Simulating change — ${competitorName ?? 'competitor'}`
      : mode === 'all'
        ? 'Collecting competitors'
        : `Collecting ${competitorName ?? 'competitor'}`

  return (
    <div className="modal-overlay" role="presentation" onClick={onClose}>
      <div
        className="modal collect-progress-modal"
        role="dialog"
        aria-labelledby="collect-progress-title"
        aria-describedby="collect-progress-desc"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="collect-progress-top">
          <div>
            <h3 id="collect-progress-title" className="collect-progress-title">
              {title}
            </h3>
            <p id="collect-progress-desc" className="collect-progress-desc">
              {error
                ? kind === 'simulate'
                  ? 'Simulation failed.'
                  : 'Collection failed.'
                : finished
                  ? 'Done — dashboard updated.'
                  : 'Hang tight — here’s what’s happening behind the scenes.'}
            </p>
          </div>
          <div
            className={`collect-progress-indicator ${
              error ? 'error' : finished ? 'done' : 'running'
            }`}
            aria-hidden
          >
            <div className="collect-spinner" />
          </div>
        </div>

        {error && <div className="collect-progress-error">{error}</div>}

        <ol className="collect-steps">
          {steps.map((s, idx) => {
            const state =
              error && idx === activeIdx
                ? 'error'
                : finished && idx <= activeIdx
                  ? 'done'
                  : idx < activeIdx
                    ? 'done'
                    : idx === activeIdx
                      ? 'active'
                      : 'todo'
            return (
              <li key={s.label} className={`collect-step ${state}`}>
                <div className="collect-step-dot" aria-hidden />
                <div className="collect-step-text">
                  <div className="collect-step-label">{s.label}</div>
                  <div className="collect-step-hint">{s.hint}</div>
                </div>
              </li>
            )
          })}
        </ol>

        <div className="modal-actions">
          <button type="button" className="btn" onClick={onClose}>
            {finished ? 'Close' : 'Hide'}
          </button>
        </div>
      </div>
    </div>
  )
}

