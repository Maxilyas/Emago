/**
 * pages/CombatsPage.tsx — v3
 * Agent 6 — Développeur Frontend
 *
 * Fix :
 *  1. EmptyState : action doit être React.ReactNode, pas un objet {label, onClick}
 *  2. Notifications : type='combat' (pas 'combat.result'), timestamp=number (Date.now())
 *  3. data.combat_id depuis CombatResultData pour naviguer vers /combat/:id
 *  4. api.get<T>() retourne déjà le JSON parsé
 */
import React from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useGameStore } from '@/stores/gameStore'
import { LoadingSpinner, EmptyState } from '@/components/ui'
import { fmtDate, fmt } from '@/lib/utils'
import type { CombatResultData } from '@/types'

interface CombatSummary {
  combat_id: string
  outcome: 'ATTACKER_WIN' | 'DEFENDER_WIN' | 'DRAW'
  fought_at: string
  attacker_power: number
  defender_power: number
  total_rounds: number
}

const OUTCOME_CFG = {
  ATTACKER_WIN: { label: '⚔️ Victoire',  color: 'text-green-400',  bg: 'bg-green-900/20 border-green-700/40' },
  DEFENDER_WIN: { label: '🛡️ Défaite',   color: 'text-red-400',    bg: 'bg-red-900/20 border-red-700/40'    },
  DRAW:         { label: '🤝 Match nul', color: 'text-yellow-400', bg: 'bg-yellow-900/20 border-yellow-700/40' },
} as const

export function CombatsPage() {
  const navigate = useNavigate()

  // Notifications du vrai store — type='combat', timestamp=number, data=CombatResultData
  const notifications = useGameStore(s => s.notifications)
  const combatNotifs = notifications.filter(n => n.type === 'combat')

  // Historique depuis l'API — api.get<T>() retourne déjà le JSON parsé
  const { data: history, isLoading } = useQuery<CombatSummary[]>({
    queryKey: ['combat', 'history'],
    queryFn: () => api.get<CombatSummary[]>('/combat/history'),
    retry: false,
    staleTime: 60_000,
  })

  const hasHistory  = Array.isArray(history) && history.length > 0
  const hasNotifs   = combatNotifs.length > 0
  const isEmpty     = !isLoading && !hasHistory && !hasNotifs

  return (
    <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">

      {/* En-tête */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate('/dashboard')}
          className="text-gray-400 hover:text-white transition-colors text-lg leading-none"
          aria-label="Retour"
        >
          ←
        </button>
        <div>
          <h1 className="text-2xl font-bold text-white">⚔️ Combats</h1>
          <p className="text-sm text-gray-400">Vos rapports de combat récents</p>
        </div>
      </div>

      {/* Chargement */}
      {isLoading && <LoadingSpinner />}

      {/* Aucun combat — action est du JSX, pas un objet */}
      {isEmpty && (
        <EmptyState
          icon="🚀"
          title="Aucun combat récent"
          message="Vos rapports apparaîtront ici après vos premières batailles."
          action={
            <button
              onClick={() => navigate('/galaxy')}
              className="mt-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-lg font-medium transition-colors"
            >
              🌌 Aller à la Galaxie
            </button>
          }
        />
      )}

      {/* Combats reçus via WS cette session */}
      {hasNotifs && (
        <div>
          <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-3">
            Cette session
          </h2>
          <div className="space-y-2">
            {combatNotifs.map(n => {
              const d = n.data as CombatResultData | undefined
              const outcomeKey = d?.winner === 'ATTACKER' ? 'ATTACKER_WIN'
                               : d?.winner === 'DRAW'     ? 'DRAW'
                               : 'DEFENDER_WIN'
              const cfg = OUTCOME_CFG[outcomeKey]
              // timestamp est un number (Date.now())
              const time = new Date(n.timestamp).toLocaleTimeString('fr-FR', {
                hour: '2-digit', minute: '2-digit',
              })
              return (
                <button
                  key={n.id}
                  onClick={() => d?.combat_id && navigate(`/combat/${d.combat_id}`)}
                  className={`w-full text-left rounded-xl p-4 border transition-all hover:opacity-80 ${cfg.bg}`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className={`font-bold text-sm ${cfg.color}`}>{n.title}</p>
                      <p className="text-xs text-gray-400 mt-0.5 truncate">{n.message}</p>
                    </div>
                    <div className="text-right shrink-0">
                      <p className="text-xs text-gray-500">{time}</p>
                      {d?.combat_id && (
                        <p className="text-xs text-blue-400 mt-0.5">Rapport →</p>
                      )}
                    </div>
                  </div>
                </button>
              )
            })}
          </div>
        </div>
      )}

      {/* Historique depuis l'API */}
      {hasHistory && (
        <div>
          <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-widest mb-3">
            Historique
          </h2>
          <div className="space-y-2">
            {history!.map(combat => {
              const cfg = OUTCOME_CFG[combat.outcome] ?? OUTCOME_CFG.DRAW
              return (
                <button
                  key={combat.combat_id}
                  onClick={() => navigate(`/combat/${combat.combat_id}`)}
                  className={`w-full text-left rounded-xl p-4 border transition-all hover:opacity-80 ${cfg.bg}`}
                >
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <div>
                      <p className={`font-bold text-sm ${cfg.color}`}>{cfg.label}</p>
                      <p className="text-xs text-gray-400 mt-0.5">
                        {combat.total_rounds} rounds · {fmt(combat.attacker_power)} vs {fmt(combat.defender_power)}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-gray-500">{fmtDate(combat.fought_at)}</p>
                      <p className="text-xs text-blue-400 mt-0.5">Voir le rapport →</p>
                    </div>
                  </div>
                </button>
              )
            })}
          </div>
        </div>
      )}

    </div>
  )
}
