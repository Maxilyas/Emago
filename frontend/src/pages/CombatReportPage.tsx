/**
 * pages/CombatReportPage.tsx
 * Agent 6 — Développeur Frontend | Sprint 3
 *
 * Page dédiée au rapport de combat — route /combat/:id
 * Consomme GET /api/v1/combat/:id
 * Affiche : rounds, puissances, XP gagnée, cicatrices, butin pillé.
 *
 * Design Agent 4 : Dark UI, couleurs par camp (bleu attaquant / rouge défenseur)
 */
import React from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { LoadingSpinner, EmptyState, Badge } from '@/components/ui'
import { fmt, fmtDate } from '@/lib/utils'

// ─── Types ───────────────────────────────────────────────────────────────────

interface CombatReport {
  combat_id: string
  outcome: 'ATTACKER_WIN' | 'DEFENDER_WIN' | 'DRAW'
  fought_at: string
  attacker_power: number
  defender_power: number
  pillaged_metal: number
  pillaged_crystal: number
  pillaged_deuterium: number
  total_rounds: number
  rounds_log: RoundLog[]
  attacker_ships_snapshot: ShipSnapshot[]
  defender_ships_snapshot: ShipSnapshot[]
}

interface RoundLog {
  round: number
  synergies?: string[]
  attackers_before?: Array<{ ship_id: string; hull: number; shield: number; dps: number }>
  defenders_before?: Array<{ ship_id: string; hull: number; shield: number; dps: number }>
  attackers_after?: Array<{ ship_id: string; hull: number; alive: boolean }>
  defenders_after?: Array<{ ship_id: string; hull: number; alive: boolean }>
  hits?: Array<{ attacker_id: string; defender_id: string; damage: number }>
  // champs optionnels pour compatibilité future
  attacker_dps?: number
  defender_dps?: number
  ships_destroyed?: string[]
  xp_earned?: Record<string, number>
  scars_earned?: Array<{ ship_id: string; tag: string }>
}

interface ShipSnapshot {
  ship_id: string
  owner_id: string
  ship_type: string
  rarity: string
  grade: number
  class: string
  hull_at_start: number
  hull_at_end: number
  destroyed: boolean
  xp_earned?: number
  scar?: string
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

const OUTCOME_CONFIG = {
  ATTACKER_WIN: { label: 'Victoire attaquant', color: 'text-blue-400', bg: 'bg-blue-900/30' },
  DEFENDER_WIN: { label: 'Victoire défenseur', color: 'text-red-400', bg: 'bg-red-900/30' },
  DRAW:         { label: 'Match nul', color: 'text-yellow-400', bg: 'bg-yellow-900/30' },
}

const RARITY_COLOR: Record<string, string> = {
  COMMON: '#9E9E9E', UNCOMMON: '#4CAF50',
  RARE: '#2196F3', EPIC: '#9C27B0', LEGENDARY: '#FFD700',
}

function HullBar({ start, end, destroyed }: { start: number; end: number; destroyed: boolean }) {
  const pct = destroyed ? 0 : Math.round((end / start) * 100)
  return (
    <div className="w-full bg-gray-700 rounded-full h-1.5 mt-1">
      <div
        className={`h-1.5 rounded-full transition-all ${destroyed ? 'bg-red-600' : pct > 50 ? 'bg-green-500' : 'bg-orange-500'}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  )
}

function ShipCard({ snap, side }: { snap: ShipSnapshot; side: 'attacker' | 'defender' }) {
  const rarityColor = RARITY_COLOR[snap.rarity] || '#9E9E9E'
  const borderColor = side === 'attacker' ? '#2196F3' : '#E53935'
  return (
    <div
      className={`rounded-lg p-3 bg-gray-800/80 border ${snap.destroyed ? 'opacity-50' : ''}`}
      style={{ borderColor }}
    >
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-bold uppercase" style={{ color: rarityColor }}>
          {snap.rarity}
        </span>
        {snap.destroyed && (
          <span className="text-xs text-red-400 font-bold">💥 Détruit</span>
        )}
        {!snap.destroyed && snap.xp_earned && snap.xp_earned > 0 && (
          <span className="text-xs text-yellow-300">+{snap.xp_earned} XP</span>
        )}
      </div>
      <p className="text-sm text-white font-mono">{snap.ship_type.replace('_', ' ')}</p>
      <p className="text-xs text-gray-400">Grade {snap.grade}</p>
      <HullBar start={snap.hull_at_start} end={snap.hull_at_end} destroyed={snap.destroyed} />
      {snap.scar && (
        <p className="text-xs text-orange-300 mt-1 italic">🩹 {snap.scar}</p>
      )}
    </div>
  )
}

// ─── Composant principal ──────────────────────────────────────────────────────

export function CombatReportPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const { data: report, isLoading, error } = useQuery<CombatReport>({
    queryKey: ['combat', id],
    queryFn: () => api.get<CombatReport>(`/combat/${id}`),
    enabled: !!id,
    retry: false,
  })

  if (isLoading) return (
    <div className="flex items-center justify-center min-h-screen">
      <LoadingSpinner />
    </div>
  )

  if (error || !report) return (
    <EmptyState
      icon="⚔️"
      title="Combat introuvable"
      message="Ce rapport n'existe pas ou vous n'êtes pas participant."
      action={
        <button
          onClick={() => navigate(-1)}
          className="mt-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded-lg transition-colors"
        >
          ← Retour
        </button>
      }
    />
  )

  const outcome = OUTCOME_CONFIG[report.outcome]
  const hasPillage = report.pillaged_metal > 0 || report.pillaged_crystal > 0 || report.pillaged_deuterium > 0

  return (
    <div className="max-w-5xl mx-auto px-4 py-6 space-y-6">

      {/* ─── En-tête ───────────────────────────────────────────────── */}
      <div className={`rounded-xl p-5 ${outcome.bg} border border-gray-700`}>
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <h1 className={`text-2xl font-bold font-display ${outcome.color}`}>
              {outcome.label}
            </h1>
            <p className="text-gray-400 text-sm mt-1">{fmtDate(report.fought_at)}</p>
          </div>
          <div className="flex gap-4 text-center">
            <div>
              <p className="text-blue-400 text-xl font-bold">{fmt(report.attacker_power)}</p>
              <p className="text-gray-400 text-xs">Puissance attaquant</p>
            </div>
            <div className="text-gray-600 text-2xl self-center">⚔️</div>
            <div>
              <p className="text-red-400 text-xl font-bold">{fmt(report.defender_power)}</p>
              <p className="text-gray-400 text-xs">Puissance défenseur</p>
            </div>
          </div>
        </div>
        <p className="text-gray-300 text-sm mt-3">
          Combat résolu en <span className="text-white font-bold">{report.total_rounds}</span> rounds
        </p>
      </div>

      {/* ─── Butin pillé ───────────────────────────────────────────── */}
      {hasPillage && (
        <div className="rounded-xl p-4 bg-yellow-900/20 border border-yellow-700/40">
          <h2 className="text-yellow-300 font-bold mb-3">💰 Ressources pillées</h2>
          <div className="flex gap-6">
            {report.pillaged_metal > 0 && (
              <div><p className="text-white font-bold">{fmt(report.pillaged_metal)}</p><p className="text-gray-400 text-xs">Métal</p></div>
            )}
            {report.pillaged_crystal > 0 && (
              <div><p className="text-cyan-300 font-bold">{fmt(report.pillaged_crystal)}</p><p className="text-gray-400 text-xs">Cristal</p></div>
            )}
            {report.pillaged_deuterium > 0 && (
              <div><p className="text-green-300 font-bold">{fmt(report.pillaged_deuterium)}</p><p className="text-gray-400 text-xs">Deutérium</p></div>
            )}
          </div>
        </div>
      )}

      {/* ─── Flottes ───────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <h2 className="text-blue-400 font-bold mb-3 flex items-center gap-2">
            <span>⚔️</span> Flotte attaquante ({report.attacker_ships_snapshot.length} vaisseaux)
          </h2>
          <div className="space-y-2">
            {report.attacker_ships_snapshot.map(s => (
              <ShipCard key={s.ship_id} snap={s} side="attacker" />
            ))}
          </div>
        </div>
        <div>
          <h2 className="text-red-400 font-bold mb-3 flex items-center gap-2">
            <span>🛡️</span> Flotte défenseure ({report.defender_ships_snapshot.length} vaisseaux)
          </h2>
          <div className="space-y-2">
            {report.defender_ships_snapshot.map(s => (
              <ShipCard key={s.ship_id} snap={s} side="defender" />
            ))}
          </div>
        </div>
      </div>

      {/* ─── Log des rounds ────────────────────────────────────────── */}
      {report.rounds_log.length > 0 && (
        <div className="rounded-xl bg-gray-800/50 border border-gray-700 overflow-hidden">
          <h2 className="text-white font-bold p-4 border-b border-gray-700">📋 Déroulement des rounds</h2>
          <div className="divide-y divide-gray-700/50 max-h-96 overflow-y-auto">
            {report.rounds_log.map((round) => (
              <div key={round.round} className="p-3 hover:bg-gray-700/20 transition-colors">

                {/* Ligne titre du round */}
                <div className="flex items-center justify-between text-sm mb-2">
                  <span className="text-white font-bold font-mono">Round {round.round}</span>
                  {round.synergies && round.synergies.length > 0 && (
                    <span className="text-cyan-400 text-xs">✨ {round.synergies.join(' · ')}</span>
                  )}
                </div>

                {/* Tableau attaquants / défenseurs */}
                <div className="grid grid-cols-2 gap-2 text-xs mb-2">
                  {/* Attaquants avant le round */}
                  <div>
                    <p className="text-blue-400 font-semibold mb-1">⚔️ Attaquants</p>
                    {(round.attackers_before ?? []).map((s, i) => (
                      <div key={i} className="flex items-center justify-between bg-blue-900/10 rounded px-2 py-1 mb-0.5">
                        <span className="text-gray-300 font-mono text-[10px]">{s?.ship_id?.slice(0,6) ?? '?'}…</span>
                        <span className="text-blue-300">❤️ {Math.round(s?.hull ?? 0)}</span>
                        <span className="text-orange-300">⚔️ {Math.round(s?.dps ?? 0)}</span>
                      </div>
                    ))}
                  </div>
                  {/* Défenseurs avant le round */}
                  <div>
                    <p className="text-red-400 font-semibold mb-1">🛡️ Défenseurs</p>
                    {(round.defenders_before ?? []).map((s, i) => (
                      <div key={i} className="flex items-center justify-between bg-red-900/10 rounded px-2 py-1 mb-0.5">
                        <span className="text-gray-300 font-mono text-[10px]">{s?.ship_id?.slice(0,6) ?? '?'}…</span>
                        <span className="text-blue-300">❤️ {Math.round(s?.hull ?? 0)}</span>
                        <span className="text-orange-300">⚔️ {Math.round(s?.dps ?? 0)}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Frappes du round */}
                {round.hits && round.hits.length > 0 && (
                  <div className="mb-1">
                    {round.hits.map((hit, i) => (
                      <p key={i} className="text-gray-500 text-[10px]">
                        {hit?.attacker_id?.slice(0,6) ?? '?'}… → {hit?.defender_id?.slice(0,6) ?? '?'}… : -{Math.round(hit?.damage ?? 0)} dégâts
                      </p>
                    ))}
                  </div>
                )}

                {/* Résultat : destructions */}
                {(() => {
                  const attDestroyed = round.attackers_after?.filter(s => !s.alive).length ?? 0
                  const defDestroyed = round.defenders_after?.filter(s => !s.alive).length ?? 0
                  if (attDestroyed === 0 && defDestroyed === 0) return null
                  return (
                    <div className="flex gap-3 mt-1">
                      {attDestroyed > 0 && <p className="text-red-400 text-xs">💥 {attDestroyed} attaquant(s) détruit(s)</p>}
                      {defDestroyed > 0 && <p className="text-red-400 text-xs">💥 {defDestroyed} défenseur(s) détruit(s)</p>}
                    </div>
                  )
                })()}

              </div>
            ))}
          </div>
        </div>
      )}

      <button
        onClick={() => navigate(-1)}
        className="text-gray-400 hover:text-white transition-colors text-sm"
      >
        ← Retour
      </button>
    </div>
  )
}
