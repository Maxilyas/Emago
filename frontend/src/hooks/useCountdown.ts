/**
 * Hook countdown — interpolation côté client à partir d'eta_seconds.
 * Le serveur est la source de vérité — on interpole juste pour l'affichage.
 */
import { useState, useEffect, useRef } from 'react'

export function useCountdown(etaSeconds: number, onComplete?: () => void) {
  const [remaining, setRemaining] = useState(Math.max(0, etaSeconds))
  const startedAt = useRef(Date.now())
  const initialEta = useRef(etaSeconds)
  const completedRef = useRef(false)

  useEffect(() => {
    startedAt.current = Date.now()
    initialEta.current = Math.max(0, etaSeconds)
    completedRef.current = false
    setRemaining(initialEta.current)

    if (initialEta.current <= 0) {
      onComplete?.()
      return
    }

    const tick = () => {
      const elapsed = (Date.now() - startedAt.current) / 1000
      const left = Math.max(0, initialEta.current - elapsed)
      setRemaining(Math.round(left))

      if (left <= 0 && !completedRef.current) {
        completedRef.current = true
        onComplete?.()
      }
    }

    const interval = setInterval(tick, 1000)
    return () => clearInterval(interval)
  }, [etaSeconds]) // eslint-disable-line react-hooks/exhaustive-deps

  const pct = initialEta.current > 0
    ? Math.round(((initialEta.current - remaining) / initialEta.current) * 100)
    : 100

  return { remaining, pct, done: remaining <= 0 }
}
