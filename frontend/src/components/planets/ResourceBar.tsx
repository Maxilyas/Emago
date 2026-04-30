/**
 * ResourceBar — affiche métal/cristal/deutérium avec interpolation client.
 * La production s'incrémente visuellement côté client.
 * Le serveur reste la source de vérité (synchro sur chaque GET /planets/:id).
 */
import React, { useState, useEffect, useRef } from 'react'
import { fmtShort, fmt, clamp } from '@/lib/utils'
import type { PlanetDetail } from '@/types'

interface ResourceBarProps {
  planet: PlanetDetail
}

interface ResourceState {
  metal: number
  crystal: number
  deuterium: number
}

export function ResourceBar({ planet }: ResourceBarProps) {
  const [res, setRes] = useState<ResourceState>({
    metal: planet.metal,
    crystal: planet.crystal,
    deuterium: planet.deuterium,
  })

  const lastSync  = useRef(Date.now())
  const rateRef   = useRef(planet.production_rates)
  const baseRef   = useRef<ResourceState>({ metal: planet.metal, crystal: planet.crystal, deuterium: planet.deuterium })

  // Sync quand la planète est rechargée depuis le serveur
  useEffect(() => {
    lastSync.current = Date.now()
    rateRef.current  = planet.production_rates
    baseRef.current  = { metal: planet.metal, crystal: planet.crystal, deuterium: planet.deuterium }
    setRes(baseRef.current)
  }, [planet.metal, planet.crystal, planet.deuterium])

  // Interpolation toutes les secondes
  useEffect(() => {
    const tick = () => {
      const elapsedH = (Date.now() - lastSync.current) / 3_600_000
      const rates    = rateRef.current
      const base     = baseRef.current
      setRes({
        metal:     clamp(base.metal     + rates.metal_per_hour     * elapsedH, 0, planet.metal_capacity),
        crystal:   clamp(base.crystal   + rates.crystal_per_hour   * elapsedH, 0, planet.crystal_capacity),
        deuterium: clamp(base.deuterium + rates.deuterium_per_hour * elapsedH, 0, planet.deut_capacity),
      })
    }
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [planet.metal_capacity, planet.crystal_capacity, planet.deut_capacity])

  const resources = [
    {
      key: 'metal',
      label: 'Métal',
      icon: '⛏️',
      value: res.metal,
      capacity: planet.metal_capacity,
      rate: planet.production_rates.metal_per_hour,
      color: '#94a3b8',
      bg: 'bg-slate-400',
    },
    {
      key: 'crystal',
      label: 'Cristal',
      icon: '💎',
      value: res.crystal,
      capacity: planet.crystal_capacity,
      rate: planet.production_rates.crystal_per_hour,
      color: '#7dd3fc',
      bg: 'bg-sky-300',
    },
    {
      key: 'deuterium',
      label: 'Deutérium',
      icon: '⚗️',
      value: res.deuterium,
      capacity: planet.deut_capacity,
      rate: planet.production_rates.deuterium_per_hour,
      color: '#86efac',
      bg: 'bg-green-300',
    },
  ] as const

  return (
    <div className="panel">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">Ressources</h2>
        <span className="text-xs text-gray-500">{planet.name}</span>
      </div>
      <div className="grid grid-cols-3 gap-3 sm:gap-4">
        {resources.map((r) => {
          const pct = Math.min(100, (r.value / r.capacity) * 100)
          const isFull = r.value >= r.capacity * 0.99
          return (
            <div key={r.key} className="text-center space-y-1.5">
              <div className="flex items-center justify-center gap-1">
                <span className="text-sm">{r.icon}</span>
                <span className="text-xs text-gray-400 hidden sm:inline">{r.label}</span>
              </div>
              <p className={`text-sm font-mono font-semibold ${isFull ? 'text-orange-400' : 'text-white'}`}>
                {fmtShort(r.value)}
              </p>
              {/* Barre de capacité */}
              <div className="h-1 bg-surface-border rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-1000"
                  style={{ width: `${pct}%`, backgroundColor: r.color }}
                />
              </div>
              <p className="text-xs text-gray-600">
                +{fmtShort(r.rate)}/h
              </p>
            </div>
          )
        })}
      </div>
      {planet.production_rates.energy_factor < 0.99 && (
        <div className="mt-3 text-xs text-orange-400 bg-orange-900/20 rounded px-2 py-1">
          ⚠️ Énergie insuffisante — production à {Math.round(planet.production_rates.energy_factor * 100)}%
        </div>
      )}
    </div>
  )
}
