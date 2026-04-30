import React, { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { api } from '@/lib/api'
import { ApiError } from '@/lib/api'
import { planetsApi } from '@/api'
import { LoadingSpinner } from '@/components/ui'
import { fmt, fmtShort, fmtCountdown } from '@/lib/utils'

// ─── Types ────────────────────────────────────────────────────────────────────
interface UnlockInfo { level: number; unlock: string }
interface BuildingInfo {
  key: string; label: string; level: number
  icon: string; category: string
  description: string; per_level: string
  synergies: string[]; unlocks: UnlockInfo[]; tip: string
  cost_next: { metal: number; crystal: number; deuterium: number; seconds: number }
  in_queue: boolean; next_unlock: string | null
}
interface QueueItem {
  id: string; item_name: string; label: string
  target_level: number; completes_at: string; seconds_remaining: number
}
interface PlanetDetail {
  id: string; name: string; galaxy: number; system: number; position: number
  is_homeworld: boolean; metal: number; crystal: number; deuterium: number
  metal_capacity: number; crystal_capacity: number; deut_capacity: number
  buildings: BuildingInfo[]; production_rates: any; build_queue: QueueItem[]
}

// ─── Countdown ───────────────────────────────────────────────────────────────
function Countdown({ secs: initSecs, onDone }: { secs: number; onDone: () => void }) {
  const [s, setS] = useState(initSecs)
  useEffect(() => {
    setS(initSecs)
    if (initSecs <= 0) { onDone(); return }
    const start = Date.now()
    const id = setInterval(() => {
      const left = Math.max(0, initSecs - (Date.now() - start) / 1000)
      setS(Math.round(left))
      if (left <= 0) { clearInterval(id); onDone() }
    }, 1000)
    return () => clearInterval(id)
  }, [initSecs])
  if (s <= 0) return <span className="text-green-400 font-display text-sm">TERMINÉ ✓</span>
  return <span className="font-mono text-accent-blue">{fmtCountdown(s)}</span>
}

// ─── Building Card ────────────────────────────────────────────────────────────
function BuildingCard({ building, resources, onBuild, disabled }: {
  building: BuildingInfo
  resources: { metal: number; crystal: number; deuterium: number }
  onBuild: (key: string) => void
  disabled: boolean
}) {
  const [expanded, setExpanded] = useState(false)
  const cost = building.cost_next
  const canAfford = Math.floor(resources.metal) >= cost.metal
    && Math.floor(resources.crystal) >= cost.crystal
    && Math.floor(resources.deuterium) >= cost.deuterium
  const MAX_LEVEL = 20

  // Couleur par catégorie
  const catColor: Record<string, string> = {
    production: '#94a3b8',
    energy:     '#fbbf24',
    military:   '#2d7dd2',
    research:   '#7c3aed',
  }
  const color = catColor[building.category] ?? '#6b7280'

  return (
    <div
      className="rounded-xl border transition-all duration-200 overflow-hidden"
      style={{
        background: `linear-gradient(135deg, rgba(${hexToRgb(color)},0.06) 0%, rgba(13,18,30,0.9) 60%)`,
        borderColor: `rgba(${hexToRgb(color)},0.25)`,
      }}
    >
      {/* Header */}
      <div className="p-4">
        <div className="flex items-start gap-3 mb-3">
          <div className="h-11 w-11 rounded-xl flex items-center justify-center text-2xl shrink-0"
            style={{ background: `rgba(${hexToRgb(color)},0.12)`, border: `1px solid rgba(${hexToRgb(color)},0.25)` }}>
            {building.icon}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between gap-2">
              <p className="font-semibold text-white text-sm">{building.label}</p>
              {building.in_queue && (
                <span className="text-[10px] font-display px-2 py-0.5 rounded-full shrink-0"
                  style={{ color, background: `rgba(${hexToRgb(color)},0.15)`, border: `1px solid rgba(${hexToRgb(color)},0.3)` }}>
                  EN COURS
                </span>
              )}
            </div>
            <p className="text-[11px] text-gray-500 mt-0.5 leading-relaxed">{building.description}</p>
          </div>
        </div>

        {/* Barre de niveau */}
        <div className="mb-3">
          <div className="flex justify-between text-[10px] mb-1">
            <span className="font-display text-gray-400">NIVEAU {building.level}</span>
            <span className="text-gray-600">{building.level}/{MAX_LEVEL}</span>
          </div>
          <div className="h-1.5 bg-gray-800/60 rounded-full overflow-hidden">
            <div className="h-full rounded-full transition-all duration-700"
              style={{ width: `${(building.level / MAX_LEVEL) * 100}%`,
                background: `linear-gradient(90deg, rgba(${hexToRgb(color)},0.5), ${color})` }} />
          </div>
          <p className="text-[10px] text-gray-600 mt-1">{building.per_level}</p>
        </div>

        {/* Prochain unlock */}
        {building.next_unlock && !building.in_queue && (
          <div className="mb-3 px-2.5 py-2 rounded-lg text-xs flex items-start gap-2"
            style={{ background: `rgba(${hexToRgb(color)},0.08)`, border: `1px solid rgba(${hexToRgb(color)},0.2)` }}>
            <span className="shrink-0 mt-0.5">🔓</span>
            <span style={{ color }}>Niveau {building.level + 1} débloque : <strong>{building.next_unlock}</strong></span>
          </div>
        )}

        {/* Coûts + bouton */}
        {!building.in_queue && (
          <>
            <div className="flex flex-wrap gap-2 mb-3 text-xs">
              {cost.metal > 0 && (
                <span className={Math.floor(resources.metal) >= cost.metal ? 'text-gray-300' : 'text-red-400'}>
                  ⛏️ {fmt(cost.metal)}
                </span>
              )}
              {cost.crystal > 0 && (
                <span className={Math.floor(resources.crystal) >= cost.crystal ? 'text-gray-300' : 'text-red-400'}>
                  💎 {fmt(cost.crystal)}
                </span>
              )}
              {cost.deuterium > 0 && (
                <span className={Math.floor(resources.deuterium) >= cost.deuterium ? 'text-gray-300' : 'text-red-400'}>
                  ⚗️ {fmt(cost.deuterium)}
                </span>
              )}
              <span className="text-gray-600">⏱ {fmtCountdown(cost.seconds)}</span>
            </div>
            <button
              onClick={() => onBuild(building.key)}
              disabled={disabled || !canAfford}
              className="w-full py-2 rounded-lg text-xs font-display tracking-wider transition-all duration-200"
              style={canAfford && !disabled ? {
                background: `linear-gradient(135deg, rgba(${hexToRgb(color)},0.2), rgba(${hexToRgb(color)},0.08))`,
                border: `1px solid rgba(${hexToRgb(color)},0.4)`,
                color,
              } : { background: 'rgba(30,40,55,0.4)', border: '1px solid rgba(45,58,80,0.4)', color: '#374151' }}>
              {canAfford ? `AMÉLIORER → Niv.${building.level + 1}` : 'RESSOURCES INSUFFISANTES'}
            </button>
          </>
        )}

        {/* Bouton "voir détails" */}
        <button
          onClick={() => setExpanded(v => !v)}
          className="w-full mt-2 py-1.5 text-[10px] text-gray-600 hover:text-gray-400 transition-colors font-display tracking-wider">
          {expanded ? '▲ MASQUER' : '▼ SYNERGIES & INFOS'}
        </button>
      </div>

      {/* Panneau détails dépliable */}
      {expanded && (
        <div className="border-t px-4 py-3 space-y-3"
          style={{ borderColor: `rgba(${hexToRgb(color)},0.15)`, background: 'rgba(5,8,16,0.4)' }}>

          {/* Synergies */}
          {building.synergies.length > 0 && (
            <div>
              <p className="text-[10px] font-display tracking-wider text-gray-600 mb-2">SYNERGIES</p>
              <div className="space-y-1.5">
                {building.synergies.map((s, i) => (
                  <div key={i} className="flex items-start gap-2 text-xs text-gray-400">
                    <span className="text-cyan-500 shrink-0 mt-0.5">◆</span>
                    {s}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Tous les unlocks */}
          {building.unlocks.length > 0 && (
            <div>
              <p className="text-[10px] font-display tracking-wider text-gray-600 mb-2">DÉVERROUILLAGES</p>
              <div className="space-y-1.5">
                {building.unlocks.map((u) => (
                  <div key={u.level} className="flex items-start gap-2 text-xs">
                    <span className={`shrink-0 font-mono font-bold ${building.level >= u.level ? 'text-green-400' : 'text-gray-600'}`}>
                      Niv.{u.level}
                    </span>
                    <span className={building.level >= u.level ? 'text-gray-300 line-through opacity-50' : 'text-gray-400'}>
                      {u.unlock}
                    </span>
                    {building.level >= u.level && <span className="text-green-400 shrink-0">✓</span>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Astuce */}
          {building.tip && (
            <div className="flex items-start gap-2 p-2.5 rounded-lg"
              style={{ background: `rgba(${hexToRgb(color)},0.06)`, border: `1px solid rgba(${hexToRgb(color)},0.15)` }}>
              <span className="text-sm shrink-0">💡</span>
              <p className="text-xs italic" style={{ color }}>{building.tip}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function hexToRgb(hex: string): string {
  try {
    const r = parseInt(hex.slice(1, 3), 16)
    const g = parseInt(hex.slice(3, 5), 16)
    const b = parseInt(hex.slice(5, 7), 16)
    return `${r},${g},${b}`
  } catch { return '107,114,128' }
}

// ─── CATEGORIES ───────────────────────────────────────────────────────────────
const CATS = [
  { id: 'all',        label: 'TOUS' },
  { id: 'production', label: 'PRODUCTION' },
  { id: 'energy',     label: 'ÉNERGIE' },
  { id: 'military',   label: 'MILITAIRE' },
  { id: 'research',   label: 'RECHERCHE' },
]

// ─── Page principale ──────────────────────────────────────────────────────────
export function BuildingsPage() {
  const qc = useQueryClient()
  const [selectedPlanetId, setSelectedPlanetId] = useState('')
  const [category, setCategory] = useState('all')

  const { data: planets } = useQuery({ queryKey: ['planets'], queryFn: planetsApi.list })

  useEffect(() => {
    if (planets && planets.length > 0 && !selectedPlanetId) {
      setSelectedPlanetId(planets[0].id)
    }
  }, [planets, selectedPlanetId])

  const { data: planet, isLoading } = useQuery({
    queryKey: ['planet', selectedPlanetId],
    queryFn:  () => api.get<PlanetDetail>(`/planets/${selectedPlanetId}`),
    enabled:  !!selectedPlanetId,
    refetchInterval: 15_000,
  })

  const { mutate: buildBuilding, isPending } = useMutation({
    mutationFn: (building: string) => api.post<any>(`/planets/${selectedPlanetId}/build`, { building }),
    onSuccess: (res) => {
      const msg = res.next_unlock
        ? `🔓 ${res.label} → Niveau ${res.target_level} — Débloque : ${res.next_unlock}`
        : `✅ ${res.label} → Niveau ${res.target_level} en ${fmtCountdown(res.seconds)}`
      toast.success(msg, { duration: 6000 })
      qc.invalidateQueries({ queryKey: ['planet', selectedPlanetId] })
    },
    onError: (err) => toast.error(err instanceof ApiError ? err.detail : 'Erreur'),
  })

  const filtered = planet?.buildings.filter(b =>
    category === 'all' || b.category === category
  ) ?? []

  const resources = {
    metal:     planet?.metal     ?? 0,
    crystal:   planet?.crystal   ?? 0,
    deuterium: planet?.deuterium ?? 0,
  }

  // Indicateur d'énergie
  const energyFactor = planet?.production_rates?.energy_factor ?? 1
  const energyOk = energyFactor >= 0.99

  return (
    <div className="space-y-5 animate-fade-in pb-20 lg:pb-0">

      {/* Header */}
      <div>
        <p className="section-title mb-1">Infrastructure</p>
        <h1 className="text-2xl font-bold text-white">Bâtiments</h1>
      </div>

      {/* Sélecteur planète + ressources */}
      <div className="panel">
        <div className="flex flex-wrap items-center gap-2 mb-4">
          <p className="text-xs text-gray-600 shrink-0 font-display">PLANÈTE</p>
          {(planets ?? []).map(p => (
            <button key={p.id} onClick={() => setSelectedPlanetId(p.id)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-all"
              style={selectedPlanetId === p.id ? {
                background: 'rgba(45,125,210,0.15)', border: '1px solid rgba(45,125,210,0.4)', color: '#60a5fa',
              } : { background: 'rgba(20,28,42,0.6)', border: '1px solid rgba(35,50,70,0.6)', color: '#6b7280' }}>
              {p.is_homeworld ? '🏠' : '🪐'} {p.name}
            </button>
          ))}
        </div>

        {planet && (
          <>
            <div className="grid grid-cols-3 gap-4">
              {[
                { icon: '⛏️', label: 'Métal',     val: planet.metal,     cap: planet.metal_capacity,   color: '#94a3b8' },
                { icon: '💎', label: 'Cristal',   val: planet.crystal,   cap: planet.crystal_capacity, color: '#7dd3fc' },
                { icon: '⚗️', label: 'Deutérium', val: planet.deuterium, cap: planet.deut_capacity,    color: '#86efac' },
              ].map(r => {
                const pct = Math.min(100, (r.val / r.cap) * 100)
                const full = r.val >= r.cap * 0.99
                return (
                  <div key={r.label}>
                    <div className="flex items-center gap-1.5 mb-1">
                      <span className="text-sm">{r.icon}</span>
                      <span className="text-[10px] text-gray-600 uppercase tracking-wider">{r.label}</span>
                    </div>
                    <p className={`text-sm font-mono font-bold ${full ? 'text-orange-400' : 'text-white'}`}>
                      {fmtShort(r.val)}
                      {full && <span className="text-[9px] ml-1 text-orange-500">PLEIN</span>}
                    </p>
                    <div className="h-0.5 bg-gray-800 rounded-full mt-1 overflow-hidden">
                      <div className="h-full rounded-full" style={{ width: `${pct}%`, background: full ? '#f97316' : r.color }} />
                    </div>
                    <p className="text-[10px] text-gray-700 mt-0.5">+{fmtShort(planet.production_rates[r.label === 'Métal' ? 'metal_per_hour' : r.label === 'Cristal' ? 'crystal_per_hour' : 'deuterium_per_hour'])}/h</p>
                  </div>
                )
              })}
            </div>
            {!energyOk && (
              <div className="mt-3 flex items-center gap-2 text-xs text-orange-400 bg-orange-900/20 border border-orange-800/30 rounded-lg px-3 py-2">
                <span>⚡</span>
                <span>Énergie insuffisante — production à {Math.round(energyFactor * 100)}% — Améliorez la Centrale solaire !</span>
              </div>
            )}
          </>
        )}
      </div>

      {/* File de construction */}
      {planet?.build_queue && planet.build_queue.length > 0 && (
        <div>
          <p className="section-title mb-3">En construction</p>
          <div className="space-y-2">
            {planet.build_queue.map(item => {
              const cfg = planet.buildings.find(b => b.key === item.item_name)
              const catColor: Record<string, string> = { production: '#94a3b8', energy: '#fbbf24', military: '#2d7dd2', research: '#7c3aed' }
              const color = catColor[cfg?.category ?? 'production'] ?? '#6b7280'
              return (
                <div key={item.id} className="panel" style={{ borderColor: `rgba(${hexToRgb(color)},0.3)` }}>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2.5">
                      <span className="text-xl">{cfg?.icon ?? '🏗️'}</span>
                      <div>
                        <p className="text-sm font-semibold text-white">{item.label}</p>
                        <p className="text-xs text-gray-500">
                          Niv.{item.target_level - 1} → <span style={{ color }}>Niv.{item.target_level}</span>
                        </p>
                      </div>
                    </div>
                    <Countdown
                      secs={item.seconds_remaining}
                      onDone={() => {
                        qc.invalidateQueries({ queryKey: ['planet', selectedPlanetId] })
                        toast.success(`${item.label} terminé — Niveau ${item.target_level} !`)
                      }}
                    />
                  </div>
                  <div className="h-1.5 bg-gray-800/60 rounded-full overflow-hidden">
                    <div className="h-full rounded-full forge-active"
                      style={{ background: `linear-gradient(90deg, rgba(${hexToRgb(color)},0.5), ${color})`, width: '100%' }} />
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Filtres */}
      <div className="flex gap-2 flex-wrap">
        {CATS.map(cat => (
          <button key={cat.id} onClick={() => setCategory(cat.id)}
            className="px-3 py-1.5 rounded-lg text-[10px] font-display tracking-wider transition-all"
            style={category === cat.id ? {
              background: 'rgba(45,125,210,0.15)', border: '1px solid rgba(45,125,210,0.35)', color: '#60a5fa',
            } : { background: 'rgba(20,28,42,0.6)', border: '1px solid rgba(35,50,70,0.6)', color: '#6b7280' }}>
            {cat.label}
          </button>
        ))}
      </div>

      {/* Grille bâtiments */}
      {isLoading ? (
        <div className="flex justify-center py-16"><LoadingSpinner size="lg" /></div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map(b => (
            <BuildingCard key={b.key} building={b} resources={resources}
              onBuild={buildBuilding} disabled={isPending} />
          ))}
        </div>
      )}
    </div>
  )
}
