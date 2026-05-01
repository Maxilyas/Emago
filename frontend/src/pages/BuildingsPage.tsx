import React, { useState, useEffect, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import toast from 'react-hot-toast'
import { api } from '@/lib/api'
import { ApiError } from '@/lib/api'
import { planetsApi } from '@/api'
import { LoadingSpinner } from '@/components/ui'
import { fmt, fmtShort, fmtCountdown } from '@/lib/utils'
import { BuildingBlockedReason, ProductionDelta } from '@/components/buildings/BuildingTooltip'
import { BuildingCardUX } from '@/components/buildings/BuildingCardUX'

// ─── Types ────────────────────────────────────────────────────────────────────
interface UnlockInfo { level: number; unlock: string }
interface BuildingInfo {
  key: string; label: string; level: number; icon: string; category: string
  description: string; per_level: string; synergies: string[]
  unlocks: UnlockInfo[]; tip: string
  cost_next: { metal: number; crystal: number; deuterium: number; seconds: number }
  in_queue: boolean; next_unlock: string | null
}
interface QueueItem {
  id: string; item_name: string; label: string
  target_level: number; completes_at: string; seconds_remaining: number
}
interface PlanetDetail {
  id: string; name: string; is_homeworld: boolean
  metal: number; crystal: number; deuterium: number
  metal_capacity: number; crystal_capacity: number; deut_capacity: number
  buildings: BuildingInfo[]
  production_rates: { metal_per_hour: number; crystal_per_hour: number; deuterium_per_hour: number; energy_produced: number; energy_factor: number }
  build_queue: QueueItem[]
}

function hexToRgb(hex: string) {
  try { return `${parseInt(hex.slice(1,3),16)},${parseInt(hex.slice(3,5),16)},${parseInt(hex.slice(5,7),16)}` }
  catch { return '107,114,128' }
}

// ─── Countdown inline ────────────────────────────────────────────────────────
function Countdown({ secs: initSecs, onDone }: { secs: number; onDone: () => void }) {
  const [s, setS] = useState(initSecs)
  useEffect(() => {
    setS(initSecs); if (initSecs <= 0) { onDone(); return }
    const start = Date.now()
    const id = setInterval(() => {
      const left = Math.max(0, initSecs - (Date.now() - start) / 1000)
      setS(Math.round(left)); if (left <= 0) { clearInterval(id); onDone() }
    }, 1000)
    return () => clearInterval(id)
  }, [initSecs])
  if (s <= 0) return <span className="text-green-400 font-display text-xs">TERMINÉ ✓</span>
  return <span className="font-mono text-accent-blue text-xs">{fmtCountdown(s)}</span>
}

// ─── Jauges d'énergie ────────────────────────────────────────────────────────
function EnergyGauge({ buildings, rates }: { buildings: BuildingInfo[]; rates: any }) {
  if (!rates) return null
  const energyProd = rates.energy_produced
  const factor = rates.energy_factor
  const shortage = factor < 0.99

  const mines = [
    { key: 'metal_mine',            label: 'Mine métal',  consumption: 10, color: '#94a3b8' },
    { key: 'crystal_mine',          label: 'Mine cristal', consumption: 10, color: '#7dd3fc' },
    { key: 'deuterium_synthesizer', label: 'Synthétiseur', consumption: 20, color: '#86efac' },
  ]

  const totalConsumption = mines.reduce((acc, m) => {
    const b = buildings.find(b => b.key === m.key)
    return acc + (b?.level ?? 0) * m.consumption
  }, 0)

  return (
    <div className="panel" style={{ borderColor: shortage ? 'rgba(249,115,22,0.4)' : 'rgba(251,191,36,0.2)' }}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-lg">⚡</span>
          <p className="text-sm font-semibold text-white">Bilan énergétique</p>
        </div>
        <span className={`text-sm font-mono font-bold ${shortage ? 'text-orange-400' : 'text-yellow-400'}`}>
          {Math.round(energyProd)} / {totalConsumption}
        </span>
      </div>

      <div className="h-3 bg-gray-800 rounded-full overflow-hidden mb-3">
        <div
          className="h-full rounded-full transition-all duration-700 relative overflow-hidden"
          style={{
            width: `${Math.min(100, (energyProd / Math.max(totalConsumption, 1)) * 100)}%`,
            background: shortage ? 'linear-gradient(90deg, #ef4444, #f97316)' : 'linear-gradient(90deg, #fbbf24, #f59e0b)',
          }}
        >
          <div className="absolute inset-0 shimmer opacity-30" />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs">
        <div>
          <p className="text-gray-600 mb-1">Production</p>
          <div className="flex items-center gap-1.5">
            <div className="h-2 w-2 rounded-full bg-yellow-400" style={{ boxShadow: '0 0 4px rgba(251,191,36,0.8)' }} />
            <span className="text-yellow-400 font-mono">+{Math.round(energyProd)}</span>
            <span className="text-gray-600">(Centrale Niv.{buildings.find(b=>b.key==='solar_plant')?.level ?? 0})</span>
          </div>
        </div>
        <div>
          <p className="text-gray-600 mb-1">Consommation</p>
          {mines.map(m => {
            const lvl = buildings.find(b => b.key === m.key)?.level ?? 0
            const cons = lvl * m.consumption
            if (cons === 0) return null
            return (
              <div key={m.key} className="flex items-center gap-1.5 mb-0.5">
                <div className="h-1.5 w-1.5 rounded-full" style={{ background: m.color }} />
                <span style={{ color: m.color }}>-{cons}</span>
                <span className="text-gray-600">{m.label}</span>
              </div>
            )
          })}
        </div>
      </div>

      {shortage && (
        <div className="mt-3 text-xs text-orange-400 flex items-start gap-2 bg-orange-900/15 rounded-lg p-2">
          <span>⚠️</span>
          <span>Production réduite à {Math.round(factor * 100)}% — Améliorez la Centrale solaire !</span>
        </div>
      )}
    </div>
  )
}

// ─── Zone Chantier Naval ─────────────────────────────────────────────────────
const SHIP_REQUIREMENTS: Record<string, number> = {
  'Frégate Attaque': 1, 'Frégate Défense': 1, 'Frégate Soutien': 1,
  'Frégate Exploration': 2, 'Croiseur Attaque': 4, 'Croiseur Défense': 4,
}
const SHIP_TYPES_BY_LEVEL = [
  { level: 1, ships: ['Frégate Attaque', 'Frégate Défense', 'Frégate Soutien'], icons: ['⚔️', '🛡️', '💊'] },
  { level: 2, ships: ['Frégate Exploration'], icons: ['🔭'] },
  { level: 4, ships: ['Croiseur Attaque', 'Croiseur Défense'], icons: ['⚔️⚔️', '🛡️🛡️'] },
]

// FIX : ajout de queueLength dans les props
function ShipyardZone({ building, resources, onBuild, disabled, queueLength }: {
  building: BuildingInfo; resources: any; onBuild: (key: string) => void; disabled: boolean; queueLength: number
}) {
  const lvl = building.level
  const cost = building.cost_next
  const canAfford = Math.floor(resources.metal) >= cost.metal
    && Math.floor(resources.crystal) >= cost.crystal
    && Math.floor(resources.deuterium) >= cost.deuterium
  const hasSlot = queueLength < 5
  const canBuild = canAfford && hasSlot && !building.in_queue

  return (
    <div className="rounded-2xl overflow-hidden"
      style={{ background: 'linear-gradient(135deg, rgba(45,125,210,0.08) 0%, rgba(13,18,30,0.95) 60%)', border: '1px solid rgba(45,125,210,0.2)' }}>
      <div className="h-px" style={{ background: 'linear-gradient(90deg, transparent, rgba(45,125,210,0.6), transparent)' }} />
      <div className="p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="h-12 w-12 rounded-xl flex items-center justify-center text-2xl"
              style={{ background: 'rgba(45,125,210,0.12)', border: '1px solid rgba(45,125,210,0.3)' }}>🏭</div>
            <div>
              <p className="font-semibold text-white">{building.label}</p>
              <p className="text-accent-blue font-display text-sm">NIVEAU {lvl}</p>
            </div>
          </div>
          <Link to="/hangar" className="btn-primary text-xs py-1.5 px-3">
            🚀 Hangar →
          </Link>
        </div>

        {/* Types débloqués */}
        <div className="space-y-2 mb-4">
          {SHIP_TYPES_BY_LEVEL.map(tier => (
            <div key={tier.level}
              className={`flex items-center gap-3 p-2.5 rounded-lg ${lvl >= tier.level ? '' : 'opacity-40'}`}
              style={lvl >= tier.level ? { background: 'rgba(45,125,210,0.08)', border: '1px solid rgba(45,125,210,0.2)' } : { background: 'rgba(20,28,42,0.4)', border: '1px dashed rgba(35,50,70,0.6)' }}>
              <span className={`text-[10px] font-display px-2 py-0.5 rounded-full shrink-0 ${lvl >= tier.level ? 'text-green-400 bg-green-900/20 border border-green-800/40' : 'text-gray-600 bg-gray-900/40 border border-gray-800/40'}`}>
                {lvl >= tier.level ? '✓' : `Niv.${tier.level}`}
              </span>
              <div className="flex gap-2 flex-wrap">
                {tier.ships.map((ship, i) => (
                  <span key={ship} className={`text-xs ${lvl >= tier.level ? 'text-white' : 'text-gray-600'}`}>
                    {tier.icons[i]} {ship}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Amélioration */}
        {!building.in_queue && lvl < 8 && (
          <>
            <div className="flex flex-wrap gap-2 mb-2 text-xs">
              {cost.metal > 0 && <span className={canAfford ? 'text-gray-400' : 'text-red-400'}>⛏️ {fmt(cost.metal)}</span>}
              {cost.crystal > 0 && <span className={canAfford ? 'text-gray-400' : 'text-red-400'}>💎 {fmt(cost.crystal)}</span>}
              {cost.deuterium > 0 && <span className={canAfford ? 'text-gray-400' : 'text-red-400'}>⚗️ {fmt(cost.deuterium)}</span>}
              <span className="text-gray-600">⏱ {fmtCountdown(cost.seconds)}</span>
            </div>
            <button onClick={() => onBuild(building.key)} disabled={disabled || !canAfford}
              className="w-full py-2 rounded-lg text-xs font-display tracking-wider transition-all"
              style={canAfford ? { background: 'rgba(45,125,210,0.15)', border: '1px solid rgba(45,125,210,0.4)', color: '#60a5fa' }
                               : { background: 'rgba(30,40,55,0.4)', border: '1px solid rgba(45,58,80,0.4)', color: '#374151' }}>
              {canAfford ? `AMÉLIORER → Niv.${lvl + 1}` : 'RESSOURCES INSUFFISANTES'}
            </button>
          </>
        )}
        {building.in_queue && <p className="text-xs text-center text-accent-blue font-display">EN CONSTRUCTION...</p>}
      </div>
    </div>
  )
}

// ─── Composant bâtiment standard ──────────────────────────────────────────────
function BuildingCard({ building, resources, onBuild, disabled, queueLength }: {
  building: BuildingInfo; resources: any; onBuild: (key: string) => void
  disabled: boolean; queueLength: number
}) {
  const [expanded, setExpanded] = useState(false)
  const catColors: Record<string, string> = { production: '#94a3b8', energy: '#fbbf24', military: '#2d7dd2', research: '#7c3aed' }
  const color = catColors[building.category] ?? '#6b7280'
  const cost = building.cost_next
  const canAfford = Math.floor(resources.metal) >= cost.metal
    && Math.floor(resources.crystal) >= cost.crystal
    && Math.floor(resources.deuterium) >= cost.deuterium
  // FIX : hasSlot et canBuild manquaient dans ce scope
  const hasSlot = queueLength < 5
  const canBuild = canAfford && hasSlot && !building.in_queue

  return (
    <div className="rounded-xl border overflow-hidden transition-all duration-200"
      style={{ background: `rgba(13,18,30,0.9)`, borderColor: `rgba(${hexToRgb(color)},0.2)` }}>
      <div className="p-4">
        <div className="flex items-center gap-3 mb-3">
          <div className="h-10 w-10 rounded-xl flex items-center justify-center text-xl shrink-0"
            style={{ background: `rgba(${hexToRgb(color)},0.1)`, border: `1px solid rgba(${hexToRgb(color)},0.25)` }}>
            {building.icon}
          </div>
          <div className="flex-1">
            <div className="flex items-center justify-between">
              <p className="font-semibold text-sm text-white">{building.label}</p>
              {building.in_queue && <span className="text-[10px] font-display" style={{ color }}>EN COURS</span>}
            </div>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-[10px] font-display" style={{ color }}>NIV.{building.level}</span>
              <div className="flex-1 h-0.5 bg-gray-800 rounded-full overflow-hidden">
                <div className="h-full rounded-full" style={{ width: `${(building.level/20)*100}%`, background: `linear-gradient(90deg, rgba(${hexToRgb(color)},0.5), ${color})` }} />
              </div>
            </div>
          </div>
        </div>

        {building.per_level && (
          <ProductionDelta perLevel={building.per_level} currentLevel={building.level} icon={building.icon} />
        )}

        {building.next_unlock && !building.in_queue && (
          <div className="mb-3 px-2.5 py-1.5 rounded-lg text-xs flex items-center gap-2"
            style={{ background: `rgba(${hexToRgb(color)},0.06)`, border: `1px solid rgba(${hexToRgb(color)},0.15)` }}>
            <span>🔓</span><span style={{ color }}>Niv.{building.level+1} : {building.next_unlock}</span>
          </div>
        )}

        {!building.in_queue && (
          <>
            <div className="flex flex-wrap gap-2 mb-2 text-xs">
              {cost.metal > 0 && <span className={canAfford ? 'text-gray-400' : 'text-red-400'}>⛏️ {fmt(cost.metal)}</span>}
              {cost.crystal > 0 && <span className={canAfford ? 'text-gray-400' : 'text-red-400'}>💎 {fmt(cost.crystal)}</span>}
              {cost.deuterium > 0 && <span className={canAfford ? 'text-gray-400' : 'text-red-400'}>⚗️ {fmt(cost.deuterium)}</span>}
              <span className="text-gray-600">⏱ {fmtCountdown(cost.seconds)}</span>
            </div>
            <button onClick={() => onBuild(building.key)} disabled={disabled || !canBuild}
              className="w-full py-1.5 rounded-lg text-xs font-display tracking-wider transition-all"
              style={canBuild ? { background: `rgba(${hexToRgb(color)},0.12)`, border: `1px solid rgba(${hexToRgb(color)},0.3)`, color }
                              : { background: 'rgba(30,40,55,0.4)', border: '1px solid rgba(45,58,80,0.4)', color: '#374151' }}>
              {canBuild ? `AMÉLIORER → Niv.${building.level+1}` : '🔒 IMPOSSIBLE'}
            </button>

            {!canBuild && (
              <BuildingBlockedReason
                building={building}
                planetResources={resources}
                energyFactor={1}
                hasQueueSlot={hasSlot}
              />
            )}
          </>
        )}

        <button onClick={() => setExpanded(v => !v)}
          className="w-full mt-2 text-[10px] text-gray-700 hover:text-gray-500 font-display tracking-wider transition-colors">
          {expanded ? '▲ MASQUER' : '▼ DÉTAILS'}
        </button>
      </div>

      {expanded && (
        <div className="border-t px-4 py-3 space-y-3" style={{ borderColor: `rgba(${hexToRgb(color)},0.1)`, background: 'rgba(5,8,16,0.4)' }}>
          <p className="text-xs text-gray-400 leading-relaxed">{building.description}</p>
          {building.synergies.length > 0 && (
            <div>
              <p className="text-[10px] font-display text-gray-600 mb-1.5">SYNERGIES</p>
              {building.synergies.map((s, i) => (
                <p key={i} className="text-xs text-gray-500 flex gap-2"><span className="text-cyan-600 shrink-0">◆</span>{s}</p>
              ))}
            </div>
          )}
          {building.unlocks.length > 0 && (
            <div>
              <p className="text-[10px] font-display text-gray-600 mb-1.5">DÉVERROUILLAGES</p>
              {building.unlocks.map(u => (
                <div key={u.level} className="flex gap-2 text-xs mb-1">
                  <span className={`font-mono font-bold shrink-0 ${building.level >= u.level ? 'text-green-400' : 'text-gray-600'}`}>Niv.{u.level}</span>
                  <span className={building.level >= u.level ? 'text-gray-500 line-through opacity-50' : 'text-gray-400'}>{u.unlock}</span>
                  {building.level >= u.level && <span className="text-green-400">✓</span>}
                </div>
              ))}
            </div>
          )}
          {building.tip && (
            <div className="p-2 rounded-lg text-xs flex gap-2"
              style={{ background: `rgba(${hexToRgb(color)},0.05)`, border: `1px solid rgba(${hexToRgb(color)},0.12)` }}>
              <span>💡</span><span className="italic" style={{ color }}>{building.tip}</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Page principale ──────────────────────────────────────────────────────────
export function BuildingsPage() {
  const qc = useQueryClient()
  const [selectedPlanetId, setSelectedPlanetId] = useState('')

  const { data: planets } = useQuery({ queryKey: ['planets'], queryFn: planetsApi.list })
  useEffect(() => { if (planets?.length && !selectedPlanetId) setSelectedPlanetId(planets[0].id) }, [planets, selectedPlanetId])

  const { data: planet, isLoading } = useQuery({
    queryKey: ['planet', selectedPlanetId],
    queryFn: () => api.get<PlanetDetail>(`/planets/${selectedPlanetId}`),
    enabled: !!selectedPlanetId, refetchInterval: 15_000,
  })

  const { mutate: build, isPending } = useMutation({
    mutationFn: (building: string) => api.post<any>(`/planets/${selectedPlanetId}/build`, { building }),
    onSuccess: (res) => {
      const msg = res.next_unlock ? `🔓 ${res.label} → Niv.${res.target_level} — ${res.next_unlock}` : `✅ ${res.label} → Niv.${res.target_level}`
      toast.success(msg, { duration: 5000 })
      qc.invalidateQueries({ queryKey: ['planet', selectedPlanetId] })
    },
    onError: (err) => toast.error(err instanceof ApiError ? err.detail : 'Erreur'),
  })

  const resources = { metal: planet?.metal ?? 0, crystal: planet?.crystal ?? 0, deuterium: planet?.deuterium ?? 0 }

  const shipyard = planet?.buildings.find(b => b.key === 'shipyard')
  const productionBuildings = planet?.buildings.filter(b => ['metal_mine','crystal_mine','deuterium_synthesizer'].includes(b.key)) ?? []
  const solarPlant = planet?.buildings.find(b => b.key === 'solar_plant')
  const researchLab = planet?.buildings.find(b => b.key === 'research_lab')

  const onDone = useCallback(() => qc.invalidateQueries({ queryKey: ['planet', selectedPlanetId] }), [qc, selectedPlanetId])

  return (
    <div className="space-y-6 animate-fade-in pb-20 lg:pb-0">
      <div>
        <p className="section-title mb-1">Infrastructure Planétaire</p>
        <h1 className="text-2xl font-bold text-white">Bâtiments</h1>
      </div>

      {/* Sélecteur planète */}
      <div className="flex flex-wrap items-center gap-2">
        <p className="text-xs text-gray-600 font-display">PLANÈTE :</p>
        {(planets ?? []).map(p => (
          <button key={p.id} onClick={() => setSelectedPlanetId(p.id)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-all"
            style={selectedPlanetId === p.id
              ? { background: 'rgba(45,125,210,0.15)', border: '1px solid rgba(45,125,210,0.4)', color: '#60a5fa' }
              : { background: 'rgba(20,28,42,0.6)', border: '1px solid rgba(35,50,70,0.6)', color: '#6b7280' }}>
            {p.is_homeworld ? '🏠' : '🪐'} {p.name}
          </button>
        ))}
      </div>

      {isLoading ? <div className="flex justify-center py-16"><LoadingSpinner size="lg" /></div> : planet ? (
        <>
          {/* File de construction */}
          {planet.build_queue.length > 0 && (
            <div>
              <p className="section-title mb-3">EN CONSTRUCTION</p>
              <div className="space-y-2">
                {planet.build_queue.map(item => (
                  <div key={item.id} className="panel flex items-center justify-between">
                    <div className="flex items-center gap-2.5">
                      <span className="text-xl">{planet.buildings.find(b=>b.key===item.item_name)?.icon ?? '🏗️'}</span>
                      <div>
                        <p className="text-sm font-semibold text-white">{item.label}</p>
                        <p className="text-xs text-gray-500">→ Niveau {item.target_level}</p>
                      </div>
                    </div>
                    <Countdown secs={item.seconds_remaining} onDone={onDone} />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ZONE ÉNERGIE */}
          <div>
            <p className="section-title mb-3">⚡ ÉNERGIE</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <EnergyGauge buildings={planet.buildings} rates={planet.production_rates} />
              {solarPlant && (
                <BuildingCard
                  building={solarPlant}
                  resources={resources}
                  onBuild={build}
                  disabled={isPending}
                  queueLength={planet.build_queue.length}
                />
              )}
            </div>
          </div>

          {/* ZONE PRODUCTION */}
          <div>
            <p className="section-title mb-3">⛏️ PRODUCTION</p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {productionBuildings.map(b => (
                <BuildingCard
                  key={b.key}
                  building={b}
                  resources={resources}
                  onBuild={build}
                  disabled={isPending}
                  queueLength={planet.build_queue.length}
                />
              ))}
            </div>
          </div>

          {/* ZONE CHANTIER NAVAL */}
          <div>
            <p className="section-title mb-3">🏭 CHANTIER NAVAL</p>
            {shipyard && (
              <ShipyardZone
                building={shipyard}
                resources={resources}
                onBuild={build}
                disabled={isPending}
                queueLength={planet.build_queue.length}
              />
            )}
          </div>

          {/* ZONE RECHERCHE */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <p className="section-title">🔬 RECHERCHE</p>
              <Link to="/tech" className="text-[10px] text-accent-blue font-display">ARBRE TECH →</Link>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {researchLab && (
                <BuildingCard
                  building={researchLab}
                  resources={resources}
                  onBuild={build}
                  disabled={isPending}
                  queueLength={planet.build_queue.length}
                />
              )}
              {/* Teaser Académie des modules */}
              <Link to="/tech" className="panel hover:bg-surface-elevated transition-all group"
                style={{ borderColor: 'rgba(124,58,237,0.2)' }}>
                <div className="h-px mb-4" style={{ background: 'linear-gradient(90deg, transparent, rgba(124,58,237,0.5), transparent)' }} />
                <div className="flex items-center gap-3 mb-3">
                  <span className="text-2xl">🔭</span>
                  <div>
                    <p className="font-semibold text-white">Arbre Technologique</p>
                    <p className="text-[10px] text-purple-400 font-display">BONUS PERMANENTS PAR CLASSE</p>
                  </div>
                </div>
                <p className="text-xs text-gray-500">Recherchez des améliorations permanentes pour chaque classe de vaisseau. DPS, boucliers, vitesse, furtivité...</p>
                <p className="text-[10px] text-purple-400 font-display mt-3 group-hover:text-purple-300">ACCÉDER →</p>
              </Link>
            </div>
          </div>

          {/* ZONE EXPÉDITION */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <p className="section-title">🌌 EXPÉDITIONS</p>
              <Link to="/expeditions" className="text-[10px] text-accent-blue font-display">GÉRER →</Link>
            </div>
            <Link to="/expeditions" className="panel hover:bg-surface-elevated transition-all group block"
              style={{ borderColor: 'rgba(124,58,237,0.2)', background: 'linear-gradient(135deg, rgba(124,58,237,0.05), rgba(13,18,30,0.9))' }}>
              <div className="h-px mb-4" style={{ background: 'linear-gradient(90deg, transparent, rgba(124,58,237,0.5), transparent)' }} />
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">🚀</span>
                  <div>
                    <p className="font-semibold text-white">Centre d'Expédition</p>
                    <p className="text-[10px] text-purple-400 font-display">AVENTURES AUTONOMES · XP · MODULES · CICATRICES</p>
                  </div>
                </div>
                <span className="text-purple-400 font-display text-xs group-hover:text-purple-300">EXPLORER →</span>
              </div>
              <p className="text-xs text-gray-500 mt-3">Envoyez vos vaisseaux en expédition — 12 événements narratifs, ressources, modules rares et cicatrices légendaires.</p>
            </Link>
          </div>
        </>
      ) : null}
    </div>
  )
}