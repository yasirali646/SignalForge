import { useCallback, useEffect, useState } from 'react'
import type { AlertLog, AlertRule, Competitor } from '../types'
import { api } from '../api/client'
import { ConfirmDialog } from './ConfirmDialog'
import { useToast } from './ToastProvider'

interface AlertRulesPanelProps {
  competitors: Competitor[]
}

const EVENT_TYPE_OPTIONS = [
  { value: 'pricing_change', label: 'Pricing changes' },
  { value: 'messaging_change', label: 'Messaging changes' },
  { value: 'hiring_change', label: 'Hiring changes' },
  { value: 'news_signal', label: 'News signals' },
  { value: 'agent_intel', label: 'Agent intelligence' },
] as const

type RuleFormState = {
  name: string
  enabled: boolean
  min_severity: 'low' | 'medium' | 'high'
  event_types: string[]
  competitor_id: number | null
  webhook_url: string
}

const emptyForm = (): RuleFormState => ({
  name: '',
  enabled: true,
  min_severity: 'medium',
  event_types: ['pricing_change', 'messaging_change'],
  competitor_id: null,
  webhook_url: '',
})

function parseEventTypes(raw: string): string[] {
  return raw
    .split(',')
    .map((t) => t.trim())
    .filter(Boolean)
}

function formFromRule(rule: AlertRule): RuleFormState {
  return {
    name: rule.name,
    enabled: rule.enabled,
    min_severity: rule.min_severity as RuleFormState['min_severity'],
    event_types: parseEventTypes(rule.event_types),
    competitor_id: rule.competitor_id,
    webhook_url: rule.webhook_url ?? '',
  }
}

function toApiBody(form: RuleFormState) {
  return {
    name: form.name.trim(),
    enabled: form.enabled,
    min_severity: form.min_severity,
    event_types: form.event_types.join(','),
    competitor_id: form.competitor_id,
    webhook_url: form.webhook_url.trim() || null,
  }
}

export function AlertRulesPanel({ competitors }: AlertRulesPanelProps) {
  const { showToast } = useToast()
  const [rules, setRules] = useState<AlertRule[]>([])
  const [logs, setLogs] = useState<AlertLog[]>([])
  const [error, setError] = useState<string | null>(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form, setForm] = useState<RuleFormState>(emptyForm)
  const [saving, setSaving] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<AlertRule | null>(null)
  const [deleting, setDeleting] = useState(false)

  const load = useCallback(async () => {
    try {
      const [r, l] = await Promise.all([api.getAlertRules(), api.getAlertLogs()])
      setRules(r)
      setLogs(l)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load alerts')
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  function openCreate() {
    setEditingId(null)
    setForm(emptyForm())
    setModalOpen(true)
  }

  function openEdit(rule: AlertRule) {
    setEditingId(rule.id)
    setForm(formFromRule(rule))
    setModalOpen(true)
  }

  function closeModal() {
    setModalOpen(false)
    setEditingId(null)
    setForm(emptyForm())
  }

  function toggleEventType(value: string) {
    setForm((f) => {
      const has = f.event_types.includes(value)
      const event_types = has
        ? f.event_types.filter((t) => t !== value)
        : [...f.event_types, value]
      return { ...f, event_types }
    })
  }

  async function saveRule(e: React.FormEvent) {
    e.preventDefault()
    if (!form.name.trim()) {
      showToast('Enter a rule name', 'error')
      return
    }
    if (form.event_types.length === 0) {
      showToast('Select at least one event type', 'error')
      return
    }

    setSaving(true)
    try {
      const body = toApiBody(form)
      if (editingId != null) {
        const existing = rules.find((r) => r.id === editingId)
        if (!existing) throw new Error('Rule not found')
        await api.updateAlertRule(editingId, { ...existing, ...body })
        showToast('Alert rule updated')
      } else {
        await api.createAlertRule(body)
        showToast('Alert rule created')
      }
      closeModal()
      await load()
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Could not save rule', 'error')
    } finally {
      setSaving(false)
    }
  }

  async function toggleRule(rule: AlertRule) {
    try {
      await api.updateAlertRule(rule.id, { ...rule, enabled: !rule.enabled })
      await load()
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Could not update rule', 'error')
    }
  }

  function requestDelete(rule: AlertRule) {
    setDeleteTarget(rule)
  }

  async function confirmDelete() {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      await api.deleteAlertRule(deleteTarget.id)
      showToast('Alert rule deleted')
      setDeleteTarget(null)
      await load()
    } catch (err) {
      showToast(err instanceof Error ? err.message : 'Could not delete rule', 'error')
    } finally {
      setDeleting(false)
    }
  }

  return (
    <section className="panel alerts-panel">
      <p className="alerts-intro">
        Alert rules watch new change events from collection or Forge Scout. When an event
        matches your severity and signal types (and optional competitor filter), SignalForge
        logs it below and can POST to a webhook URL.
      </p>

      <div className="panel-header">
        Alert rules
        <button type="button" className="btn btn-sm btn-primary" onClick={openCreate}>
          Add rule
        </button>
      </div>
      <div className="panel-body">
        {error && <p className="error-banner">{error}</p>}
        {rules.length === 0 ? (
          <p className="empty">
            No rules yet. Two defaults are created on first API start — click Add rule to
            create your own.
          </p>
        ) : (
          <ul className="rules-list">
            {rules.map((r) => (
              <li key={r.id} className="rule-item">
                <div className="rule-item-top">
                  <label className="rule-toggle">
                    <input
                      type="checkbox"
                      checked={r.enabled}
                      onChange={() => toggleRule(r)}
                    />
                    <strong>{r.name}</strong>
                  </label>
                  <div className="rule-actions">
                    <button
                      type="button"
                      className="btn btn-sm"
                      onClick={() => openEdit(r)}
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      className="btn btn-sm btn-danger"
                      onClick={() => requestDelete(r)}
                    >
                      Delete
                    </button>
                  </div>
                </div>
                <div className="rule-meta">
                  Min severity: {r.min_severity}
                  {r.event_types && ` · Types: ${r.event_types}`}
                  {r.competitor_id &&
                    ` · ${competitors.find((c) => c.id === r.competitor_id)?.name ?? 'Competitor'}`}
                  {r.webhook_url && ' · Webhook'}
                  {!r.enabled && ' · Paused'}
                </div>
              </li>
            ))}
          </ul>
        )}

        <h4 className="alerts-subhead">Recent alerts</h4>
        {logs.length === 0 ? (
          <p className="empty">
            No alerts fired yet. Run Collect or simulate a change — matching rules will
            appear here.
          </p>
        ) : (
          <ul className="alert-logs">
            {logs.slice(0, 8).map((l) => (
              <li key={l.id}>
                <span className="log-msg">{l.message}</span>
                <span className="log-time">
                  {new Date(l.created_at).toLocaleString()}
                  {l.delivered ? ' · delivered' : ''}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <ConfirmDialog
        open={deleteTarget != null}
        title="Delete alert rule?"
        message={
          deleteTarget
            ? `"${deleteTarget.name}" will be removed. Past alert logs are kept, but this rule will no longer fire.`
            : ''
        }
        confirmLabel="Delete"
        cancelLabel="Keep rule"
        variant="danger"
        loading={deleting}
        onConfirm={confirmDelete}
        onCancel={() => !deleting && setDeleteTarget(null)}
      />

      {modalOpen && (
        <div className="modal-overlay" role="presentation" onClick={closeModal}>
          <div
            className="modal alert-rule-modal"
            role="dialog"
            aria-labelledby="alert-rule-title"
            onClick={(ev) => ev.stopPropagation()}
          >
            <h3 id="alert-rule-title">
              {editingId != null ? 'Edit alert rule' : 'New alert rule'}
            </h3>
            <form className="alert-rule-form" onSubmit={saveRule}>
              <label className="form-field">
                <span>Name</span>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                  placeholder="e.g. Acme pricing spikes"
                  required
                  maxLength={128}
                />
              </label>

              <label className="form-field">
                <span>Minimum severity</span>
                <select
                  value={form.min_severity}
                  onChange={(e) =>
                    setForm((f) => ({
                      ...f,
                      min_severity: e.target.value as RuleFormState['min_severity'],
                    }))
                  }
                >
                  <option value="low">Low and above</option>
                  <option value="medium">Medium and above</option>
                  <option value="high">High only</option>
                </select>
              </label>

              <fieldset className="form-field">
                <legend>Event types</legend>
                <div className="checkbox-grid">
                  {EVENT_TYPE_OPTIONS.map((opt) => (
                    <label key={opt.value} className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={form.event_types.includes(opt.value)}
                        onChange={() => toggleEventType(opt.value)}
                      />
                      {opt.label}
                    </label>
                  ))}
                </div>
              </fieldset>

              <label className="form-field">
                <span>Competitor (optional)</span>
                <select
                  value={form.competitor_id ?? ''}
                  onChange={(e) =>
                    setForm((f) => ({
                      ...f,
                      competitor_id: e.target.value ? Number(e.target.value) : null,
                    }))
                  }
                >
                  <option value="">All competitors</option>
                  {competitors.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </label>

              <label className="form-field">
                <span>Webhook URL (optional)</span>
                <input
                  type="url"
                  value={form.webhook_url}
                  onChange={(e) => setForm((f) => ({ ...f, webhook_url: e.target.value }))}
                  placeholder="https://hooks.example.com/..."
                />
              </label>

              <label className="checkbox-label rule-enabled">
                <input
                  type="checkbox"
                  checked={form.enabled}
                  onChange={(e) => setForm((f) => ({ ...f, enabled: e.target.checked }))}
                />
                Rule enabled
              </label>

              <div className="modal-actions">
                <button type="button" className="btn" onClick={closeModal} disabled={saving}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={saving}>
                  {saving ? 'Saving…' : editingId != null ? 'Save changes' : 'Create rule'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </section>
  )
}
