/**
 * Hook WebSocket Emago.
 *
 * - Connexion automatique quand l'utilisateur est authentifié
 * - Reconnexion avec backoff exponentiel (1s → 30s max)
 * - Ping/pong keepalive toutes les 30s
 * - Dispatch des événements dans gameStore + invalidation TanStack Query
 * - Fallback polling GET /forge/:id si WS déconnecté pendant forge active
 */
import { useEffect, useRef, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { useAuthStore } from '@/stores/authStore'
import { useGameStore } from '@/stores/gameStore'
import type { CombatResultData, ForgeCompleteData, GradeUpData, ScarEarnedData, FleetArrivedData } from '@/types'
import { GRADE_CONFIG } from '@/types'

const WS_URL = '/ws'

export function useGameSocket() {
  const { accessToken } = useAuthStore()
  const { setWsConnected, addNotification, setPendingCombatResult } = useGameStore()
  const queryClient = useQueryClient()

  const wsRef       = useRef<WebSocket | null>(null)
  const retryRef    = useRef(0)
  const pingRef     = useRef<ReturnType<typeof setInterval> | null>(null)
  const mountedRef  = useRef(true)

  const handleForgeComplete = useCallback((data: ForgeCompleteData) => {
    queryClient.invalidateQueries({ queryKey: ['ships'] })
    queryClient.invalidateQueries({ queryKey: ['forge', 'history'] })
    addNotification({
      type: 'forge',
      title: '🔨 Forge terminée !',
      message: `Nouveau vaisseau ${data.rarity} prêt dans le hangar.`,
      data,
    })
    toast.success(`Forge terminée — vaisseau ${data.rarity} créé !`, { duration: 6000 })
  }, [queryClient, addNotification])

  const handleCombatResult = useCallback((data: CombatResultData) => {
    queryClient.invalidateQueries({ queryKey: ['ships'] })
    setPendingCombatResult(data)
    const won = data.winner === 'ATTACKER'
    addNotification({
      type: 'combat',
      title: won ? '⚔️ Victoire !' : data.winner === 'DRAW' ? '⚔️ Match nul' : '⚔️ Défaite',
      message: `Combat en ${data.total_rounds} rounds — ${won ? 'victoire' : data.winner === 'DRAW' ? 'égalité' : 'défaite'}`,
      data,
    })
  }, [queryClient, addNotification, setPendingCombatResult])

  const handleGradeUp = useCallback((data: GradeUpData) => {
    queryClient.invalidateQueries({ queryKey: ['ship', data.ship_id] })
    const gradeName = GRADE_CONFIG[data.new_grade]?.name ?? `Grade ${data.new_grade}`
    addNotification({
      type: 'grade_up',
      title: '⬆️ Progression de grade !',
      message: `Un vaisseau atteint le grade ${gradeName}`,
      data,
    })
    toast.success(`Grade ${gradeName} atteint !`, { icon: '⭐' })
  }, [queryClient, addNotification])

  const handleScarEarned = useCallback((data: ScarEarnedData) => {
    queryClient.invalidateQueries({ queryKey: ['ship', data.ship_id] })
    addNotification({
      type: 'scar',
      title: '🩹 Cicatrice gagnée',
      message: data.tag,
      data,
    })
  }, [queryClient, addNotification])

  const handleFleetArrived = useCallback((data: FleetArrivedData) => {
    queryClient.invalidateQueries({ queryKey: ['fleets'] })
    addNotification({
      type: 'fleet',
      title: '🚀 Flotte arrivée',
      message: `Mission ${data.mission} terminée`,
      data,
    })
  }, [queryClient, addNotification])

  const connect = useCallback(() => {
    if (!accessToken || !mountedRef.current) return
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const ws = new WebSocket(`${WS_URL}?token=${accessToken}`)
    wsRef.current = ws

    ws.onopen = () => {
      retryRef.current = 0
      setWsConnected(true)

      // Ping keepalive toutes les 30s
      pingRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'ping' }))
      }, 30_000)
    }

    ws.onmessage = (e: MessageEvent<string>) => {
      try {
        const event = JSON.parse(e.data) as { type: string; data: unknown }
        switch (event.type) {
          case 'forge.complete':  handleForgeComplete(event.data as ForgeCompleteData); break
          case 'combat.result':   handleCombatResult(event.data as CombatResultData); break
          case 'ship.grade_up':   handleGradeUp(event.data as GradeUpData); break
          case 'ship.scar_earned':handleScarEarned(event.data as ScarEarnedData); break
          case 'fleet.arrived':   handleFleetArrived(event.data as FleetArrivedData); break
          case 'connected':       break // bienvenue
          case 'pong':            break // keepalive
        }
      } catch (err) {
        console.warn('[WS] parse error', err)
      }
    }

    ws.onerror = () => { /* géré dans onclose */ }

    ws.onclose = () => {
      setWsConnected(false)
      if (pingRef.current) clearInterval(pingRef.current)
      if (!mountedRef.current) return
      // Backoff exponentiel
      const delay = Math.min(1000 * 2 ** retryRef.current, 30_000)
      retryRef.current++
      setTimeout(connect, delay)
    }
  }, [accessToken, setWsConnected, handleForgeComplete, handleCombatResult, handleGradeUp, handleScarEarned, handleFleetArrived])

  useEffect(() => {
    mountedRef.current = true
    if (accessToken) connect()
    return () => {
      mountedRef.current = false
      wsRef.current?.close()
      if (pingRef.current) clearInterval(pingRef.current)
    }
  }, [accessToken, connect])

  /** Envoie un message WebSocket (ex: forge.poll) */
  const send = useCallback((msg: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg))
    }
  }, [])

  return { send }
}
