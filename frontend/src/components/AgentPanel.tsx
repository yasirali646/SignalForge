import { useCallback, useEffect, useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import type { AgentRun, Competitor } from '../types'
import { agentChatStream, api } from '../api/client'
import { AgentMarkdown } from './AgentMarkdown'

interface AgentStatus {
  configured: boolean
  mcp_configured: boolean
  brightdata_agent: boolean
  agent_mode: string
  model: string
  agent_requests_used: number
  agent_requests_limit: number | null
  agent_requests_remaining: number | null
}

interface AgentPanelProps {
  competitors: Competitor[]
  onPipelineUpdate?: () => void
}

export function AgentPanel({ competitors, onPipelineUpdate }: AgentPanelProps) {
  const { user, refreshUser } = useAuth()
  const [status, setStatus] = useState<AgentStatus | null>(null)
  const [apiReachable, setApiReachable] = useState(true)
  const [model, setModel] = useState('')
  const [message, setMessage] = useState('')
  const [reply, setReply] = useState('')
  const [streamStatus, setStreamStatus] = useState('')
  const [loading, setLoading] = useState(false)
  const [competitorId, setCompetitorId] = useState<number | ''>('')
  const [error, setError] = useState<string | null>(null)
  const [runs, setRuns] = useState<AgentRun[]>([])
  const [pipelineNote, setPipelineNote] = useState('')

  const configured = status?.configured ?? false
  const agentLimit = status?.agent_requests_limit ?? user?.agent_requests_limit ?? null
  const agentRemaining =
    status?.agent_requests_remaining ?? user?.agent_requests_remaining ?? null
  const agentExhausted =
    agentLimit !== null && agentLimit !== undefined && (agentRemaining ?? 0) <= 0

  const loadStatus = useCallback(async () => {
    try {
      const s = await api.getAgentStatus()
      setStatus(s)
      setModel(s.model)
      setApiReachable(true)
      setError(null)
    } catch (err) {
      setApiReachable(false)
      setStatus(null)
      const msg = err instanceof Error ? err.message : 'Unknown error'
      if (msg.includes('404') || msg.includes('Not Found')) {
        setError('Service is temporarily unavailable. Please refresh the page.')
      } else {
        setError(msg)
      }
    }
  }, [])

  const loadRuns = useCallback(async () => {
    try {
      const cid = competitorId === '' ? undefined : Number(competitorId)
      setRuns(await api.getAgentRuns(cid))
    } catch {
      setRuns([])
    }
  }, [competitorId])

  useEffect(() => {
    loadStatus()
  }, [loadStatus])

  useEffect(() => {
    if (configured) loadRuns()
  }, [configured, loadRuns])

  async function afterAgentSuccess() {
    await Promise.all([loadStatus(), refreshUser(), loadRuns()])
    onPipelineUpdate?.()
  }

  async function handleChat(e: React.FormEvent) {
    e.preventDefault()
    if (!message.trim() || agentExhausted) return
    setLoading(true)
    setError(null)
    setReply('')
    setStreamStatus('')
    setPipelineNote('')
    const cid = competitorId === '' ? undefined : Number(competitorId)
    try {
      let accumulated = ''
      await agentChatStream(message, cid, (event, data) => {
        if (event === 'status') {
          setStreamStatus(String(data))
        } else if (event === 'token') {
          accumulated += String(data)
          setReply(accumulated)
        } else if (event === 'pipeline') {
          const p = data as {
            events_created?: number
            collection_triggered?: boolean
            agent_requests_remaining?: number | null
          }
          setPipelineNote(
            `Linked to pipeline: ${p.events_created ?? 0} event(s)` +
              (p.collection_triggered ? ', collection ran' : '')
          )
          void afterAgentSuccess()
        } else if (event === 'error') {
          setError(String(data))
        }
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Agent request failed')
      await loadStatus()
      await refreshUser()
    } finally {
      setLoading(false)
      setStreamStatus('')
    }
  }

  async function handleResearch(id: number) {
    if (agentExhausted) return
    setLoading(true)
    setError(null)
    setReply('')
    setPipelineNote('')
    try {
      const res = await api.agentResearch(id)
      setReply(res.reply)
      setPipelineNote(
        `Run #${res.agent_run_id}: ${res.events_created ?? 0} events` +
          (res.collection_triggered ? ' · pipeline refreshed' : '')
      )
      await afterAgentSuccess()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Research failed')
      await loadStatus()
      await refreshUser()
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="panel agent-panel ai-panel">
      <div className="panel-header">✦ Forge Scout</div>
      <div className="panel-body">
        {apiReachable && configured && (
          <p className="agent-meta status-ok">
            Agent online · {model || 'Bright Data MCP'}
          </p>
        )}

        {agentLimit !== null && (
          <p
            className={`agent-quota ${agentExhausted ? 'agent-quota-exhausted' : ''}`}
          >
            Demo agent requests: {status?.agent_requests_used ?? user?.agent_requests_used ?? 0}{' '}
            / {agentLimit} used
            {agentRemaining !== null && agentRemaining > 0
              ? ` · ${agentRemaining} remaining`
              : agentExhausted
                ? ' · limit reached'
                : ''}
          </p>
        )}

        {!configured && apiReachable && status && (
          <p className="empty">
            Add BRIGHTDATA_MCP or BRIGHTDATA_API_TOKEN in .env to enable the agent.
          </p>
        )}

        {agentExhausted && (
          <p className="settings-error">
            Demo agent limit reached. Sign in with an admin account for unlimited Forge Scout
            requests.
          </p>
        )}

        <form onSubmit={handleChat} className="agent-form">
          <label>
            Focus competitor
            <select
              value={competitorId}
              onChange={(e) =>
                setCompetitorId(e.target.value === '' ? '' : Number(e.target.value))
              }
              disabled={agentExhausted}
            >
              <option value="">All / general</option>
              {competitors.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Ask the agent
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={3}
              placeholder="Research competitor moves, pricing, hiring…"
              disabled={!configured || loading || agentExhausted}
            />
          </label>
          <div className="agent-form-actions">
            <button
              type="submit"
              className="btn btn-primary"
              disabled={
                !configured || loading || !message.trim() || agentExhausted
              }
            >
              {loading ? 'Streaming…' : 'Ask agent (live)'}
            </button>
          </div>
        </form>

        {streamStatus && <p className="stream-status">{streamStatus}</p>}
        {pipelineNote && <p className="pipeline-note">{pipelineNote}</p>}

        {competitors.length > 0 && configured && (
          <div className="agent-quick">
            <span>Quick research → pipeline:</span>
            {competitors.map((c) => (
              <button
                key={c.id}
                type="button"
                className="btn btn-sm"
                disabled={loading || agentExhausted}
                onClick={() => handleResearch(c.id)}
              >
                {c.name}
              </button>
            ))}
          </div>
        )}

        {runs.length > 0 && (
          <div className="agent-runs">
            <h4>Recent agent runs</h4>
            <ul>
              {runs.map((r) => (
                <li key={r.id}>
                  <button
                    type="button"
                    className="run-link"
                    onClick={async () => {
                      const full = await api.getAgentRun(r.id)
                      setReply(full.reply_md)
                    }}
                  >
                    {r.competitor_name ?? 'General'} — {new Date(r.created_at).toLocaleString()}
                  </button>
                  <span className="run-meta">
                    {r.events_created} events
                    {r.collection_triggered ? ' · collected' : ''}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {error && <p className="settings-error">{error}</p>}
        {reply && (
          <div className="agent-reply agent-reply-box">
            <h4>Agent response</h4>
            <AgentMarkdown content={reply} />
          </div>
        )}
      </div>
    </section>
  )
}
