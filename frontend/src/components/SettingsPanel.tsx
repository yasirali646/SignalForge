import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import type { SchedulerSettings } from '../types'
import { useToast } from './ToastProvider'

function formatNextRun(iso: string | null | undefined) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString()
  } catch {
    return iso
  }
}

function formatInterval(hours: number) {
  if (hours < 1) return `${Math.round(hours * 60)} minutes`
  if (hours === 1) return '1 hour'
  return `${hours} hours`
}

interface SettingsPanelProps {
  onSaved?: () => void
}

export function SettingsPanel({ onSaved }: SettingsPanelProps) {
  const { showToast } = useToast()
  const [settings, setSettings] = useState<SchedulerSettings | null>(null)
  const [enabled, setEnabled] = useState(true)
  const [intervalHours, setIntervalHours] = useState(6)
  const [useCustom, setUseCustom] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const s = await api.getSchedulerSettings()
      setSettings(s)
      setEnabled(s.scheduler_enabled)
      setIntervalHours(s.scheduler_interval_hours)
      const presetMatch = s.interval_presets.some(
        (p) => Math.abs(p.hours - s.scheduler_interval_hours) < 0.01
      )
      setUseCustom(!presetMatch)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load settings')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const updated = await api.updateSchedulerSettings({
        scheduler_enabled: enabled,
        scheduler_interval_hours: intervalHours,
      })
      setSettings(updated)
      onSaved?.()
      if (updated.scheduler_enabled) {
        showToast(
          `Background collection enabled — runs every ${formatInterval(updated.scheduler_interval_hours)}`,
          'success'
        )
      } else {
        showToast('Background collection turned off', 'success')
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Save failed'
      setError(msg)
      showToast('Could not save settings', 'error')
    } finally {
      setSaving(false)
    }
  }

  function selectPreset(hours: number) {
    setUseCustom(false)
    setIntervalHours(hours)
  }

  if (loading) {
    return (
      <section className="panel settings-panel">
        <div className="panel-header">Settings</div>
        <div className="panel-body">
          <p className="empty">Loading settings…</p>
        </div>
      </section>
    )
  }

  return (
    <section className="panel settings-panel">
      <div className="panel-header">Settings</div>
      <div className="panel-body">
        <form onSubmit={handleSave} className="settings-form">
          <div className="settings-section">
            <h3>Background collection</h3>
            <p className="settings-desc">
              Automatically fetch competitor data from the web while the API is
              running. Changes apply immediately without restarting the server.
            </p>

            <label className="settings-toggle">
              <input
                type="checkbox"
                checked={enabled}
                onChange={(e) => setEnabled(e.target.checked)}
              />
              <span>Enable automatic collection</span>
            </label>

            {enabled && (
              <>
                <p className="settings-label">How often to run</p>
                <div className="settings-presets">
                  {settings?.interval_presets.map((p) => (
                    <button
                      key={p.hours}
                      type="button"
                      className={`preset-chip ${
                        !useCustom &&
                        Math.abs(intervalHours - p.hours) < 0.01
                          ? 'active'
                          : ''
                      }`}
                      onClick={() => selectPreset(p.hours)}
                    >
                      {p.label}
                    </button>
                  ))}
                </div>

                <label className="settings-custom">
                  <input
                    type="checkbox"
                    checked={useCustom}
                    onChange={(e) => setUseCustom(e.target.checked)}
                  />
                  Custom interval (hours)
                </label>
                {useCustom && (
                  <input
                    type="number"
                    className="settings-input"
                    min={0.25}
                    max={168}
                    step={0.25}
                    value={intervalHours}
                    onChange={(e) =>
                      setIntervalHours(parseFloat(e.target.value) || 0.25)
                    }
                  />
                )}

                <p className="settings-summary">
                  Current schedule:{' '}
                  <strong>{formatInterval(intervalHours)}</strong>
                </p>
              </>
            )}
          </div>

          <div className="settings-status-card">
            <div className="settings-status-row">
              <span>Scheduler</span>
              <span
                className={
                  settings?.scheduler_running ? 'status-ok' : 'status-muted'
                }
              >
                {settings?.scheduler_running ? 'Active' : 'Inactive'}
              </span>
            </div>
            {enabled && (
              <div className="settings-status-row">
                <span>Next collection</span>
                <span>{formatNextRun(settings?.next_run_at)}</span>
              </div>
            )}
          </div>

          {error && <p className="settings-error">{error}</p>}

          <button
            type="submit"
            className="btn btn-primary"
            disabled={saving}
          >
            {saving ? 'Saving…' : 'Save settings'}
          </button>
        </form>
      </div>
    </section>
  )
}
