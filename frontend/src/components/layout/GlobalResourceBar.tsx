import React, { useState, useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useGameStore } from '@/stores/gameStore'
import { api } from '@/lib/api'
import { fmtShort, clamp } from '@/lib/utils'
import type { PlanetSummary, PlanetDetail } from '@/types'

export function GlobalResourceBar() {
  const { activePlanetId, setActivePlanetId } = useGameStore()

  const { data: planets = [] } = useQuery<PlanetSummary[]>({
    queryKey: ['planets'],
    queryFn: () => api.get<PlanetSummary[]>('/planets'),
    refetchInterval: 30_000,
    staleTime: 10_000,
  })

  // Auto-sélectionne la planète natale au premier chargement
  useEffect(() => {
    if (!activePlanetId && planets.length > 0) {
      const hw = planets.find((p) => p.is_homeworld) ?? planets[0]
      setActivePlanetId(hw.id)
    }
  }, [planets, activePlanetId, setActivePlanetId])

  const { data: planet } = useQuery<PlanetDetail>({
    queryKey: ['planet', activePlanetId],
    queryFn: () => api.get<PlanetDetail>(`/planets/${activePlanetId}`),
    enabled: !!activePlanetId,
    refetchInterval: 15_000,
    staleTime: 5_000,
  })

  // Interpolation temps réel
  const [res, setRes] = useState({ metal: 0, crystal: 0, deuterium: 0 })
  const lastSync = useRef(Date.now())
  const rateRef = useRef({ metal_per_hour: 0, crystal_per_hour: 0, deuterium_per_hour: 0, energy_factor: 1 })
  const baseRef = useRef({ metal: 0, crystal: 0, deuterium: 0 })
  const capRef = useRef({ metal: 1, crystal: 1, deut: 1 })

  useEffect(() => {
    if (!planet) return
    lastSync.current = Date.now()
    rateRef.current = planet.production_rates
    baseRef.current = { metal: planet.metal, crystal: planet.crystal, deuterium: planet.deuterium }
    capRef.current = { metal: planet.metal_capacity, crystal: planet.crystal_capacity, deut: planet.deut_capacity }
    setRes(baseRef.current)
  }, [planet?.metal, planet?.crystal, planet?.deuterium])

  useEffect(() => {
    if (!planet) return
    const id = setInterval(() => {
      const h = (Date.now() - lastSync.current) / 3_600_000
      const r = rateRef.current
      const b = baseRef.current
      const c = capRef.current
      setRes({
        metal:     clamp(b.metal     + r.metal_per_hour     * h, 0, c.metal),
        crystal:   clamp(b.crystal   + r.crystal_per_hour   * h, 0, c.crystal),
        deuterium: clamp(b.deuterium + r.deuterium_per_hour * h, 0, c.deut),
      })
    }, 1000)
    return () => clearInterval(id)
  }, [planet?.metal_capacity, planet?.crystal_capacity, planet?.deut_capacity])

  if (!planet || !activePlanetId) {
    return (
      <div className="flex items-center gap-2 text-xs text-gray-600 animate-pulse">
        <span className="text-sm">🪐</span>
        <span>Chargement…</span>
      </div>
    )
  }

  const energyWarn = planet.production_rates.energy_factor < 0.99

  return (
    <div className="flex items-center gap-2 sm:gap-4 min-w-0 overflow-x-auto">

      {/* Sélecteur de planète */}
      <select
        value={activePlanetId}
        onChange={(e) => setActivePlanetId(e.target.value)}
        className="shrink-0 text-xs rounded px-2 py-1 text-gray-300 cursor-pointer
                   border border-white/10 hover:border-accent-blue/40 transition-colors
                   focus:outline-none focus:border-accent-blue/60"
        style={{ background: 'rgba(45,125,210,0.08)' }}
      >
        {planets.map((p) => (
          <option key={p.id} value={p.id} style={{ background: '#0a0f1e' }}>
            {p.is_homeworld ? '🏠' : '🪐'} {p.name}
          </option>
        ))}
      </select>

      {/* Séparateur */}
      <div className="h-4 w-px bg-white/10 shrink-0 hidden sm:block" />

      {/* Ressources */}
      <div className="flex items-center gap-3 sm:gap-5 shrink-0">
        <ResourceItem
          icon="⛏️" value={res.metal}
          rate={planet.production_rates.metal_per_hour}
          capacity={planet.metal_capacity}
          color="#94a3b8"
        />
        <ResourceItem
          icon="💎" value={res.crystal}
          rate={planet.production_rates.crystal_per_hour}
          capacity={planet.crystal_capacity}
          color="#7dd3fc"
        />
        <ResourceItem
          icon="⚗️" value={res.deuterium}
          rate={planet.production_rates.deuterium_per_hour}
          capacity={planet.deut_capacity}
          color="#86efac"
        />
      </div>

      {/* Alerte énergie */}
      {energyWarn && (
        <span className="shrink-0 text-[11px] text-orange-400 font-medium bg-orange-900/20 px-2 py-0.5 rounded">
          ⚡ {Math.round(planet.production_rates.energy_factor * 100)}%
        </span>
      )}
    </div>
  )
}

function ResourceItem({
  icon, value, rate, capacity, color,
}: {
  icon: string
  value: number
  rate: number
  capacity: number
  color: string
}) {
  const isFull = value >= capacity * 0.99
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-sm leading-none">{icon}</span>
      <div className="flex flex-col leading-none">
        <span
          className="text-xs font-mono font-semibold"
          style={{ color: isFull ? '#fb923c' : '#fff' }}
        >
          {fmtShort(value)}
        </span>
        <span className="text-[10px] text-gray-500 hidden sm:block mt-0.5">
          +{fmtShort(rate)}/h
        </span>
      </div>
    </div>
  )
}
