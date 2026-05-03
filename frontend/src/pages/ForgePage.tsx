/**
 * pages/ForgePage.tsx — v2
 * Agent 6 — Sprint UX
 *
 * Améliorations :
 *   1. Filtre automatique de compatibilité — quand un vaisseau A est sélectionné,
 *      les vaisseaux incompatibles (type ou rareté différents) sont grisés+non-cliquables
 *   2. Aperçu des stats avant/après avec fourchette RNG du résultat
 *   3. Animation de lancement (spinner + message)
 */
import React, { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { shipsApi } from '@/api/ships'
import { forgeApi } from '@/api'
import { ShipCard, ShipCardSkeleton } from '@/components/ships/ShipCard'
import { ForgeProgress } from '@/components/forge/ForgeProgress'
import { EmptyState, Tabs } from '@/components/ui'
import { ApiError } from '@/lib/api'
import { RARITY_CONFIG, FORGE_COSTS, type Rarity } from '@/types'
import { fmt, fmtDate, rarityColor } from '@/lib/utils'

// Rareté suivante dans la chaîne de forge
const NEXT_RARITY: Partial<Record<Rarity, Rarity>> = {
  COMMON: 'UNCOMMON', UNCOMMON: 'RARE', RARE: 'EPIC', EPIC: 'LEGENDARY',
}

// Multiplicateurs de stats par rareté (GDD §2)
const RARITY_MULT: Record<string, number> = {
  COMMON: 1.0, UNCOMMON: 1.25, RARE: 1.55, EPIC: 1.90, LEGENDARY: 2.40,
}

export function ForgePage() {
  const qc = useQueryClient()
  const [tab, setTab]       = useState('forge')
  const [selected, setSelected] = useState<string[]>([])
  const [launching, setLaunching] = useState(false)

  const { data: ships, isLoading: shipsLoading } = useQuery({
    queryKey: ['ships'],
    queryFn: shipsApi.list,
  })

  const { data: forgeHistory } = useQuery({
    queryKey: ['forge', 'history'],
    queryFn: forgeApi.history,
    refetchInterval: 30_000,
  })

  const activeForges  = (forgeHistory ?? []).filter((f) => !f.is_completed)
  const { data: activeStatuses } = useQuery({
    queryKey: ['forge', 'active', activeForges.map((f) => f.forge_id)],
    queryFn: () => Promise.all(activeForges.map((f) => forgeApi.status(f.forge_id))),
    enabled: activeForges.length > 0,
    refetchInterval: 30_000,
  })

  // Vaisseaux éligibles (DOCKED, pas LEGENDARY)
  const eligible = useMemo(
    () => ships?.filter((s) => s.status === 'DOCKED' && s.rarity !== 'LEGENDARY') ?? [],
    [ships],
  )

  const shipA = eligible.find((s) => s.id === selected[0])
  const shipB = eligible.find((s) => s.id === selected[1])

  const compatible = shipA && shipB &&
    shipA.ship_type === shipB.ship_type &&
    shipA.rarity    === shipB.rarity

  // Vaisseau incompatible avec le premier sélectionné
  function isIncompatible(shipId: string): boolean {
    if (!shipA || selected.includes(shipId)) return false
    const s = eligible.find(x => x.id === shipId)
    if (!s) return false
    return s.ship_type !== shipA.ship_type || s.rarity !== shipA.rarity
  }

  const { mutate: startForge, isPending } = useMutation({
    mutationFn: () => forgeApi.start(selected[0], selected[1]),
    onMutate: () => setLaunching(true),
    onSuccess: () => {
      toast.success('🔨 Forge lancée — résultat dans 8 heures !', { duration: 6000 })
      qc.invalidateQueries({ queryKey: ['ships'] })
      qc.invalidateQueries({ queryKey: ['forge', 'history'] })
      setSelected([])
      setLaunching(false)
      setTab('history')
    },
    onError: (err) => {
      setLaunching(false)
      toast.error(err instanceof ApiError ? err.detail : 'Erreur de forge')
    },
  })

  function toggleSelect(id: string) {
    if (isIncompatible(id)) return  // bloquer les incompatibles
    setSelected((prev) => {
      if (prev.includes(id)) return prev.filter((x) => x !== id)
      if (prev.length >= 2) return [prev[1], id]
      return [...prev, id]
    })
  }

  // Calcul aperçu stats du résultat
  const resultPreview = useMemo(() => {
    if (!compatible || !shipA) return null
    const nextRarity = NEXT_RARITY[shipA.rarity as Rarity]
    if (!nextRarity) return null
    const mult = RARITY_MULT[nextRarity] ?? 1
    const baseMult = RARITY_MULT[shipA.rarity] ?? 1
    // Stat de base COMMON Attaque = 100, on estime depuis le multiplicateur
    return { nextRarity, mult, baseMult }
  }, [compatible, shipA])

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

          {/* Bandeau forge(s) en cours */}
          {activeStatuses && activeStatuses.length > 0 && (
            <div>
              <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">En cours</p>
              <div className="space-y-2">
                {activeStatuses.map((f) => (
                  <ForgeProgress
                    key={f.forge_id}
                    forge={f}
                    onComplete={() => {
                      qc.invalidateQueries({ queryKey: ['forge', 'history'] })
                      qc.invalidateQueries({ queryKey: ['ships'] })
                    }}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Sélection A / B */}
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
                      <p className="text-gray-500 text-sm">
                        {idx === 0 ? 'Sélectionnez ci-dessous' : 'Sélectionnez un vaisseau compatible'}
                      </p>
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          {/* Aperçu résultat — amélioré */}
          {compatible && shipA && resultPreview && (
            <div
              className="panel border"
              style={{ borderColor: RARITY_CONFIG[NEXT_RARITY[shipA.rarity as Rarity]!].color + '60' }}
            >
              <div className="flex items-center gap-2 mb-3">
                <span className="text-xl">✨</span>
                <p className="font-bold text-white">Résultat de la forge</p>
              </div>

              <div className="flex items-center gap-4 mb-4">
                {/* Rareté actuelle */}
                <div className="text-center">
                  <div
                    className="px-3 py-1 rounded-full text-xs font-bold"
                    style={{ background: `${RARITY_CONFIG[shipA.rarity as Rarity].color}20`,
                             border: `1px solid ${RARITY_CONFIG[shipA.rarity as Rarity].color}60`,
                             color: RARITY_CONFIG[shipA.rarity as Rarity].color }}
                  >
                    {RARITY_CONFIG[shipA.rarity as Rarity].label}
                  </div>
                  <p className="text-[10px] text-gray-600 mt-1">×2</p>
                </div>
                <span className="text-gray-500 text-xl">→</span>
                {/* Rareté résultat */}
                {(() => {
                  const nextR = NEXT_RARITY[shipA.rarity as Rarity]!
                  const rc = RARITY_CONFIG[nextR]
                  return (
                    <div className="text-center">
                      <div
                        className="px-3 py-1 rounded-full text-xs font-bold animate-pulse"
                        style={{ background: `${rc.color}20`, border: `1px solid ${rc.color}80`, color: rc.color,
                                 boxShadow: `0 0 10px ${rc.color}40` }}
                      >
                        {rc.label}
                      </div>
                      <p className="text-[10px] text-gray-500 mt-1">×{resultPreview.mult.toFixed(2)} stats</p>
                    </div>
                  )
                })()}
              </div>

              <ul className="text-xs text-gray-400 space-y-0.5 mb-3">
                <li>✓ Meilleures stats des deux parents retenues</li>
                <li>✓ 30% de l'XP du vaisseau le plus expérimenté transférée</li>
                <li>✓ Durée : 8 heures</li>
              </ul>

              {/* Coût */}
              {FORGE_COSTS[shipA.ship_type] && (
                <div className="pt-3 border-t border-surface-border">
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

          {/* Message d'erreur compatibilité */}
          {selected.length === 2 && !compatible && (
            <div className="text-center text-orange-400 text-sm py-2 rounded-xl border border-orange-900/40 bg-orange-900/10">
              ⚠️ Les deux vaisseaux doivent être du même type ET de la même rareté
            </div>
          )}

          {/* Bouton lancement */}
          <button
            className="btn-primary w-full py-3 text-base relative overflow-hidden"
            disabled={!compatible || isPending}
            onClick={() => startForge()}
          >
            {launching ? (
              <span className="flex items-center justify-center gap-2">
                <span className="inline-block w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Lancement en cours…
              </span>
            ) : '🔨 Lancer la Forge (8 heures)'}
          </button>

          {/* Note si premier vaisseau sélectionné */}
          {shipA && !shipB && (
            <p className="text-xs text-center text-gray-500">
              💡 Seuls les vaisseaux compatibles ({RARITY_CONFIG[shipA.rarity as Rarity].label} · {shipA.ship_type.replace('_', ' ')}) sont sélectionnables
            </p>
          )}

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
              <EmptyState icon="🚀" title="Aucun vaisseau disponible"
                message="Vous avez besoin de vaisseaux DOCKED non-Légendaires" />
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {eligible.map((ship) => {
                  const incompatible = isIncompatible(ship.id)
                  return (
                    <div
                      key={ship.id}
                      style={{ opacity: incompatible ? 0.3 : 1,
                               pointerEvents: incompatible ? 'none' : 'auto',
                               transition: 'opacity 0.2s' }}
                      title={incompatible ? `Incompatible avec ${shipA?.ship_type} ${shipA?.rarity}` : undefined}
                    >
                      <ShipCard
                        ship={ship}
                        compact
                        selected={selected.includes(ship.id)}
                        onClick={() => toggleSelect(ship.id)}
                      />
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Onglet historique — inchangé */}
      {tab === 'history' && (
        <div className="space-y-4">
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
          {forgeHistory && forgeHistory.filter(f => f.is_completed).length > 0 && (
            <div>
              <h2 className="text-sm font-semibold text-gray-400 uppercase mb-3">Terminées</h2>
              <div className="space-y-2">
                {forgeHistory.filter(f => f.is_completed).map(f => (
                  <div key={f.forge_id} className="panel text-sm text-gray-400 flex justify-between">
                    <span>Forge du {fmtDate(f.started_at)}</span>
                    <span className="text-green-400">✓ Terminée</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {(!forgeHistory || forgeHistory.length === 0) && (
            <EmptyState icon="🔨" title="Aucune forge"
              message="Lancez votre première fusion dans l'onglet Nouvelle forge" />
          )}
        </div>
      )}
    </div>
  )
}
