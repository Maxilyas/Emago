import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { shipsApi } from '@/api/ships'
import { forgeApi } from '@/api'
import { ShipCard, ShipCardSkeleton } from '@/components/ships/ShipCard'
import { ForgeProgress } from '@/components/forge/ForgeProgress'
import { EmptyState, Tabs } from '@/components/ui'
import { ApiError } from '@/lib/api'
import { RARITY_CONFIG, FORGE_COSTS, type Rarity } from '@/types'
import { fmt, fmtDate } from '@/lib/utils'

export function ForgePage() {
  const qc = useQueryClient()
  const [tab, setTab] = useState('forge')
  const [selected, setSelected] = useState<string[]>([])

  const { data: ships, isLoading: shipsLoading } = useQuery({
    queryKey: ['ships'],
    queryFn: shipsApi.list,
  })

  const { data: forgeHistory, isLoading: historyLoading } = useQuery({
    queryKey: ['forge', 'history'],
    queryFn: forgeApi.history,
    enabled: tab === 'history',
  })

  // Charger les statuts des forges actives
  const activeForges = (forgeHistory ?? []).filter((f) => !f.is_completed)
  const { data: activeStatuses } = useQuery({
    queryKey: ['forge', 'active', activeForges.map((f) => f.forge_id)],
    queryFn: () => Promise.all(activeForges.map((f) => forgeApi.status(f.forge_id))),
    enabled: activeForges.length > 0,
    refetchInterval: 30_000,
  })

  // Vaisseaux eligibles (DOCKED + pas LEGENDARY)
  const eligible = ships?.filter(
    (s) => s.status === 'DOCKED' && s.rarity !== 'LEGENDARY'
  ) ?? []

  const shipA = eligible.find((s) => s.id === selected[0])
  const shipB = eligible.find((s) => s.id === selected[1])

  // Validation compatibilité
  const compatible = shipA && shipB &&
    shipA.ship_type === shipB.ship_type &&
    shipA.rarity === shipB.rarity

  const { mutate: startForge, isPending } = useMutation({
    mutationFn: () => forgeApi.start(selected[0], selected[1]),
    onSuccess: () => {
      toast.success('Forge lancée — résultat dans 8 heures !', { duration: 6000 })
      qc.invalidateQueries({ queryKey: ['ships'] })
      qc.invalidateQueries({ queryKey: ['forge', 'history'] })
      setSelected([])
      setTab('history')
    },
    onError: (err) => toast.error(err instanceof ApiError ? err.detail : 'Erreur de forge'),
  })

  function toggleSelect(id: string) {
    setSelected((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id)
      if (prev.length >= 2) return [prev[1], id]
      return [...prev, id]
    })
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-white">Forge</h1>
        <p className="text-sm text-gray-400 mt-0.5">
          Fusionnez deux vaisseaux identiques pour obtenir une rareté supérieure
        </p>
      </div>

      <Tabs
        tabs={[
          { id: 'forge',   label: 'Nouvelle forge', icon: '🔨' },
          { id: 'history', label: 'Historique',     icon: '📋' },
        ]}
        active={tab}
        onChange={setTab}
      />

      {tab === 'forge' && (
        <div className="space-y-5">
          {/* Sélection + prévisualisation résultat */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {[0, 1].map((idx) => {
              const ship = idx === 0 ? shipA : shipB
              return (
                <div key={idx} className="panel">
                  <p className="text-xs text-gray-500 mb-2 uppercase tracking-wide">
                    Vaisseau {idx + 1}
                  </p>
                  {ship ? (
                    <ShipCard ship={ship} compact onClick={() => toggleSelect(ship.id)} selected />
                  ) : (
                    <div className="border-2 border-dashed border-surface-border rounded-xl p-8 text-center">
                      <p className="text-gray-500 text-sm">Sélectionnez ci-dessous</p>
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          {/* Résultat estimé */}
          {compatible && shipA && (
            <div className="panel border border-dashed"
              style={{ borderColor: RARITY_CONFIG[shipA.rarity as Rarity].color + '80' }}>
              <p className="text-sm text-gray-400 mb-2">Résultat estimé</p>
              <div className="flex items-center gap-3">
                <span className="text-2xl">✨</span>
                <div>
                  <p className="font-semibold" style={{ color: RARITY_CONFIG[shipA.rarity as Rarity].color }}>
                    {RARITY_CONFIG[shipA.rarity as Rarity].label} → {
                      RARITY_CONFIG[{
                        COMMON: 'UNCOMMON', UNCOMMON: 'RARE', RARE: 'EPIC', EPIC: 'LEGENDARY'
                      }[shipA.rarity] as Rarity]?.label ?? '?'
                    }
                  </p>
                  <p className="text-xs text-gray-500">Meilleures stats des deux parents · 30% XP transférée</p>
                </div>
              </div>
              {/* Coût */}
              {FORGE_COSTS[shipA.ship_type] && (
                <div className="mt-3 pt-3 border-t border-surface-border">
                  <p className="text-xs text-gray-500 mb-1">Coût :</p>
                  <div className="flex gap-4 text-sm">
                    {FORGE_COSTS[shipA.ship_type].metal > 0 &&
                      <span className="text-metal">⛏️ {fmt(FORGE_COSTS[shipA.ship_type].metal)}</span>}
                    {FORGE_COSTS[shipA.ship_type].crystal > 0 &&
                      <span className="text-crystal">💎 {fmt(FORGE_COSTS[shipA.ship_type].crystal)}</span>}
                    {FORGE_COSTS[shipA.ship_type].deuterium > 0 &&
                      <span className="text-deuterium">⚗️ {fmt(FORGE_COSTS[shipA.ship_type].deuterium)}</span>}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Bouton lancement */}
          {selected.length === 2 && !compatible && (
            <div className="text-center text-orange-400 text-sm">
              ⚠️ Les deux vaisseaux doivent être du même type ET de la même rareté
            </div>
          )}

          <button
            className="btn-primary w-full"
            disabled={!compatible || isPending}
            onClick={() => startForge()}
          >
            {isPending ? '⏳ Lancement…' : '🔨 Lancer la Forge (8 heures)'}
          </button>

          {/* Grille de sélection */}
          <div>
            <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">
              Vaisseaux disponibles ({eligible.length})
            </h2>
            {shipsLoading ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {[...Array(4)].map((_, i) => <ShipCardSkeleton key={i} />)}
              </div>
            ) : eligible.length === 0 ? (
              <EmptyState icon="🚀" title="Aucun vaisseau disponible" message="Vous avez besoin de vaisseaux DOCKED non-Légendaires" />
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {eligible.map((ship) => (
                  <ShipCard
                    key={ship.id}
                    ship={ship}
                    compact
                    selected={selected.includes(ship.id)}
                    onClick={() => toggleSelect(ship.id)}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {tab === 'history' && (
        <div className="space-y-4">
          {/* Forges actives */}
          {activeStatuses && activeStatuses.length > 0 && (
            <div>
              <h2 className="text-sm font-semibold text-gray-400 uppercase mb-3">En cours</h2>
              {activeStatuses.map((forge) => (
                <ForgeProgress
                  key={forge.forge_id}
                  forge={forge}
                  onComplete={() => qc.invalidateQueries({ queryKey: ['forge', 'history'] })}
                />
              ))}
            </div>
          )}

          {/* Historique complet */}
          <h2 className="text-sm font-semibold text-gray-400 uppercase">Terminées</h2>
          {historyLoading ? (
            <p className="text-gray-500 text-sm">Chargement…</p>
          ) : (
            (forgeHistory ?? [])
              .filter((f) => f.is_completed)
              .map((f) => (
                <div key={f.forge_id} className="panel flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <span className="text-xl">✅</span>
                    <div>
                      <p className="text-sm font-medium">Forge terminée</p>
                      <p className="text-xs text-gray-500">{fmtDate(f.completed_at)}</p>
                    </div>
                  </div>
                  {f.result_ship_id && (
                    <span className="text-xs text-green-400 bg-green-900/20 px-2 py-0.5 rounded">
                      Vaisseau créé
                    </span>
                  )}
                </div>
              ))
          )}
        </div>
      )}
    </div>
  )
}
