import { useCallback, useEffect, useState } from 'react'

/** Seconds remaining on a resend cooldown, counted down once a second. */
export function useCountdown(initial = 0) {
  const [left, setLeft] = useState(initial)

  useEffect(() => {
    if (left <= 0) return
    const id = window.setTimeout(() => setLeft((n) => n - 1), 1000)
    return () => window.clearTimeout(id)
  }, [left])

  const start = useCallback((seconds: number) => setLeft(seconds), [])
  return { left, start }
}
