import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type { Competitor, Event, EventFilters } from '../types'
import { EventFeed } from './EventFeed'
import { EventFiltersBar } from './EventFiltersBar'

const PAGE_SIZE = 25

interface EventsSectionProps {
  competitors: Competitor[]
  refreshSignal?: number
}

function mergeEvents(prev: Event[], next: Event[]): Event[] {
  const seen = new Set(prev.map((e) => e.id))
  const unique = next.filter((e) => !seen.has(e.id))
  return unique.length ? [...prev, ...unique] : prev
}

export function EventsSection({ competitors, refreshSignal = 0 }: EventsSectionProps) {
  const [filters, setFilters] = useState<EventFilters>({})
  const [events, setEvents] = useState<Event[]>([])
  const [hasMore, setHasMore] = useState(true)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const offsetRef = useRef(0)
  const loadingMoreRef = useRef(false)
  const sentinelRef = useRef<HTMLDivElement>(null)

  const fetchPage = useCallback(
    async (offset: number, append: boolean) => {
      const batch = await api.getEvents({
        ...filters,
        limit: PAGE_SIZE,
        offset,
      })
      setHasMore(batch.length >= PAGE_SIZE)
      offsetRef.current = offset + batch.length
      setEvents((prev) => (append ? mergeEvents(prev, batch) : batch))
      return batch
    },
    [filters]
  )

  const loadInitial = useCallback(async () => {
    setLoading(true)
    setError(null)
    offsetRef.current = 0
    setHasMore(true)
    try {
      await fetchPage(0, false)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load events')
      setEvents([])
      setHasMore(false)
    } finally {
      setLoading(false)
    }
  }, [fetchPage])

  const loadMore = useCallback(async () => {
    if (loadingMoreRef.current || !hasMore || loading) return
    loadingMoreRef.current = true
    setLoadingMore(true)
    setError(null)
    try {
      await fetchPage(offsetRef.current, true)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load more events')
    } finally {
      loadingMoreRef.current = false
      setLoadingMore(false)
    }
  }, [fetchPage, hasMore, loading])

  useEffect(() => {
    loadInitial()
  }, [loadInitial, refreshSignal])

  useEffect(() => {
    const el = sentinelRef.current
    if (!el || loading) return

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) {
          void loadMore()
        }
      },
      { root: null, rootMargin: '240px', threshold: 0 }
    )

    observer.observe(el)
    return () => observer.disconnect()
  }, [loadMore, loading, events.length, hasMore])

  return (
    <>
      <EventFiltersBar competitors={competitors} filters={filters} onChange={setFilters} />
      {error && <div className="error-banner">{error}</div>}
      {loading && events.length === 0 ? (
        <section className="panel">
          <div className="panel-body">
            <p className="loading">Loading events…</p>
          </div>
        </section>
      ) : (
        <EventFeed
          events={events}
          footer={
            <>
              <div ref={sentinelRef} className="scroll-sentinel" aria-hidden />
              {loadingMore && (
                <p className="feed-status feed-status--loading">Loading more events…</p>
              )}
              {!hasMore && events.length > 0 && (
                <p className="feed-status">You&apos;ve reached the end of the feed.</p>
              )}
            </>
          }
        />
      )}
    </>
  )
}
