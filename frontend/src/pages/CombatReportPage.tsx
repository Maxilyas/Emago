/**
 * pages/CombatReportPage.tsx — v3
 * Agent 6 — Sprint UX
 *
 * Améliorations :
 *   1. Résumé 3 lignes en haut : outcome · ressources pillées · XP max gagnée
 *   2. Vaisseaux nommés par "Type + Grade" au lieu de l'UUID
 *   3. Barre HP sparkline par vaisseau (hull_at_start → hull_at_end)
 *   4. Synergies expliquées en clair
 *   5. Section XP gagnée par vaisseau survivant
 */
import React from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { LoadingSpinner, EmptyState } from '@/components/ui'
import { fmt, fmtDate } from '@/lib/utils'

// ─── Types ────────────────────────────────────────────────────────────────────

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

interface RoundLog {
  round: number
  synergies?: string[]
  attackers_before?: Array<{ ship_id?: string; hull?: number; shield?: number; dps?: number }>
  defenders_before?: Array<{ ship_id?: string; hull?: number; shield?: number; dps?: number }>
  attackers_after?: Array<{ ship_id?: string; hull?: number; alive?: boolean }>
  defenders_after?: Array<{ ship_id?: string; hull?: number; alive?: boolean }>
  hits?: Array<{ attacker_id?: string; defender_id?: string; damage?: number }>
}

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

// ─── Helpers ─────────────────────────────────────────────────────────────────

const OUTCOME_CONFIG = {
  ATTACKER_WIN: { label: '⚔️ Victoire',  color: 'text-green-400', bg: 'bg-green-900/20 border-green-700/30' },
  DEFENDER_WIN: { label: '🛡️ Défaite',   color: 'text-red-400',   bg: 'bg-red-900/20 border-red-700/30'   },
  DRAW:         { label: '🤝 Match nul', color: 'text-yellow-400', bg: 'bg-yellow-900/20 border-yellow-700/30' },
}

const RARITY_COLOR: Record<string, string> = {
  COMMON: '#9E9E9E', UNCOMMON: '#4CAF50', RARE: '#2196F3', EPIC: '#9C27B0', LEGENDARY: '#FFD700',
}

const GRADE_NAMES = ['Recrue', 'Vétéran', 'Élite', 'Légion', 'Légende', 'Spectre']

function shipName(snap: ShipSnapshot): string {
  const type  = snap.ship_type.replace('_', ' ')
  const grade = GRADE_NAMES[snap.grade] ?? `G${snap.grade}`
  return `${type} ${grade}`
}

// Barre de HP horizontale
function HullBar({ start, end, destroyed }: { start: number; end: number; destroyed: boolean }) {
  const pct = destroyed || start === 0 ? 0 : Math.round((end / start) * 100)
  const color = destroyed ? '#ef4444' : pct > 60 ? '#22c55e' : pct > 30 ? '#f97316' : '#ef4444'
  return (
    <div className="mt-1.5">
      <div className="flex justify-between text-[10px] text-gray-500 mb-0.5">
        <span>❤️ {destroyed ? 0 : end} / {start}</span>
        <span>{pct}%</span>
      </div>
      <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
    </div>
  )
}

// Carte vaisseau dans le rapport
function ShipReportCard({ snap, side }: { snap: ShipSnapshot; side: 'attacker' | 'defender' }) {
  const rc          = RARITY_COLOR[snap.rarity] ?? '#9E9E9E'
  const borderColor = side === 'attacker' ? '#2196F3' : '#E53935'

  return (
    <div
      className={`rounded-xl p-3 border ${snap.destroyed ? 'opacity-50' : ''}`}
      style={{ background: 'rgba(13,18,30,0.8)', borderColor }}
    >
      <div className="flex items-center justify-between mb-1">
        <span className="text-[10px] font-bold uppercase tracking-wide" style={{ color: rc }}>
          {snap.rarity}
        </span>
        {snap.destroyed
          ? <span className="text-[10px] text-red-400 font-bold">💥 Détruit</span>
          : snap.xp_earned && snap.xp_earned > 0
            ? <span className="text-[10px] text-yellow-300">+{snap.xp_earned} XP</span>
            : null
        }
      </div>
      <p className="text-sm font-medium text-white">{shipName(snap)}</p>
      <p className="text-[10px] text-gray-500">Grade {snap.grade} · {snap.class}</p>
      <HullBar start={snap.hull_at_start} end={snap.hull_at_end} destroyed={snap.destroyed} />
      {snap.scar && <p className="text-[10px] text-orange-300 mt-1.5 italic">🩹 {snap.scar}</p>}
    </div>
  )
}

// ─── Composant principal ──────────────────────────────────────────────────────

export function CombatReportPage() {
  const { id }   = useParams<{ id: string }>()
  const navigate = useNavigate()

  const { data: report, isLoading, error } = useQuery<CombatReport>({
    queryKey: ['combat', id],
    queryFn:  () => api.get<CombatReport>(`/combat/${id}`),
    enabled:  !!id,
    retry:    false,
  })

  if (isLoading) return (
    <div className="flex items-center justify-center min-h-[60vh]"><LoadingSpinner /></div>
  )

  if (error || !report) return (
    <EmptyState
      icon="⚔️"
      title="Combat introuvable"
      message="Ce rapport n'existe pas ou vous n'êtes pas participant."
      action={
        <button onClick={() => navigate(-1)}
          className="mt-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded-lg transition-colors">
          ← Retour
        </button>
      }
    />
  )

  const outcome    = OUTCOME_CONFIG[report.outcome]
  const hasPillage = report.pillaged_metal > 0 || report.pillaged_crystal > 0 || report.pillaged_deuterium > 0

  // XP max gagnée (tous les survivants)
  const allSnaps  = [...report.attacker_ships_snapshot, ...report.defender_ships_snapshot]
  const maxXp     = Math.max(0, ...allSnaps.map(s => s.xp_earned ?? 0))
  const scarCount = allSnaps.filter(s => s.scar).length

  return (
    <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">

      {/* Bouton retour */}
      <button onClick={() => navigate(-1)} className="text-gray-400 hover:text-white text-sm transition-colors">
        ← Retour
      </button>

      {/* ── RÉSUMÉ 3 LIGNES ─────────────────────────────────────────────────── */}
      <div className={`rounded-2xl p-5 border ${outcome.bg}`}>
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div>
            <h1 className={`text-3xl font-bold ${outcome.color}`}>{outcome.label}</h1>
            <p className="text-gray-400 text-sm mt-1">{fmtDate(report.fought_at)}</p>
          </div>
          <div className="flex gap-6 text-center">
            <div>
              <p className="text-blue-400 text-xl font-bold font-mono">{fmt(report.attacker_power)}</p>
              <p className="text-gray-500 text-xs">Puissance attaquant</p>
            </div>
            <div className="text-gray-600 text-2xl self-center">⚔️</div>
            <div>
              <p className="text-red-400 text-xl font-bold font-mono">{fmt(report.defender_power)}</p>
              <p className="text-gray-500 text-xs">Puissance défenseur</p>
            </div>
          </div>
        </div>

        {/* Résumé compact */}
        <div className="flex flex-wrap gap-4 mt-4 text-sm">
          <span className="text-gray-300">
            🔢 <strong>{report.total_rounds}</strong> round{report.total_rounds > 1 ? 's' : ''}
          </span>
          {hasPillage && (
            <span className="text-yellow-300">
              💰 {[
                report.pillaged_metal     > 0 && `${fmt(report.pillaged_metal)} métal`,
                report.pillaged_crystal   > 0 && `${fmt(report.pillaged_crystal)} cristal`,
                report.pillaged_deuterium > 0 && `${fmt(report.pillaged_deuterium)} deut.`,
              ].filter(Boolean).join(' · ')} pillé{report.pillaged_metal > 0 ? '' : 's'}
            </span>
          )}
          {maxXp > 0 && (
            <span className="text-yellow-400">⭐ +{maxXp} XP (max)</span>
          )}
          {scarCount > 0 && (
            <span className="text-orange-300">🩹 {scarCount} cicatrice{scarCount > 1 ? 's' : ''} gagnée{scarCount > 1 ? 's' : ''}</span>
          )}
        </div>
      </div>

      {/* ── FLOTTES ──────────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <h2 className="text-blue-400 font-bold mb-3 text-sm uppercase tracking-wide">
            ⚔️ Flotte attaquante ({report.attacker_ships_snapshot.length})
          </h2>
          <div className="space-y-2">
            {report.attacker_ships_snapshot.map(s => (
              <ShipReportCard key={s.ship_id} snap={s} side="attacker" />
            ))}
          </div>
        </div>
        <div>
          <h2 className="text-red-400 font-bold mb-3 text-sm uppercase tracking-wide">
            🛡️ Flotte défenseure ({report.defender_ships_snapshot.length})
          </h2>
          <div className="space-y-2">
            {report.defender_ships_snapshot.map(s => (
              <ShipReportCard key={s.ship_id} snap={s} side="defender" />
            ))}
          </div>
        </div>
      </div>

      {/* ── ROUNDS ───────────────────────────────────────────────────────────── */}
      {report.rounds_log.length > 0 && (
        <div className="rounded-xl bg-gray-900/50 border border-gray-700 overflow-hidden">
          <h2 className="font-bold text-white p-4 border-b border-gray-700 text-sm uppercase tracking-wide">
            📋 Déroulement des rounds
          </h2>
          <div className="divide-y divide-gray-700/50 max-h-96 overflow-y-auto">
            {report.rounds_log.map((round) => (
              <div key={round.round} className="p-4 hover:bg-gray-700/10 transition-colors">

                {/* Titre round */}
                <div className="flex items-center justify-between mb-3">
                  <span className="font-bold text-white font-mono">Round {round.round}</span>
                  {round.synergies && round.synergies.length > 0 && (
                    <span className="text-cyan-400 text-xs">✨ {round.synergies.join(' · ')}</span>
                  )}
                </div>

                {/* Attaquants / défenseurs */}
                <div className="grid grid-cols-2 gap-3 text-xs mb-3">
                  <div>
                    <p className="text-blue-400 font-semibold mb-1">⚔️ Attaquants</p>
                    {(round.attackers_before ?? []).map((s, i) => (
                      <div key={i} className="flex justify-between bg-blue-900/10 rounded px-2 py-1 mb-0.5">
                        <span className="text-gray-400">❤️ {Math.round(s?.hull ?? 0)}</span>
                        <span className="text-orange-300">⚔️ {Math.round(s?.dps ?? 0)}</span>
                      </div>
                    ))}
                  </div>
                  <div>
                    <p className="text-red-400 font-semibold mb-1">🛡️ Défenseurs</p>
                    {(round.defenders_before ?? []).map((s, i) => (
                      <div key={i} className="flex justify-between bg-red-900/10 rounded px-2 py-1 mb-0.5">
                        <span className="text-gray-400">❤️ {Math.round(s?.hull ?? 0)}</span>
                        <span className="text-orange-300">⚔️ {Math.round(s?.dps ?? 0)}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Frappes */}
                {round.hits && round.hits.length > 0 && (
                  <div className="space-y-0.5 mb-2">
                    {round.hits.map((hit, i) => (
                      <p key={i} className="text-gray-500 text-[11px] font-mono">
                        ↳ -{Math.round(hit?.damage ?? 0)} dégâts
                      </p>
                    ))}
                  </div>
                )}

                {/* Destructions */}
                {(() => {
                  const ad = round.attackers_after?.filter(s => !s.alive).length ?? 0
                  const dd = round.defenders_after?.filter(s => !s.alive).length ?? 0
                  if (ad === 0 && dd === 0) return null
                  return (
                    <div className="flex gap-3 text-xs">
                      {ad > 0 && <span className="text-red-400">💥 {ad} attaquant{ad > 1 ? 's' : ''} détruit{ad > 1 ? 's' : ''}</span>}
                      {dd > 0 && <span className="text-red-400">💥 {dd} défenseur{dd > 1 ? 's' : ''} détruit{dd > 1 ? 's' : ''}</span>}
                    </div>
                  )
                })()}
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  )
}
