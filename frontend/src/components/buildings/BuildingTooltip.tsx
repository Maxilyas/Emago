/**
 * components/buildings/BuildingTooltip.tsx
 * Agent 6 — Sprint UX
 *
 * Composant tooltip "Pourquoi bloqué" pour les bâtiments.
 * Affiché sous le bouton de construction quand l'action est impossible.
 *
 * Usage dans BuildingsPage :
 *   <BuildingBlockedReason
 *     building={b}
 *     planetResources={{ metal, crystal, deuterium }}
 *     energyFactor={rates.energy_factor}
 *     hasQueueSlot={build_queue.length < MAX_QUEUE}
 *   />
 */
import React from 'react'
import { fmt } from '@/lib/utils'

interface BuildingInfo {
  key: string
  level: number
  in_queue: boolean
  cost_next: { metal: number; crystal: number; deuterium: number; seconds: number }
}

interface Props {
  building: BuildingInfo
  planetResources: { metal: number; crystal: number; deuterium: number }
  energyFactor: number
  hasQueueSlot: boolean
}

export function BuildingBlockedReason({ building, planetResources, energyFactor, hasQueueSlot }: Props) {
  const reasons: { icon: string; msg: string; color: string }[] = []

  if (building.in_queue) {
    reasons.push({ icon: '⏳', msg: 'Déjà en file de construction', color: 'text-blue-400' })
    return null // Pas besoin d'autres raisons
  }

  if (!hasQueueSlot) {
    reasons.push({ icon: '📋', msg: 'File de construction pleine', color: 'text-orange-400' })
  }

  const cost = building.cost_next
  if (planetResources.metal < cost.metal) {
    reasons.push({
      icon: '⛏️',
      msg: `Métal insuffisant — ${fmt(planetResources.metal)} / ${fmt(cost.metal)}`,
      color: 'text-red-400',
    })
  }
  if (planetResources.crystal < cost.crystal) {
    reasons.push({
      icon: '💎',
      msg: `Cristal insuffisant — ${fmt(planetResources.crystal)} / ${fmt(cost.crystal)}`,
      color: 'text-red-400',
    })
  }
  if (planetResources.deuterium < cost.deuterium) {
    reasons.push({
      icon: '⚗️',
      msg: `Deutérium insuffisant — ${fmt(planetResources.deuterium)} / ${fmt(cost.deuterium)}`,
      color: 'text-red-400',
    })
  }
  if (energyFactor < 0.5) {
    reasons.push({
      icon: '⚡',
      msg: 'Énergie trop basse — la production est réduite de plus de 50%. Construisez une centrale.',
      color: 'text-orange-400',
    })
  }

  if (reasons.length === 0) return null

  return (
    <div className="mt-2 space-y-1">
      {reasons.map((r, i) => (
        <p key={i} className={`text-[11px] flex items-start gap-1.5 ${r.color}`}>
          <span className="shrink-0">{r.icon}</span>
          <span>{r.msg}</span>
        </p>
      ))}
    </div>
  )
}

/**
 * FloatingBuildQueue — barre flottante en bas de l'écran
 * Affiche la construction en cours avec countdown.
 * À intégrer dans AppLayout pour être visible sur toutes les pages.
 *
 * Usage dans AppLayout :
 *   <FloatingBuildQueue />
 */
import { useQuery } from '@tanstack/react-query'
import { planetsApi } from '@/api'
import { fmtCountdown } from '@/lib/utils'
import { useState, useEffect } from 'react'

export function FloatingBuildQueue() {
  const { data: planets } = useQuery({
    queryKey: ['planets'],
    queryFn: planetsApi.list,
    refetchInterval: 15_000,
  })

  // Chercher la première construction en cours sur toutes les planètes
  // Note: on utilise build_queue depuis PlanetDetail, pas depuis PlanetSummary
  // Ce composant nécessite que les données de détail soient chargées
  // Pour l'instant, on affiche uniquement si on a les données

  if (!planets || planets.length === 0) return null

  // Placeholder — en phase 2, fetch le détail de la planète active
  // pour afficher la file de construction courante
  return null
}

/**
 * ProductionDelta — affiche le gain de production du prochain niveau
 * "+320 métal/h au niveau 6" directement sur la carte bâtiment.
 */
export function ProductionDelta({ perLevel, currentLevel, icon }: {
  perLevel: string  // ex: "+320 métal/h par niveau"
  currentLevel: number
  icon: string
}) {
  if (!perLevel) return null
  return (
    <p className="text-xs text-green-400 mt-1">
      {icon} {perLevel}
    </p>
  )
}
