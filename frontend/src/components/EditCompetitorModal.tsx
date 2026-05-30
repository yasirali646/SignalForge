import { useEffect, useState } from 'react'
import { api, sourcesToFormUrls } from '../api/client'
import type { Competitor, CompetitorUpdate } from '../types'

interface EditCompetitorModalProps {
  competitor: Competitor | null
  onClose: () => void
  onSubmit: (id: number, data: CompetitorUpdate) => Promise<void>
}

export function EditCompetitorModal({
  competitor,
  onClose,
  onSubmit,
}: EditCompetitorModalProps) {
  const [name, setName] = useState('')
  const [domain, setDomain] = useState('')
  const [pricingUrl, setPricingUrl] = useState('')
  const [homepageUrl, setHomepageUrl] = useState('')
  const [careersUrl, setCareersUrl] = useState('')
  const [loadingForm, setLoadingForm] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!competitor) return
    let cancelled = false
    setLoadingForm(true)
    setError(null)
    setName(competitor.name)
    setDomain(competitor.domain)
    api
      .getCompetitorSources(competitor.id)
      .then((sources) => {
        if (cancelled) return
        const urls = sourcesToFormUrls(sources)
        setPricingUrl(urls.pricing_url)
        setHomepageUrl(urls.homepage_url)
        setCareersUrl(urls.careers_url)
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load sources')
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingForm(false)
      })
    return () => {
      cancelled = true
    }
  }, [competitor])

  if (!competitor) return null

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!competitor) return
    setError(null)
    setSubmitting(true)
    try {
      await onSubmit(competitor.id, {
        name,
        domain,
        pricing_url: pricingUrl || undefined,
        homepage_url: homepageUrl || undefined,
        careers_url: careersUrl || undefined,
      })
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update competitor')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose} role="presentation">
      <div className="modal" onClick={(e) => e.stopPropagation()} role="dialog">
        <h2>Edit competitor</h2>
        {error && <p className="error-banner">{error}</p>}
        {loadingForm ? (
          <p className="empty" style={{ padding: '1.5rem 0' }}>
            Loading sources…
          </p>
        ) : (
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="edit-name">Company name</label>
              <input
                id="edit-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label htmlFor="edit-domain">Domain</label>
              <input
                id="edit-domain"
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label htmlFor="edit-pricing">Pricing URL (Unlocker)</label>
              <input
                id="edit-pricing"
                value={pricingUrl}
                onChange={(e) => setPricingUrl(e.target.value)}
              />
            </div>
            <div className="form-group">
              <label htmlFor="edit-homepage">Homepage URL</label>
              <input
                id="edit-homepage"
                value={homepageUrl}
                onChange={(e) => setHomepageUrl(e.target.value)}
              />
            </div>
            <div className="form-group">
              <label htmlFor="edit-careers">Careers URL</label>
              <input
                id="edit-careers"
                value={careersUrl}
                onChange={(e) => setCareersUrl(e.target.value)}
              />
            </div>
            <div className="modal-actions">
              <button type="button" className="btn" onClick={onClose}>
                Cancel
              </button>
              <button type="submit" className="btn btn-primary" disabled={submitting}>
                {submitting ? 'Saving…' : 'Save changes'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
