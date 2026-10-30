import { useCallback, useEffect, useState } from 'react'
import { ApiError, api, type Me } from '@/lib/api'

/** Loads the signed-in account, sending anyone without a session to /login. */
export function useMe() {
  const [me, setMe] = useState<Me | null>(null)
  const [loading, setLoading] = useState(true)

  const reload = useCallback(async () => {
    try {
      const next = await api.me()
      // An account that never confirmed its address cannot use the assistant.
      if (!next.verified && window.location.pathname !== '/verify') {
        window.location.href = '/verify'
        return
      }
      setMe(next)
    } catch (ex) {
      if (ex instanceof ApiError && ex.status === 401) {
        window.location.href = '/login'
        return
      }
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void reload()
  }, [reload])

  /** Optimistic bump after an exchange, so the meter moves without a refetch. */
  const countExchange = useCallback(() => {
    setMe((prev) => (prev ? { ...prev, used: prev.used + 1, remaining: Math.max(0, prev.remaining - 1) } : prev))
  }, [])

  const setWakeName = useCallback((wake_name: string) => {
    setMe((prev) => (prev ? { ...prev, wake_name } : prev))
  }, [])

  return { me, loading, reload, countExchange, setWakeName }
}
