import React, { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { shipsApi } from '@/api/ships'
import { planetsApi } from '@/api'
import { ShipCard, ShipCardSkeleton } from '@/components/ships/ShipCard'
import { EmptyState } from '@/components/ui'
import { ApiError } from '@/lib/api'
import { fmt } from '@/lib/utils'
import type { Rarity, ShipType } from '@/types'
import { SHIP_TYPE_CONFIG, RARITY_CONFIG } from '@/types'

// Coûts de construction (sync avec backend)
const BUILD_COSTS: Record<ShipType, { metal: number; crystal: number; deuterium: number; time: string }> = {
  frigate_attack:      { metal: 3_000,  crystal: 1_000,  deuterium: 0,     time: '~2 min' },
  frigate_defense:     { metal: 6_000,  crystal: 2_000,  deuterium: 0,     time: '~4 min' },
  frigate_support:     { metal: 2_000,  crystal: 2_000,  deuterium: 500,   time: '~3 min' },
  frigate_exploration: { metal: 2_000,  crystal: 1_000,  deuterium: 1_000, time: '~3 min' },
  cruiser_attack:      { metal: 20_000, crystal: 7_000,  deuterium: 2_000, time: '~15 min' },
  cruiser_defense:     { metal: 30_000, crystal: 10_000, deuterium: 2_000, time: '~20 min' },
}

const CLASS_INFO = {
  ATTACK:      { desc: 'DPS élevé, vitesse moyenne',          color: '#ef4444' },
  DEFENSE:     { desc: 'Coque massive, boucliers renforcés',  color: '#3b82f6' },
  SUPPORT:     { desc: 'Aura alliée, boost de flotte',        color: '#22c55e' },
  EXPLORATION: { desc: 'Furtivité, cargo élevé, vitesse max', color: '#a855f7' },
}

export function HangarPage() {
  const navigate  = useNavigate()
  const qc        = useQueryClient()
  const [statusFilter, setStatusFilter] = useState('all')
  const [rarityFilter, setRarityFilter] = useState<Rarity | 'all'>('all')
  const [showBuild, setShowBuild] = useState(false)

  const { data: ships, isLoading } = useQuery({ queryKey: ['ships'], queryFn: shipsApi.list })
  const { data: planets } = useQuery({ queryKey: ['planets'], queryFn: planetsApi.list })

  const filtered = useMemo(() => {
    if (!ships) return []
    return ships
      .filter(s => statusFilter === 'all' || s.status === statusFilter)
      .filter(s => rarityFilter === 'all' || s.rarity === rarityFilter)
  }, [ships, statusFilter, rarityFilter])

  const STATUSES = [
    { id: 'all',      label: 'TOUS',       count: ships?.length ?? 0 },
    { id: 'DOCKED',   label: 'AMARRÉS',    count: ships?.filter(s => s.status === 'DOCKED').length ?? 0 },
    { id: 'IN_FLEET', label: 'EN ROUTE',   count: ships?.filter(s => s.status === 'IN_FLEET').length ?? 0 },
    { id: 'IN_FORGE', label: 'EN FORGE',   count: ships?.filter(s => s.status === 'IN_FORGE').length ?? 0 },
  ]

  return (
    <div className="space-y-5 animate-fade-in">

      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <p className="section-title mb-1">Flotte spatiale</p>
          <h1 className="text-2xl font-bold text-white">Hangar</h1>
        </div>
        <button onClick={() => setShowBuild(true)} className="btn-primary">
          + Construire
        </button>
      </div>

      {/* ── Filtres statut ─────────────────────────────────────────────────── */}
      <div className="flex gap-2 flex-wrap">
        {STATUSES.map(s => (
          <button key={s.id} onClick={() => setStatusFilter(s.id)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-display tracking-wider transition-all duration-200"
            style={statusFilter === s.id ? {
              background: 'rgba(45,125,210,0.15)', border: '1px solid rgba(45,125,210,0.35)', color: '#60a5fa',
            } : { background: 'rgba(20,28,42,0.6)', border: '1px solid rgba(35,50,70,0.6)', color: '#6b7280' }}>
            <span>{s.label}</span>
            <span className="px-1.5 py-0.5 rounded-full text-[10px]"
              style={{ background: statusFilter === s.id ? 'rgba(45,125,210,0.3)' : 'rgba(35,50,70,0.6)' }}>
              {s.count}
            </span>
          </button>
        ))}
      </div>

      {/* ── Filtres rareté ─────────────────────────────────────────────────── */}
      <div className="flex gap-2 flex-wrap">
        <button onClick={() => setRarityFilter('all')}
          className="px-3 py-1 rounded-full text-[10px] font-display tracking-wider transition-all"
          style={rarityFilter === 'all'
            ? { background: 'rgba(107,114,128,0.2)', border: '1px solid rgba(107,114,128,0.4)', color: '#d1d5db' }
            : { background: 'transparent', border: '1px solid rgba(55,65,81,0.5)', color: '#6b7280' }}>
          TOUTES
        </button>
        {(Object.keys(RARITY_CONFIG) as Rarity[]).map(r => (
          <button key={r} onClick={() => setRarityFilter(r === rarityFilter ? 'all' : r)}
            className="px-3 py-1 rounded-full text-[10px] font-display tracking-wider transition-all"
            style={{
              background: rarityFilter === r ? `${RARITY_CONFIG[r].color}20` : 'transparent',
              border: `1px solid ${rarityFilter === r ? RARITY_CONFIG[r].color + '60' : 'rgba(55,65,81,0.5)'}`,
              color: rarityFilter === r ? RARITY_CONFIG[r].color : '#6b7280',
            }}>
            {RARITY_CONFIG[r].label.toUpperCase()}
          </button>
        ))}
      </div>

      {/* ── Grille vaisseaux ───────────────────────────────────────────────── */}
      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => <ShipCardSkeleton key={i} />)}
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState icon="🚀" title="Aucun vaisseau"
          message="Construisez votre premier vaisseau pour commencer la conquête"
          action={<button onClick={() => setShowBuild(true)} className="btn-primary mt-3">+ Construire</button>} />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map(ship => (
            <ShipCard key={ship.id} ship={ship} onClick={() => navigate(`/hangar/${ship.id}`)} />
          ))}
        </div>
      )}

      {/* ── Modal construction ─────────────────────────────────────────────── */}
      {showBuild && (
        <BuildModal
          planets={planets ?? []}
          onClose={() => setShowBuild(false)}
          onBuilt={() => { qc.invalidateQueries({ queryKey: ['ships'] }); setShowBuild(false) }}
        />
      )}
    </div>
  )
}

// ─── Modal construction premium ──────────────────────────────────────────────
function BuildModal({ planets, onClose, onBuilt }: {
  planets: { id: string; name: string; metal: number; crystal: number; deuterium: number }[]
  onClose: () => void
  onBuilt: () => void
}) {
  const [shipType, setShipType] = useState<ShipType>('frigate_attack')
  const [planetId, setPlanetId] = useState(planets[0]?.id ?? '')

  const selectedPlanet = planets.find(p => p.id === planetId)
  const cost = BUILD_COSTS[shipType]
  const typeCfg = SHIP_TYPE_CONFIG[shipType]
  const canAfford = selectedPlanet
    ? selectedPlanet.metal >= cost.metal && selectedPlanet.crystal >= cost.crystal && selectedPlanet.deuterium >= cost.deuterium
    : false

  const { mutate: build, isPending } = useMutation({
    mutationFn: () => shipsApi.build({ ship_type: shipType, planet_id: planetId }),
    onSuccess: (res) => {
      const rarity = res.rarity as Rarity
      const cfg = RARITY_CONFIG[rarity]
      toast.success(`🎲 ${cfg.label} obtenu !`, {
        duration: 6000,
        style: { background: '#0d1220', border: `1px solid ${cfg.color}50`, color: cfg.color },
      })
      onBuilt()
    },
    onError: (err) => toast.error(err instanceof ApiError ? err.detail : 'Erreur'),
  })

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4" onClick={onClose}>
      <div className="absolute inset-0 bg-black/70" style={{ backdropFilter: 'blur(8px)' }} />
      <div className="relative w-full max-w-2xl animate-slide-up rounded-2xl overflow-hidden"
        style={{ background: 'rgba(8,12,24,0.98)', border: '1px solid rgba(45,125,210,0.2)' }}
        onClick={e => e.stopPropagation()}>

        {/* Ligne lumineuse */}
        <div className="h-px" style={{ background: 'linear-gradient(90deg, transparent, rgba(45,125,210,0.8), transparent)' }} />

        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <p className="section-title mb-1">Chantier naval</p>
              <h2 className="text-xl font-bold text-white">Construire un vaisseau</h2>
            </div>
            <button onClick={onClose} className="btn-ghost text-xl">×</button>
          </div>

          {/* Sélection type */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 mb-5">
            {(Object.entries(SHIP_TYPE_CONFIG) as [ShipType, typeof SHIP_TYPE_CONFIG[ShipType]][]).map(([type, cfg]) => {
              const classInfo = CLASS_INFO[cfg.class]
              const selected  = shipType === type
              return (
                <button key={type} onClick={() => setShipType(type)}
                  className="p-3 rounded-xl text-left transition-all duration-200 relative overflow-hidden"
                  style={{
                    background: selected ? `${classInfo.color}12` : 'rgba(20,28,42,0.6)',
                    border: `1px solid ${selected ? classInfo.color + '50' : 'rgba(35,50,70,0.6)'}`,
                    boxShadow: selected ? `0 0 15px ${classInfo.color}20` : 'none',
                  }}>
                  {selected && <div className="absolute top-0 left-0 right-0 h-px"
                    style={{ background: `linear-gradient(90deg, transparent, ${classInfo.color}80, transparent)` }} />}
                  <p className="text-lg mb-1">{cfg.icon}</p>
                  <p className="text-xs font-semibold text-white">{cfg.label}</p>
                  <p className="text-[10px] mt-0.5" style={{ color: classInfo.color }}>{cfg.class}</p>
                </button>
              )
            })}
          </div>

          {/* Info classe sélectionnée */}
          <div className="panel mb-5" style={{ background: 'rgba(20,28,42,0.4)' }}>
            <div className="flex items-start gap-3">
              <span className="text-2xl">{typeCfg.icon}</span>
              <div>
                <p className="font-semibold text-white">{typeCfg.label}</p>
                <p className="text-xs text-gray-400 mt-0.5">{CLASS_INFO[typeCfg.class].desc}</p>
                <div className="flex gap-3 mt-2 text-xs">
                  {cost.metal > 0 && <span className={selectedPlanet && selectedPlanet.metal >= cost.metal ? 'text-gray-300' : 'text-red-400'}>⛏️ {fmt(cost.metal)}</span>}
                  {cost.crystal > 0 && <span className={selectedPlanet && selectedPlanet.crystal >= cost.crystal ? 'text-gray-300' : 'text-red-400'}>💎 {fmt(cost.crystal)}</span>}
                  {cost.deuterium > 0 && <span className={selectedPlanet && selectedPlanet.deuterium >= cost.deuterium ? 'text-gray-300' : 'text-red-400'}>⚗️ {fmt(cost.deuterium)}</span>}
                  <span className="text-gray-600">⏱ {cost.time}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Planète */}
          <div className="mb-5">
            <label className="section-title block mb-2">Planète chantier</label>
            <div className="flex gap-2 flex-wrap">
              {planets.map(p => (
                <button key={p.id} onClick={() => setPlanetId(p.id)}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-all"
                  style={planetId === p.id ? {
                    background: 'rgba(45,125,210,0.15)', border: '1px solid rgba(45,125,210,0.4)', color: '#60a5fa',
                  } : { background: 'rgba(20,28,42,0.6)', border: '1px solid rgba(35,50,70,0.6)', color: '#6b7280' }}>
                  🌍 {p.name}
                </button>
              ))}
            </div>
          </div>

          {/* Note RNG */}
          <div className="panel mb-5" style={{ background: 'rgba(124,58,237,0.06)', borderColor: 'rgba(124,58,237,0.2)' }}>
            <p className="text-xs text-purple-400">
              🎲 La rareté est tirée aléatoirement — 55% Commun · 27% Peu commun · 12% Rare · 5% Épique · 1% Légendaire
            </p>
          </div>

          {/* Bouton */}
          <button className="btn-primary w-full py-3 text-base" disabled={!canAfford || isPending || !planetId} onClick={() => build()}>
            {isPending ? '⏳ Construction en cours…' : canAfford ? '🚀 Lancer la construction' : '❌ Ressources insuffisantes'}
          </button>
        </div>
      </div>
    </div>
  )
}
