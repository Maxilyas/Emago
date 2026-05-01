/**
 * components/layout/NotificationPanel.tsx — v2
 * Agent 6 — Développeur Frontend | Sprint 3
 *
 * Panel de notifications WebSocket — intégration complète.
 * Sprint 3 : invalidation TanStack Query après events WS + toasts.
 *
 * Events gérés :
 *   combat.result   → invalidate ships, afficher résumé
 *   forge.complete  → invalidate ships + hangar, toast 🎉
 *   ship.grade_up   → invalidate ship detail, toast ⭐
 *   ship.scar_earned → invalidate ship detail, toast narratif
 *   fleet.arrived   → invalidate fleets
 */
import React, { useEffect, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { useGameStore } from '@/stores/gameStore'

// ─── Types ────────────────────────────────────────────────────────────────────

interface Notification {
  id: string
  type: string
  title: string
  message: string
  timestamp: Date
  read: boolean
  data?: unknown
}

// ─── Hook d'invalidation ─────────────────────────────────────────────────────

export function useWsEventHandlers() {
  const qc = useQueryClient()
  const { addNotification } = useGameStore()

  const handleCombatResult = (data: any) => {
    const won = data.winner === 'ATTACKER'
    const emoji = won ? '⚔️ Victoire !' : data.winner === 'DRAW' ? '🤝 Match nul' : '🛡️ Défaite'
    const msg = `${data.ships_lost?.attacker?.length ?? 0} vaisseaux perdus | ${data.ships_lost?.defender?.length ?? 0} vaisseaux détruits`

    // Invalider ships (XP, grades, cicatrices ont pu changer)
    qc.invalidateQueries({ queryKey: ['ships'] })
    // Invalider le classement (score peut avoir changé)
    qc.invalidateQueries({ queryKey: ['ranking'] })

    toast(emoji, { duration: 4000 })
    addNotification({
      id: data.combat_id,
      type: 'combat.result',
      title: emoji,
      message: msg,
      timestamp: new Date(),
      read: false,
      data,
    })
  }

  const handleForgeComplete = (data: any) => {
    // Invalider le hangar complet et la liste des ships
    qc.invalidateQueries({ queryKey: ['ships'] })
    qc.invalidateQueries({ queryKey: ['forge'] })
    qc.invalidateQueries({ queryKey: ['forge', 'history'] })

    toast.success(`🎉 Forge terminée ! Rareté : ${data.rarity}`, { duration: 5000 })
    addNotification({
      id: data.new_ship_id,
      type: 'forge.complete',
      title: '🎉 Forge terminée',
      message: `Nouveau vaisseau ${data.rarity} prêt dans le hangar`,
      timestamp: new Date(),
      read: false,
      data,
    })
  }

  const handleGradeUp = (data: any) => {
    // Invalider le vaisseau spécifique
    qc.invalidateQueries({ queryKey: ['ships', data.ship_id] })
    qc.invalidateQueries({ queryKey: ['ships'] })

    const gradeNames = ['Recrue', 'Vétéran', 'Élite', 'Légion', 'Légende', 'Spectre']
    toast(`⭐ Grade ${gradeNames[data.new_grade] || data.new_grade} atteint !`, { duration: 4000 })
    addNotification({
      id: `grade_${data.ship_id}_${data.new_grade}`,
      type: 'ship.grade_up',
      title: `⭐ Grade ${gradeNames[data.new_grade]} !`,
      message: `${data.combat_xp} XP total`,
      timestamp: new Date(),
      read: false,
    })
  }

  const handleScarEarned = (data: any) => {
    qc.invalidateQueries({ queryKey: ['ships', data.ship_id] })

    toast(`🩹 Cicatrice : "${data.tag}"`, { duration: 5000 })
    addNotification({
      id: `scar_${data.ship_id}_${Date.now()}`,
      type: 'ship.scar_earned',
      title: '🩹 Nouvelle cicatrice',
      message: data.tag,
      timestamp: new Date(),
      read: false,
    })
  }

  const handleFleetArrived = (data: any) => {
    qc.invalidateQueries({ queryKey: ['fleets'] })
    qc.invalidateQueries({ queryKey: ['planets'] })

    const mission = data.mission?.toLowerCase() || 'mission'
    toast(`🚀 Flotte arrivée — ${mission}`, { duration: 3000 })
    addNotification({
      id: `fleet_${data.fleet_id}`,
      type: 'fleet.arrived',
      title: '🚀 Flotte arrivée',
      message: `Mission : ${data.mission}`,
      timestamp: new Date(),
      read: false,
    })
  }

  return { handleCombatResult, handleForgeComplete, handleGradeUp, handleScarEarned, handleFleetArrived }
}

// ─── Composant Panel ──────────────────────────────────────────────────────────

export function NotificationPanel() {
  const [open, setOpen] = useState(false)
  const { notifications, markAllRead } = useGameStore()
  const panelRef = useRef<HTMLDivElement>(null)
  const unreadCount = notifications.filter(n => !n.read).length

  // Fermer au clic extérieur
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    if (open) document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  return (
    <div className="relative" ref={panelRef}>
      {/* Bouton cloche */}
      <button
        onClick={() => { setOpen(o => !o); if (!open) markAllRead() }}
        className="relative p-2 text-gray-400 hover:text-white transition-colors rounded-lg hover:bg-gray-700/50"
      >
        🔔
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-red-500 text-white text-xs flex items-center justify-center font-bold">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {/* Panel déroulant */}
      {open && (
        <div className="absolute right-0 top-10 w-80 max-h-96 overflow-y-auto rounded-xl bg-gray-800 border border-gray-700 shadow-2xl z-50">
          <div className="p-3 border-b border-gray-700 flex items-center justify-between">
            <span className="text-sm font-bold text-white">Notifications</span>
            {notifications.length > 0 && (
              <button onClick={() => useGameStore.getState().clearNotifications()} className="text-xs text-gray-400 hover:text-white">
                Effacer tout
              </button>
            )}
          </div>

          {notifications.length === 0 ? (
            <p className="p-4 text-gray-500 text-sm text-center">Aucune notification</p>
          ) : (
            <div className="divide-y divide-gray-700/50">
              {[...notifications].reverse().map(n => (
                <div key={n.id} className={`p-3 ${n.read ? 'opacity-60' : ''}`}>
                  <p className="text-sm font-medium text-white">{n.title}</p>
                  <p className="text-xs text-gray-400 mt-0.5">{n.message}</p>
                  <p className="text-xs text-gray-600 mt-1">
                    {n.timestamp.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
