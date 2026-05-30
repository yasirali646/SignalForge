import { useState } from 'react'
import type { CompetitorCreate } from '../types'

interface AddCompetitorModalProps {
  open: boolean
  onClose: () => void
  onSubmit: (data: CompetitorCreate) => Promise<void>
}

export function AddCompetitorModal({ open, onClose, onSubmit }: AddCompetitorModalProps) {
  const [name, setName] = useState('')
  const [domain, setDomain] = useState('')
  const [pricingUrl, setPricingUrl] = useState('')
  const [homepageUrl, setHomepageUrl] = useState('')
  const [careersUrl, setCareersUrl] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!open) return null

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await onSubmit({
        name,
        domain,
        pricing_url: pricingUrl || undefined,
        homepage_url: homepageUrl || undefined,
        careers_url: careersUrl || undefined,
      })
      setName('')
      setDomain('')
      setPricingUrl('')
      setHomepageUrl('')
      setCareersUrl('')
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create competitor')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose} role="presentation">
      <div className="modal" onClick={(e) => e.stopPropagation()} role="dialog">
        <h2>Add competitor</h2>
        {error && <p className="error-banner">{error}</p>}
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="name">Company name</label>
            <input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              placeholder="Acme Corp"
            />
          </div>
          <div className="form-group">
            <label htmlFor="domain">Domain</label>
            <input
              id="domain"
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              required
              placeholder="acme.com"
            />
          </div>
          <div className="form-group">
            <label htmlFor="pricing">Pricing URL (Unlocker)</label>
            <input
              id="pricing"
              value={pricingUrl}
              onChange={(e) => setPricingUrl(e.target.value)}
              placeholder="https://acme.com/pricing"
            />
          </div>
          <div className="form-group">
            <label htmlFor="homepage">Homepage URL</label>
            <input
              id="homepage"
              value={homepageUrl}
              onChange={(e) => setHomepageUrl(e.target.value)}
              placeholder="https://acme.com"
            />
          </div>
          <div className="form-group">
            <label htmlFor="careers">Careers URL</label>
            <input
              id="careers"
              value={careersUrl}
              onChange={(e) => setCareersUrl(e.target.value)}
              placeholder="https://acme.com/careers"
            />
          </div>
          <div className="modal-actions">
            <button type="button" className="btn" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? 'Creating…' : 'Create & monitor'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
