/**
 * PlanetPage.tsx
 * Agent 6 — Frontend
 *
 * Vue principale d'une planète :
 * - Ressources avec interpolation temps réel
 * - Bâtiments avec niveau, coût, bouton construire
 * - File de construction avec countdown
 */
import React, { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { api } from '@/lib/api'
import { ApiError } from '@/lib/api'
import { LoadingSpinner, EmptyState } from '@/components/ui'
import { fmt, fmtShort, fmtCountdown, clamp } from '@/lib/utils'
import { useGameStore } from '@/stores/gameStore'

// ─── Types ────────────────────────────────────────────────────────────────────

interface ProductionRates {
  metal_per_hour: number
  crystal_per_hour: number
  deuterium_per_hour: number
  energy_produced: number
  energy_factor: number
}

interface BuildingInfo {
  key: string
  label: string
  level: number
  cost_next: { metal: number; crystal: number; deuterium: number; seconds: number }
  in_queue: boolean
}

interface QueueItem {
  id: string
  item_name: string
  label: string
  target_level: number
  completes_at: string
  seconds_remaining: number
}

interface PlanetDetail {
  id: string
  name: string
  galaxy: number
  system: number
  position: number
  is_homeworld: boolean
  metal: number
  crystal: number
  deuterium: number
  metal_capacity: number
  crystal_capacity: number
  deut_capacity: number
  buildings: BuildingInfo[]
  production_rates: ProductionRates
  build_queue: QueueItem[]
  resources_last_updated_at: string
}

// ─── Composant ResourceCounter ────────────────────────────────────────────────

function ResourceCounter({
  value, capacity, ratePerHour, color, icon, label,
}: {
  value: number; capacity: number; ratePerHour: number
  color: string; icon: string; label: string
}) {
  const [current, setCurrent] = useState(value)
  const baseRef    = useRef(value)
  const startedRef = useRef(Date.now())
  const rateRef    = useRef(ratePerHour)

  useEffect(() => {
    baseRef.current    = value
    startedRef.current = Date.now()
    rateRef.current    = ratePerHour
    setCurrent(value)
  }, [value, ratePerHour])

  useEffect(() => {
    const id = setInterval(() => {
      const elapsedH = (Date.now() - startedRef.current) / 3_600_000
      setCurrent(clamp(baseRef.current + rateRef.current * elapsedH, 0, capacity))
    }, 1000)
    return () => clearInterval(id)
  }, [capacity])

  const pct = Math.min(100, (current / capacity) * 100)
  const full = current >= capacity * 0.99

  return (
    <div className="flex-1 min-w-0">
      <div className="flex items-center gap-1.5 mb-1">
        <span className="text-base">{icon}</span>
        <span className="text-xs text-gray-400">{label}</span>
      </div>
      <p className={`text-lg font-mono font-bold ${full ? 'text-orange-400' : 'text-white'}`}>
        {fmtShort(current)}
        {full && <span className="text-xs ml-1">MAX</span>}
      </p>
      <div className="h-1 bg-surface-border rounded-full mt-1 overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-1000"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      <p className="text-xs text-gray-600 mt-0.5">+{fmtShort(ratePerHour)}/h</p>
    </div>
  )
}

// ─── Composant BuildQueueBar ──────────────────────────────────────────────────

function BuildQueueBar({ item, onComplete }: { item: QueueItem; onComplete: () => void }) {
  const [secs, setSecs] = useState(item.seconds_remaining)
  const startRef  = useRef(Date.now())
  const initialRef = useRef(item.seconds_remaining)
  const doneRef   = useRef(false)

  useEffect(() => {
    setSecs(item.seconds_remaining)
    startRef.current   = Date.now()
    initialRef.current = item.seconds_remaining
    doneRef.current    = false
  }, [item.id, item.seconds_remaining])

  useEffect(() => {
    const id = setInterval(() => {
      const elapsed = (Date.now() - startRef.current) / 1000
      const left = Math.max(0, initialRef.current - elapsed)
      setSecs(Math.round(left))
      if (left <= 0 && !doneRef.current) {
        doneRef.current = true
        onComplete()
      }
    }, 1000)
    return () => clearInterval(id)
  }, [onComplete])

  const pct = initialRef.current > 0
    ? Math.round(((initialRef.current - secs) / initialRef.current) * 100)
    : 100

  return (
    <div className="panel bg-blue-900/20 border-blue-800/50">
      <div className="flex items-center justify-between mb-2">
        <div>
          <span className="text-sm font-medium">🔨 {item.label}</span>
          <span className="text-xs text-gray-400 ml-2">→ Niveau {item.target_level}</span>
        </div>
        <span className="text-sm font-mono text-blue-400">{fmtCountdown(secs)}</span>
      </div>
      <div className="h-2 bg-surface-border rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-1000 bg-blue-500"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}

// ─── Composant BuildingCard ───────────────────────────────────────────────────

const BUILDING_ICONS: Record<string, string> = {
  metal_mine:            '⛏️',
  crystal_mine:          '💎',
  deuterium_synthesizer: '⚗️',
  solar_plant:           '☀️',
  shipyard:              '🚀',
  research_lab:          '🔬',
}

function BuildingCard({
  building, planetResources, onBuild, disabled,
}: {
  building: BuildingInfo
  planetResources: { metal: number; crystal: number; deuterium: number }
  onBuild: (key: string) => void
  disabled: boolean
}) {
  const cost   = building.cost_next
  const canAfford = (
    planetResources.metal     >= cost.metal &&
    planetResources.crystal   >= cost.crystal &&
    planetResources.deuterium >= cost.deuterium
  )

  return (
    <div className={`panel transition-all ${building.in_queue ? 'border-blue-700/50 bg-blue-900/10' : ''}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="text-2xl">{BUILDING_ICONS[building.key] ?? '🏗️'}</span>
          <div>
            <p className="font-semibold text-sm">{building.label}</p>
            <p className="text-xs text-gray-400">Niveau {building.level}</p>
          </div>
        </div>

        {building.in_queue ? (
          <span className="text-xs text-blue-400 bg-blue-900/30 px-2 py-1 rounded">En cours</span>
        ) : (
          <button
            onClick={() => onBuild(building.key)}
            disabled={disabled || !canAfford}
            className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-all ${
              canAfford && !disabled
                ? 'bg-accent-blue hover:bg-blue-500 text-white'
                : 'bg-surface-tertiary text-gray-600 cursor-not-allowed'
            }`}
            title={!canAfford ? 'Ressources insuffisantes' : `Améliorer → Niveau ${building.level + 1}`}
          >
            Améliorer
          </button>
        )}
      </div>

      {/* Coût */}
      {!building.in_queue && (
        <div className="mt-3 pt-3 border-t border-surface-border flex flex-wrap gap-3 text-xs">
          {cost.metal > 0 && (
            <span className={planetResources.metal >= cost.metal ? 'text-gray-300' : 'text-red-400'}>
              ⛏️ {fmt(cost.metal)}
            </span>
          )}
          {cost.crystal > 0 && (
            <span className={planetResources.crystal >= cost.crystal ? 'text-gray-300' : 'text-red-400'}>
              💎 {fmt(cost.crystal)}
            </span>
          )}
          {cost.deuterium > 0 && (
            <span className={planetResources.deuterium >= cost.deuterium ? 'text-gray-300' : 'text-red-400'}>
              ⚗️ {fmt(cost.deuterium)}
            </span>
          )}
          <span className="text-gray-600">⏱️ {fmtCountdown(cost.seconds)}</span>
        </div>
      )}
    </div>
  )
}

// ─── Page principale ──────────────────────────────────────────────────────────

export function PlanetPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { setActivePlanetId } = useGameStore()

  // Synchronise la planète active avec la barre de ressources globale
  useEffect(() => { if (id) setActivePlanetId(id) }, [id, setActivePlanetId])

  const { data: planet, isLoading } = useQuery({
    queryKey: ['planet', id],
    queryFn: () => api.get<PlanetDetail>(`/planets/${id}`),
    enabled: !!id,
    refetchInterval: 30_000,
  })

  const { mutate: buildBuilding, isPending } = useMutation({
    mutationFn: (building: string) =>
      api.post<{ label: string; target_level: number; seconds: number }>(
        `/planets/${id}/build`, { building }
      ),
    onSuccess: (res) => {
      toast.success(`Construction lancée : ${res.label} → Niveau ${res.target_level}`, { duration: 5000 })
      qc.invalidateQueries({ queryKey: ['planet', id] })
    },
    onError: (err) => toast.error(err instanceof ApiError ? err.detail : 'Erreur'),
  })

  if (isLoading) return <div className="flex justify-center py-20"><LoadingSpinner size="lg" /></div>
  if (!planet)   return <p className="text-center text-gray-400 py-20">Planète introuvable</p>

  const resources = { metal: planet.metal, crystal: planet.crystal, deuterium: planet.deuterium }

  return (
    <div className="space-y-5 pb-20 lg:pb-0">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button onClick={() => navigate('/dashboard')} className="text-gray-400 hover:text-white">←</button>
        <div>
          <h1 className="text-xl font-bold text-white">
            {planet.name}
            {planet.is_homeworld && <span className="ml-2 text-xs text-yellow-400 bg-yellow-900/30 px-2 py-0.5 rounded">🏠 Natale</span>}
          </h1>
          <p className="text-xs text-gray-500">
            Galaxie {planet.galaxy} · Système {planet.system} · Position {planet.position}
          </p>
        </div>
      </div>

      {/* Ressources */}
      <div className="panel">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">Ressources</h2>
          {planet.production_rates.energy_factor < 0.99 && (
            <span className="text-xs text-orange-400">⚡ Énergie {Math.round(planet.production_rates.energy_factor * 100)}%</span>
          )}
        </div>
        <div className="flex gap-4">
          <ResourceCounter value={planet.metal}     capacity={planet.metal_capacity}   ratePerHour={planet.production_rates.metal_per_hour}     color="#94a3b8" icon="⛏️" label="Métal" />
          <ResourceCounter value={planet.crystal}   capacity={planet.crystal_capacity} ratePerHour={planet.production_rates.crystal_per_hour}   color="#7dd3fc" icon="💎" label="Cristal" />
          <ResourceCounter value={planet.deuterium} capacity={planet.deut_capacity}    ratePerHour={planet.production_rates.deuterium_per_hour} color="#86efac" icon="⚗️" label="Deutérium" />
        </div>
      </div>

      {/* File de construction */}
      {planet.build_queue.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">En construction</h2>
          <div className="space-y-2">
            {planet.build_queue.map((item) => (
              <BuildQueueBar
                key={item.id}
                item={item}
                onComplete={() => {
                  qc.invalidateQueries({ queryKey: ['planet', id] })
                  toast.success(`${item.label} terminé — Niveau ${item.target_level} !`)
                }}
              />
            ))}
          </div>
        </div>
      )}

      {/* Bâtiments */}
      <div>
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">Bâtiments</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {planet.buildings.map((b) => (
            <BuildingCard
              key={b.key}
              building={b}
              planetResources={resources}
              onBuild={(key) => buildBuilding(key)}
              disabled={isPending}
            />
          ))}
        </div>
      </div>

      {/* Lien vers hangar avec cette planète sélectionnée */}
      {planet.buildings.find(b => b.key === 'shipyard' && b.level > 0) && (
        <div className="panel border-accent-blue/30 bg-accent-blue/5">
          <p className="text-sm text-gray-300 mb-3">
            🚀 Chantier naval niveau {planet.buildings.find(b => b.key === 'shipyard')?.level} disponible
          </p>
          <Link
            to={`/hangar?planet=${planet.id}`}
            className="btn-primary text-sm"
          >
            Construire des vaisseaux ici
          </Link>
        </div>
      )}
    </div>
  )
}
