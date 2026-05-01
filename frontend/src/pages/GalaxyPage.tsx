/**
 * GalaxyPage.tsx
 * Agent 6 — Frontend
 *
 * Carte galactique fonctionnelle :
 * - Grille système (9 galaxies × 499 systèmes × 15 positions)
 * - Sélecteur galaxie/système
 * - Affichage des planètes dans le système sélectionné
 * - Envoi de flotte vers une planète cible
 * - Liste des flottes en transit avec countdown
 */
import React, { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { api } from '@/lib/api'
import { ApiError } from '@/lib/api'
import { LoadingSpinner, Modal } from '@/components/ui'
import { fmt, fmtCountdown } from '@/lib/utils'
import type { ShipSummary, FleetResponse } from '@/types'
import { shipsApi } from '@/api/ships'
import { GalaxyMap } from '@/components/galaxy/GalaxyMap'

// ─── Types ────────────────────────────────────────────────────────────────────

interface GalaxySlot {
  position: number
  planet_id: string | null
  planet_name: string | null
  owner_id: string | null
  owner_username: string | null
  is_mine: boolean
}

// ─── Hook flotte countdown ────────────────────────────────────────────────────

function FleetCountdown({ arrivesAt }: { arrivesAt: string }) {
  const [secs, setSecs] = useState(0)

  useEffect(() => {
    const update = () => {
      const diff = Math.max(0, Math.round((new Date(arrivesAt).getTime() - Date.now()) / 1000))
      setSecs(diff)
    }
    update()
    const id = setInterval(update, 1000)
    return () => clearInterval(id)
  }, [arrivesAt])

  if (secs <= 0) return <span className="text-green-400 text-xs">Arrivée !</span>
  return <span className="text-blue-400 font-mono text-xs">{fmtCountdown(secs)}</span>
}

// ─── Modal envoi de flotte ────────────────────────────────────────────────────

function SendFleetModal({
  open, onClose,
  targetGalaxy, targetSystem, targetPosition, targetPlanetId,
  myPlanets,
}: {
  open: boolean
  onClose: () => void
  targetGalaxy: number
  targetSystem: number
  targetPosition: number
  targetPlanetId: string | null
  myPlanets: { id: string; name: string }[]
}) {
  const qc = useQueryClient()
  const [originPlanetId, setOriginPlanetId] = useState('')
  const [mission, setMission]               = useState<'ATTACK' | 'TRANSPORT' | 'ESPIONAGE'>('ATTACK')
  const [selectedShips, setSelectedShips]   = useState<string[]>([])
  const [cargoMetal, setCargoMetal]         = useState(0)
  const [cargoCrystal, setCargoCrystal]     = useState(0)

  const { data: ships } = useQuery({
    queryKey: ['ships'],
    queryFn: shipsApi.list,
    enabled: open,
  })

  // Vaisseaux DOCKED sur la planète d'origine sélectionnée
  const availableShips = ships?.filter(
    s => s.status === 'DOCKED' && s.planet_id === originPlanetId
  ) ?? []

  const { mutate: sendFleet, isPending } = useMutation({
    mutationFn: () => api.post('/fleets', {
      ship_ids: selectedShips,
      origin_planet_id: originPlanetId,
      mission,
      target_galaxy: targetGalaxy,
      target_system: targetSystem,
      target_position: targetPosition,
      cargo_metal: mission === 'TRANSPORT' ? cargoMetal : 0,
      cargo_crystal: mission === 'TRANSPORT' ? cargoCrystal : 0,
      cargo_deuterium: 0,
    }),
    onSuccess: () => {
      toast.success('Flotte envoyée !', { icon: '🚀' })
      qc.invalidateQueries({ queryKey: ['fleets'] })
      qc.invalidateQueries({ queryKey: ['ships'] })
      onClose()
    },
    onError: (err) => toast.error(err instanceof ApiError ? err.detail : 'Erreur'),
  })

  function toggleShip(id: string) {
    setSelectedShips(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    )
  }

  const MISSION_ICONS: Record<string, string> = {
    ATTACK:    '⚔️',
    TRANSPORT: '📦',
    ESPIONAGE: '🔍',
  }

  return (
    <Modal open={open} onClose={onClose} title="🚀 Envoyer une flotte" size="lg">
      <div className="space-y-4">
        {/* Cible */}
        <div className="panel bg-surface-tertiary text-sm">
          <p className="text-gray-400">Cible : <span className="text-white">
            Galaxie {targetGalaxy} · Système {targetSystem} · Position {targetPosition}
          </span></p>
          {targetPlanetId && <p className="text-xs text-gray-500 mt-1">Planète présente sur cette case</p>}
        </div>

        {/* Planète d'origine */}
        <div>
          <label className="block text-sm text-gray-400 mb-1">Planète d'origine</label>
          <select
            className="input-field"
            value={originPlanetId}
            onChange={e => { setOriginPlanetId(e.target.value); setSelectedShips([]) }}
          >
            <option value="">Choisir une planète…</option>
            {myPlanets.map(p => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>

        {/* Mission */}
        <div>
          <label className="block text-sm text-gray-400 mb-2">Mission</label>
          <div className="grid grid-cols-3 gap-2">
            {(['ATTACK', 'TRANSPORT', 'ESPIONAGE'] as const).map(m => (
              <button
                key={m}
                onClick={() => setMission(m)}
                className={`p-2 rounded-lg border text-sm font-medium transition-all ${
                  mission === m
                    ? 'border-accent-blue bg-accent-blue/10 text-accent-blue'
                    : 'border-surface-border text-gray-400 hover:text-white'
                }`}
              >
                {MISSION_ICONS[m]} {m}
              </button>
            ))}
          </div>
        </div>

        {/* Sélection vaisseaux */}
        {originPlanetId && (
          <div>
            <label className="block text-sm text-gray-400 mb-2">
              Vaisseaux ({selectedShips.length} sélectionné{selectedShips.length > 1 ? 's' : ''})
            </label>
            {availableShips.length === 0 ? (
              <p className="text-xs text-gray-500 italic">Aucun vaisseau amarré sur cette planète</p>
            ) : (
              <div className="grid grid-cols-2 gap-2 max-h-40 overflow-y-auto">
                {availableShips.map(ship => {
                  const sel = selectedShips.includes(ship.id)
                  return (
                    <button
                      key={ship.id}
                      onClick={() => toggleShip(ship.id)}
                      className={`p-2 rounded-lg border text-left text-xs transition-all ${
                        sel
                          ? 'border-accent-blue bg-accent-blue/10'
                          : 'border-surface-border hover:border-gray-500'
                      }`}
                    >
                      <p className="font-medium text-white">{ship.ship_type.replace('_', ' ')}</p>
                      <p className="text-gray-500">{ship.rarity} · G{ship.grade}</p>
                    </button>
                  )
                })}
              </div>
            )}
          </div>
        )}

        {/* Cargo si TRANSPORT */}
        {mission === 'TRANSPORT' && (
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-400 mb-1">Métal à transporter</label>
              <input type="number" min={0} className="input-field text-sm"
                value={cargoMetal} onChange={e => setCargoMetal(Number(e.target.value))} />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Cristal à transporter</label>
              <input type="number" min={0} className="input-field text-sm"
                value={cargoCrystal} onChange={e => setCargoCrystal(Number(e.target.value))} />
            </div>
          </div>
        )}

        <button
          className="btn-primary w-full"
          disabled={isPending || selectedShips.length === 0 || !originPlanetId}
          onClick={() => sendFleet()}
        >
          {isPending ? '⏳ Envoi…' : `🚀 Envoyer ${selectedShips.length} vaisseau${selectedShips.length > 1 ? 'x' : ''}`}
        </button>
      </div>
    </Modal>
  )
}

// ─── Page principale ──────────────────────────────────────────────────────────

export function GalaxyPage() {
  const qc = useQueryClient()
  const [galaxy, setGalaxy] = useState(1)
  const [system, setSystem] = useState(1)
  const [fleetTarget, setFleetTarget] = useState<{ g: number; s: number; p: number; planetId: string | null } | null>(null)

  // Charger les planètes de ce système depuis l'API
  const { data: systemSlots, isLoading } = useQuery({
    queryKey: ['galaxy', galaxy, system],
    queryFn: () => api.get<GalaxySlot[]>(`/galaxy?galaxy=${galaxy}&system=${system}`),
    // Fallback si l'endpoint n'existe pas encore — données simulées
    placeholderData: Array.from({ length: 15 }, (_, i) => ({
      position: i + 1,
      planet_id: null,
      planet_name: null,
      owner_id: null,
      owner_username: null,
      is_mine: false,
    })) as GalaxySlot[],
  })

  // Planètes du joueur pour le modal flotte
  const { data: myPlanets } = useQuery({
    queryKey: ['planets'],
    queryFn: () => api.get<{ id: string; name: string }[]>('/planets'),
  })

  // Flottes actives
  const { data: fleets } = useQuery({
    queryKey: ['fleets'],
    queryFn: () => api.get<FleetResponse[]>('/fleets'),
    refetchInterval: 10_000,
  })

  const slots = systemSlots ?? []

  return (
    <div className="space-y-5 pb-20 lg:pb-0">
      <div>
        <h1 className="text-2xl font-bold text-white">🌌 Galaxie</h1>
        <p className="text-sm text-gray-400 mt-0.5">Explorez les systèmes et envoyez vos flottes</p>
      </div>

      {/* Sélecteur galaxie/système */}
      <div className="panel flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-400">Galaxie</label>
          <div className="flex gap-1">
            <button onClick={() => setGalaxy(g => Math.max(1, g - 1))} className="btn-secondary px-2 py-1 text-sm">‹</button>
            <span className="px-3 py-1 bg-surface-tertiary rounded-lg text-white font-mono text-sm w-8 text-center">{galaxy}</span>
            <button onClick={() => setGalaxy(g => Math.min(9, g + 1))} className="btn-secondary px-2 py-1 text-sm">›</button>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-400">Système</label>
          <div className="flex gap-1">
            <button onClick={() => setSystem(s => Math.max(1, s - 1))} className="btn-secondary px-2 py-1 text-sm">‹</button>
            <input
              type="number" min={1} max={499}
              value={system}
              onChange={e => setSystem(Math.max(1, Math.min(499, Number(e.target.value))))}
              className="input-field w-16 text-center text-sm py-1"
            />
            <button onClick={() => setSystem(s => Math.min(499, s + 1))} className="btn-secondary px-2 py-1 text-sm">›</button>
          </div>
        </div>
        <p className="text-xs text-gray-500">G{galaxy}:S{system}</p>
      </div>

      {/* Carte galactique SVG interactive */}
      <GalaxyMap
        planets={slots.map(s => ({
          position: s.position,
          planet_id: s.planet_id,
          name: s.planet_name,
          owner_id: s.owner_id,
          owner_username: s.owner_username,
          is_own: s.is_mine,
        }))}
        currentPlayerId=""
        onSelectPlanet={(p) => {
          if (p.planet_id) {
            setFleetTarget({ g: galaxy, s: system, p: p.position, planetId: p.planet_id })
          }
        }}
        selectedPlanetId={fleetTarget?.planetId ?? null}
      />

      {/* Flottes en transit */}
      {fleets && fleets.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">
            🚀 Flottes en transit ({fleets.length})
          </h2>
          <div className="space-y-2">
            {fleets.map(fleet => (
              <div key={fleet.fleet_id} className="panel flex items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <span className="text-xl">
                    {fleet.mission === 'ATTACK' ? '⚔️' : fleet.mission === 'TRANSPORT' ? '📦' : '🔍'}
                  </span>
                  <div>
                    <p className="text-sm font-medium">{fleet.mission}</p>
                    <p className="text-xs text-gray-500">
                      → G{fleet.target_galaxy}:S{fleet.target_system}:P{fleet.target_position}
                      · {fleet.ship_count} vaisseau{fleet.ship_count > 1 ? 'x' : ''}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <FleetCountdown arrivesAt={fleet.arrives_at} />
                  <button
                    onClick={async () => {
                      try {
                        await api.delete(`/fleets/${fleet.fleet_id}`)
                        toast.success('Flotte rappelée')
                        qc.invalidateQueries({ queryKey: ['fleets'] })
                        qc.invalidateQueries({ queryKey: ['ships'] })
                      } catch (e) {
                        toast.error(e instanceof ApiError ? e.detail : 'Erreur')
                      }
                    }}
                    className="text-xs text-red-400 hover:text-red-300 transition-colors"
                  >
                    Rappeler
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Modal envoi flotte */}
      {fleetTarget && (
        <SendFleetModal
          open
          onClose={() => setFleetTarget(null)}
          targetGalaxy={fleetTarget.g}
          targetSystem={fleetTarget.s}
          targetPosition={fleetTarget.p}
          targetPlanetId={fleetTarget.planetId}
          myPlanets={myPlanets ?? []}
        />
      )}
    </div>
  )
}
