/**
 * CombatReport — affiche le résultat d'un combat reçu via WebSocket.
 * Sprint 4 : ajout prop onViewFull pour naviguer vers /combat/:id
 */
import React from 'react'
import { Modal, Badge } from '@/components/ui'
import { fmt, fmtShort } from '@/lib/utils'
import type { CombatResultData } from '@/types'

interface Props {
  data: CombatResultData | null
  onClose: () => void
  onViewFull?: () => void   // ← Sprint 4 : callback vers /combat/:id
}

export function CombatReport({ data, onClose, onViewFull }: Props) {
  if (!data) return null

  const won    = data.winner === 'ATTACKER'
  const draw   = data.winner === 'DRAW'
  const color  = won ? '#4CAF50' : draw ? '#FFD700' : '#ef4444'
  const title  = won ? '⚔️ Victoire !' : draw ? '⚔️ Match nul' : '⚔️ Défaite'

  const hasLoot = data.loot && (data.loot.metal || data.loot.crystal || data.loot.deuterium)

  return (
    <Modal open title={title} onClose={onClose} size="lg">
      {/* Résultat principal */}
      <div className="text-center mb-6">
        <div
          className="text-4xl font-bold mb-1"
          style={{ color }}
        >
          {title}
        </div>
        <p className="text-gray-400 text-sm">
          {data.total_rounds} round{data.total_rounds > 1 ? 's' : ''} •{' '}
          Puissance : {fmt(data.attacker_power)} vs {fmt(data.defender_power)}
        </p>
      </div>

      {/* Pertes */}
      {data.ships_lost && (
        <div className="panel mb-3">
          <h3 className="text-sm font-semibold text-gray-300 mb-2">Pertes</h3>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <p className="text-gray-500 text-xs mb-1">Attaquant</p>
              <p className="text-red-400">{data.ships_lost.attacker.length} vaisseau(x)</p>
            </div>
            <div>
              <p className="text-gray-500 text-xs mb-1">Défenseur</p>
              <p className="text-red-400">{data.ships_lost.defender.length} vaisseau(x)</p>
            </div>
          </div>
        </div>
      )}

      {/* Butin */}
      {hasLoot && (
        <div className="panel mb-3">
          <h3 className="text-sm font-semibold text-gray-300 mb-2">🏆 Butin pillé</h3>
          <div className="flex gap-4 text-sm">
            {data.loot.metal     && <span className="text-metal">⛏️ {fmt(data.loot.metal)}</span>}
            {data.loot.crystal   && <span className="text-crystal">💎 {fmt(data.loot.crystal)}</span>}
            {data.loot.deuterium && <span className="text-deuterium">⚗️ {fmt(data.loot.deuterium)}</span>}
          </div>
        </div>
      )}

      {/* XP diff */}
      {Object.keys(data.xp_diff).length > 0 && (
        <div className="panel mb-3">
          <h3 className="text-sm font-semibold text-gray-300 mb-2">⭐ XP gagnée</h3>
          <div className="space-y-1">
            {Object.entries(data.xp_diff).map(([shipId, xp]) => (
              <div key={shipId} className="flex justify-between text-xs">
                <span className="text-gray-400 font-mono">{shipId.slice(0, 8)}…</span>
                <span className="text-yellow-400">+{fmt(xp)} XP</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Montées de grade */}
      {data.grade_ups.length > 0 && (
        <div className="panel mb-3">
          <h3 className="text-sm font-semibold text-gray-300 mb-2">⬆️ Progression de grade</h3>
          {data.grade_ups.map((g, i) => (
            <p key={i} className="text-xs text-green-400">
              Grade {g.old_grade} → Grade {g.new_grade}
            </p>
          ))}
        </div>
      )}

      {/* Cicatrices */}
      {data.scars.length > 0 && (
        <div className="panel mb-3">
          <h3 className="text-sm font-semibold text-gray-300 mb-2">🩹 Cicatrices gagnées</h3>
          {data.scars.map((s, i) => (
            <p key={i} className="text-xs text-purple-300 italic">"{s.tag}"</p>
          ))}
        </div>
      )}

      {/* Synergies actives */}
      {(data.synergies.attacker.length > 0 || data.synergies.defender.length > 0) && (
        <div className="panel mb-4">
          <h3 className="text-sm font-semibold text-gray-300 mb-2">✨ Synergies actives</h3>
          {[...data.synergies.attacker, ...data.synergies.defender].map((s, i) => (
            <p key={i} className="text-xs text-cyan-400">{s}</p>
          ))}
        </div>
      )}

      {/* ── Boutons Sprint 4 ───────────────────────────────────────────────── */}
      <div className="flex gap-3">
        {/* Voir rapport complet → /combat/:id */}
        {onViewFull && (
          <button
            onClick={onViewFull}
            className="flex-1 py-2 rounded-lg border border-blue-500/40 text-blue-400 hover:bg-blue-900/20 text-sm font-medium transition-colors"
          >
            📋 Rapport complet
          </button>
        )}
        <button onClick={onClose} className="btn-primary flex-1">
          Fermer
        </button>
      </div>
    </Modal>
  )
}
