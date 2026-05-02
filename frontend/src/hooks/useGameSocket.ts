/**
 * hooks/useGameSocket.ts — v2.2
 * Agent 6 — Développeur Frontend | Sprint RPG
 *
 * v2.1 : URL construite depuis window.location (ws/wss automatique).
 * v2.2 : Token envoyé en premier message JSON après connexion (plus dans l'URL).
 *        Évite l'exposition du JWT dans les logs nginx et l'historique navigateur.
 *        Protocole côté serveur : premier message {"type":"auth","token":"..."}.
 */
import { useEffect, useRef, useCallback } from 'react'
import { useAuthStore } from '@/stores/authStore'
import { useWsEventHandlers } from '@/components/layout/NotificationPanel'

const MAX_RECONNECT_DELAY = 30_000

/** Construit l'URL WebSocket depuis l'origine courante — fonctionne en dev et prod. */
function getWsUrl(): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host     = window.location.host   // ex: "localhost:5173" ou "emago.example.com"
  return `${protocol}//${host}/ws`
}

export function useGameSocket() {
  const { accessToken } = useAuthStore()
  const wsRef           = useRef<WebSocket | null>(null)
  const delayRef        = useRef(1_000)
  const reconnectTimer  = useRef<ReturnType<typeof setTimeout> | null>(null)
  const handlers        = useWsEventHandlers()

  const connect = useCallback(() => {
    if (!accessToken) return
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const ws      = new WebSocket(getWsUrl())
    wsRef.current = ws

    ws.onopen = () => {
      // Envoyer le token en premier message — jamais dans l'URL (logs serveur)
      ws.send(JSON.stringify({ type: 'auth', token: accessToken }))
      delayRef.current = 1_000  // reset backoff sur connexion réussie
    }

    ws.onmessage = (e) => {
      try {
        const event = JSON.parse(e.data)
        switch (event.type) {
          case 'combat.result':    handlers.handleCombatResult(event.data);  break
          case 'forge.complete':   handlers.handleForgeComplete(event.data); break
          case 'ship.grade_up':    handlers.handleGradeUp(event.data);       break
          case 'ship.scar_earned': handlers.handleScarEarned(event.data);    break
          case 'fleet.arrived':    handlers.handleFleetArrived(event.data);  break
          case 'connected':        /* bienvenue */                           break
          case 'pong':             /* keepalive ok */                        break
          default:
            console.debug('[WS] Event non géré :', event.type)
        }
      } catch (err) {
        console.warn('[WS] Erreur parsing message :', err)
      }
    }

    ws.onclose = () => {
      // Reconnexion avec backoff exponentiel (1s → 30s max)
      reconnectTimer.current = setTimeout(() => {
        delayRef.current = Math.min(delayRef.current * 2, MAX_RECONNECT_DELAY)
        connect()
      }, delayRef.current)
    }

    ws.onerror = (err) => {
      console.error('[WS] Erreur :', err)
      ws.close()
    }
  }, [accessToken, handlers])

  // Keepalive ping toutes les 30s
  useEffect(() => {
    const interval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'ping' }))
      }
    }, 30_000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    connect()
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [connect])

  // Polling forge fallback (si WS interrompu pendant une forge active)
  const pollForge = useCallback((forgeId: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'forge.poll', data: { forge_id: forgeId } }))
    }
  }, [])

  return { pollForge }
}