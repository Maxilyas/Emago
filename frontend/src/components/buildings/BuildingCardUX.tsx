/**
 * pages/BuildingsPage.tsx — v2
 * Agent 6 — Sprint UX
 *
 * Améliorations :
 *   1. Tooltip "Pourquoi bloqué" sous chaque bouton de construction impossible
 *   2. Production marginale visible directement (+320 métal/h au niveau 6)
 *   3. Catégories visuelles : Production / Militaire / Recherche
 */
// Ce fichier est un PATCH partiel — il remplace uniquement la fonction BuildingCard
// et ajoute les imports nécessaires.
// Coller au-dessus de la définition de BuildingCard existante dans BuildingsPage.tsx

// ── À AJOUTER dans les imports ────────────────────────────────────────────────
// import { BuildingBlockedReason, ProductionDelta } from '@/components/buildings/BuildingTooltip'

// ── REMPLACER la fonction BuildingCard par celle-ci ──────────────────────────

import React from 'react'
import { fmt, fmtCountdown } from '@/lib/utils'
import { BuildingBlockedReason, ProductionDelta } from '@/components/buildings/BuildingTooltip'

// Catégories visuelles
const BUILDING_CATEGORY_COLOR: Record<string, { color: string; label: string }> = {
  production: { color: '#22c55e', label: 'Production'  },
  military:   { color: '#ef4444', label: 'Militaire'   },
  research:   { color: '#a855f7', label: 'Recherche'   },
  energy:     { color: '#f59e0b', label: 'Énergie'     },
  other:      { color: '#6b7280', label: 'Infrastructure' },
}

export function BuildingCardUX({
  building,
  planetResources,
  energyFactor,
  queueLength,
  maxQueue,
  onBuild,
  isBuildPending,
}: {
  building: any
  planetResources: { metal: number; crystal: number; deuterium: number }
  energyFactor: number
  queueLength: number
  maxQueue: number
  onBuild: (key: string) => void
  isBuildPending: boolean
}) {
  const cost     = building.cost_next
  const catCfg   = BUILDING_CATEGORY_COLOR[building.category] ?? BUILDING_CATEGORY_COLOR.other
  const hasSlot  = queueLength < maxQueue
  const canAfford = planetResources.metal    >= cost.metal
                 && planetResources.crystal  >= cost.crystal
                 && planetResources.deuterium >= cost.deuterium

  const canBuild  = hasSlot && canAfford && !building.in_queue

  return (
    <div
      className="rounded-xl border transition-all duration-200 overflow-hidden"
      style={{
        background: 'rgba(13,18,30,0.8)',
        borderColor: canBuild ? `${catCfg.color}30` : 'rgba(35,50,70,0.5)',
      }}
    >
      {/* Ligne de couleur catégorie */}
      <div className="h-0.5" style={{ background: catCfg.color, opacity: 0.6 }} />

      <div className="p-4">
        {/* Header */}
        <div className="flex items-start justify-between gap-2 mb-3">
          <div className="flex items-center gap-2">
            <span className="text-2xl">{building.icon}</span>
            <div>
              <p className="font-semibold text-white text-sm">{building.label}</p>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="text-[10px] px-1.5 py-0.5 rounded font-medium"
                  style={{ background: `${catCfg.color}15`, color: catCfg.color }}>
                  {catCfg.label}
                </span>
                <span className="text-xs text-gray-500">Nv. {building.level}</span>
              </div>
            </div>
          </div>
          {building.in_queue && (
            <span className="text-[10px] text-blue-400 border border-blue-800/50 rounded px-2 py-0.5 shrink-0">
              ⏳ En file
            </span>
          )}
        </div>

        {/* Description */}
        <p className="text-xs text-gray-400 mb-2 leading-relaxed">{building.description}</p>

        {/* Production marginale — la grande nouveauté UX */}
        {building.per_level && (
          <ProductionDelta
            perLevel={building.per_level}
            currentLevel={building.level}
            icon={building.icon}
          />
        )}

        {/* Coût du prochain niveau */}
        <div className="flex flex-wrap gap-2 mt-3 mb-3 text-xs">
          {cost.metal > 0 && (
            <span className={planetResources.metal >= cost.metal ? 'text-metal' : 'text-red-400'}>
              ⛏️ {fmt(cost.metal)}
            </span>
          )}
          {cost.crystal > 0 && (
            <span className={planetResources.crystal >= cost.crystal ? 'text-crystal' : 'text-red-400'}>
              💎 {fmt(cost.crystal)}
            </span>
          )}
          {cost.deuterium > 0 && (
            <span className={planetResources.deuterium >= cost.deuterium ? 'text-deuterium' : 'text-red-400'}>
              ⚗️ {fmt(cost.deuterium)}
            </span>
          )}
          <span className="text-gray-600">⏱ {fmtCountdown(cost.seconds)}</span>
        </div>

        {/* Bouton + raison de blocage */}
        <button
          className="w-full py-2 rounded-lg text-sm font-medium transition-all"
          disabled={!canBuild || isBuildPending}
          onClick={() => onBuild(building.key)}
          style={{
            background: canBuild
              ? `${catCfg.color}20`
              : 'rgba(20,28,42,0.4)',
            border: `1px solid ${canBuild ? catCfg.color + '50' : 'rgba(35,50,70,0.6)'}`,
            color: canBuild ? catCfg.color : '#4b5563',
            cursor: canBuild ? 'pointer' : 'not-allowed',
          }}
        >
          {building.in_queue
            ? '⏳ En construction'
            : canBuild
              ? `⬆️ Construire niveau ${building.level + 1}`
              : '🔒 Impossible'}
        </button>

        {/* Raisons de blocage — la nouveauté clé */}
        {!canBuild && !building.in_queue && (
          <BuildingBlockedReason
            building={building}
            planetResources={planetResources}
            energyFactor={energyFactor}
            hasQueueSlot={hasSlot}
          />
        )}
      </div>
    </div>
  )
}
