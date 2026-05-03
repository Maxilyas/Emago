import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { modulesApi } from '@/api/modules'
import { planetsApi } from '@/api/index'
import { Modal, LoadingSpinner, Tabs } from '@/components/ui'
import { ApiError } from '@/lib/api'
import {
  MODULE_CONFIG, TRAIT_CONFIG, LOOT_CRATE_CONFIG,
  type ModuleType, type PlayerModule, type LootCrate, type LootCrateOpenResult,
} from '@/types'
import { timeAgo } from '@/lib/utils'

// ─── Helpers ─────────────────────────────────────────────────────────────────

function chargesColor(charges: number): string {
  if (charges >= 4) return '#4ade80'
  if (charges === 3) return '#a3e635'
  if (charges === 2) return '#facc15'
  if (charges === 1) return '#f97316'
  return '#ef4444'
}

function ModuleBadge({ mod, selected, onClick }: {
  mod: PlayerModule
  selected?: boolean
  onClick?: () => void
}) {
  const cfg = MODULE_CONFIG[mod.module_type]
  const traitCfg = mod.trait ? TRAIT_CONFIG[mod.trait] : null

  return (
    <button
      onClick={onClick}
      disabled={mod.is_destroyed || !onClick}
      className={`relative text-left p-3 rounded-lg border transition-all ${
        mod.is_destroyed
          ? 'opacity-40 cursor-not-allowed border-surface-border'
          : selected
          ? 'border-accent-blue bg-accent-blue/10'
          : onClick
          ? 'border-surface-border hover:border-gray-500 cursor-pointer'
          : 'border-surface-border cursor-default'
      }`}
    >
      {/* En-tête */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5">
          <span className="text-base">{cfg?.icon ?? '🔧'}</span>
          <span className="text-sm font-medium text-white">{cfg?.label ?? mod.module_type}</span>
          <span className="text-xs text-gray-500">Nv.{mod.level}</span>
        </div>
        <span
          className="text-xs font-mono font-bold"
          style={{ color: chargesColor(mod.reinstall_charges) }}
        >
          {mod.reinstall_charges}×
        </span>
      </div>

      {/* Badges */}
      <div className="mt-1.5 flex flex-wrap gap-1">
        {mod.trait && traitCfg && (
          <span
            className="text-[10px] px-1.5 py-0.5 rounded-full font-medium"
            style={{ color: traitCfg.color, background: `${traitCfg.color}20`, border: `1px solid ${traitCfg.color}40` }}
          >
            {traitCfg.label}
          </span>
        )}
        {mod.is_corrupted && (
          <span className="text-[10px] px-1.5 py-0.5 rounded-full text-red-400 bg-red-900/20 border border-red-500/30">
            ☠ Corrompu
          </span>
        )}
        {mod.is_destroyed && (
          <span className="text-[10px] px-1.5 py-0.5 rounded-full text-gray-500 bg-gray-800 border border-gray-700">
            Détruit
          </span>
        )}
        {mod.memory_ship_name && (
          <span className="text-[10px] px-1.5 py-0.5 rounded-full text-purple-400 bg-purple-900/20 border border-purple-500/30">
            📜 {mod.memory_ship_name}
          </span>
        )}
      </div>
    </button>
  )
}

// ─── Tab Inventaire ───────────────────────────────────────────────────────────

function InventoryTab() {
  const [filterType, setFilterType] = useState<ModuleType | 'ALL'>('ALL')
  const [showDestroyed, setShowDestroyed] = useState(false)

  const { data: modules = [], isLoading } = useQuery({
    queryKey: ['modules', 'inventory'],
    queryFn: modulesApi.inventory,
  })

  const { data: shardData } = useQuery({
    queryKey: ['modules', 'shards'],
    queryFn: modulesApi.shards,
  })

  const filtered = modules.filter((m) => {
    if (!showDestroyed && m.is_destroyed) return false
    if (filterType !== 'ALL' && m.module_type !== filterType) return false
    return true
  })

  return (
    <div className="space-y-4">
      {/* Shards */}
      {shardData && Object.keys(shardData.shards).length > 0 && (
        <div className="panel">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Fragments</h3>
          <div className="flex flex-wrap gap-2">
            {Object.entries(shardData.shards).map(([type, count]) => {
              const cfg = MODULE_CONFIG[type as ModuleType]
              return (
                <div key={type} className="flex items-center gap-1.5 bg-surface-tertiary rounded-lg px-2 py-1.5 text-xs">
                  <span>{cfg?.icon ?? '🔧'}</span>
                  <span className="text-gray-300">{cfg?.label ?? type}</span>
                  <span className="font-bold text-yellow-400">{count}</span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Filtres */}
      <div className="flex flex-wrap gap-2 items-center">
        <button
          onClick={() => setFilterType('ALL')}
          className={`text-xs px-3 py-1.5 rounded-lg border transition-all ${
            filterType === 'ALL' ? 'border-accent-blue bg-accent-blue/10 text-accent-blue' : 'border-surface-border text-gray-400'
          }`}
        >
          Tous ({modules.filter(m => showDestroyed || !m.is_destroyed).length})
        </button>
        {(Object.keys(MODULE_CONFIG) as ModuleType[]).map((type) => {
          const cfg = MODULE_CONFIG[type]
          const count = modules.filter(m => m.module_type === type && (showDestroyed || !m.is_destroyed)).length
          if (count === 0) return null
          return (
            <button
              key={type}
              onClick={() => setFilterType(type)}
              className={`text-xs px-3 py-1.5 rounded-lg border transition-all ${
                filterType === type ? 'border-accent-blue bg-accent-blue/10 text-accent-blue' : 'border-surface-border text-gray-400'
              }`}
            >
              {cfg.icon} {cfg.label} ({count})
            </button>
          )
        })}
        <label className="flex items-center gap-1.5 text-xs text-gray-500 cursor-pointer ml-auto">
          <input
            type="checkbox"
            checked={showDestroyed}
            onChange={(e) => setShowDestroyed(e.target.checked)}
            className="accent-accent-blue"
          />
          Voir détruits
        </label>
      </div>

      {/* Liste */}
      {isLoading ? (
        <div className="flex justify-center py-10"><LoadingSpinner /></div>
      ) : filtered.length === 0 ? (
        <div className="panel text-center py-10">
          <p className="text-gray-400">Aucun module dans l'inventaire</p>
          <p className="text-gray-600 text-xs mt-1">
            Obtenez des modules via les expéditions, les combats ou en ouvrant des caisses de butin
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
          {filtered.map((mod) => (
            <ModuleBadge key={mod.id} mod={mod} />
          ))}
        </div>
      )}
    </div>
  )
}

// ─── Tab Artisanat ────────────────────────────────────────────────────────────

function CraftTab() {
  const qc = useQueryClient()
  const [selected, setSelected] = useState<string[]>([])
  const [planetId, setPlanetId] = useState<string>('')

  const { data: modules = [] } = useQuery({
    queryKey: ['modules', 'inventory'],
    queryFn: modulesApi.inventory,
  })
  const { data: planets = [] } = useQuery({
    queryKey: ['planets'],
    queryFn: planetsApi.list,
  })

  // Autos-select planète d'origine
  React.useEffect(() => {
    if (planets.length > 0 && !planetId) {
      const hw = planets.find(p => p.is_homeworld) ?? planets[0]
      setPlanetId(hw.id)
    }
  }, [planets, planetId])

  const available = modules.filter(m => !m.is_destroyed && m.reinstall_charges > 0)

  const toggle = (id: string) => {
    if (selected.includes(id)) {
      setSelected(selected.filter(s => s !== id))
      return
    }
    if (selected.length >= 3) return
    const mod = modules.find(m => m.id === id)
    if (!mod) return
    // Les 3 modules doivent être du même type ET niveau
    if (selected.length > 0) {
      const first = modules.find(m => m.id === selected[0])!
      if (first.module_type !== mod.module_type || first.level !== mod.level) {
        toast.error('Les 3 modules doivent être du même type et niveau')
        return
      }
    }
    setSelected([...selected, id])
  }

  const selMod = selected.length > 0 ? modules.find(m => m.id === selected[0]) : null
  const resultLevel = selMod ? Math.min(5, selMod.level + 1) as 1|2|3|4|5 : null

  const { mutate: craft, isPending } = useMutation({
    mutationFn: () => modulesApi.craft({ module_ids: selected, planet_id: planetId }),
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: ['modules'] })
      const cfg = MODULE_CONFIG[result.module_type]
      toast.success(`✨ Module ${cfg?.label ?? result.module_type} Nv.${result.level} créé !`)
      setSelected([])
    },
    onError: (err) => toast.error(err instanceof ApiError ? err.detail : 'Erreur artisanat'),
  })

  // Regrouper par type+niveau pour faciliter la sélection
  const groups: Record<string, PlayerModule[]> = {}
  for (const mod of available) {
    const key = `${mod.module_type}_${mod.level}`
    if (!groups[key]) groups[key] = []
    groups[key].push(mod)
  }

  return (
    <div className="space-y-4">
      <div className="panel">
        <h3 className="text-sm font-semibold text-gray-300 mb-1">Comment ça marche</h3>
        <p className="text-xs text-gray-500">
          Sélectionnez <span className="text-white font-medium">3 modules identiques</span> (même type + même niveau)
          pour les fusionner en un module du niveau supérieur. Le nouveau module hérite d'un trait potentiel.
        </p>
      </div>

      {/* Sélection en cours */}
      <div className="panel">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-gray-300">
            Sélection ({selected.length}/3)
            {selMod && (
              <span className="ml-2 text-gray-500 font-normal text-xs">
                {MODULE_CONFIG[selMod.module_type]?.label} Nv.{selMod.level}
              </span>
            )}
          </h3>
          {resultLevel && selected.length === 3 && (
            <span className="text-xs text-green-400">
              → {MODULE_CONFIG[selMod!.module_type]?.icon} Nv.{resultLevel}
            </span>
          )}
        </div>
        <div className="flex gap-2">
          {[0, 1, 2].map((i) => {
            const mod = selected[i] ? modules.find(m => m.id === selected[i]) : null
            return (
              <div
                key={i}
                className={`flex-1 h-16 rounded-lg border flex flex-col items-center justify-center text-xs transition-all ${
                  mod ? 'border-accent-blue bg-accent-blue/10' : 'border-surface-border border-dashed text-gray-600'
                }`}
              >
                {mod ? (
                  <>
                    <span className="text-lg">{MODULE_CONFIG[mod.module_type]?.icon}</span>
                    <span className="text-gray-400">Nv.{mod.level}</span>
                  </>
                ) : (
                  <span>Slot {i + 1}</span>
                )}
              </div>
            )
          })}
        </div>

        {planets.length > 0 && (
          <div className="mt-3">
            <label className="text-xs text-gray-400 block mb-1">Planète (paiement des ressources)</label>
            <select
              value={planetId}
              onChange={e => setPlanetId(e.target.value)}
              className="w-full bg-surface-secondary border border-surface-border rounded-lg px-3 py-2 text-sm text-gray-300"
            >
              {planets.map(p => (
                <option key={p.id} value={p.id}>{p.name}{p.is_homeworld ? ' ★' : ''}</option>
              ))}
            </select>
          </div>
        )}

        <button
          className="btn-primary w-full mt-3"
          disabled={selected.length < 3 || !planetId || isPending}
          onClick={() => craft()}
        >
          {isPending ? '⏳ Fusion…' : '✨ Fusionner 3 → 1'}
        </button>
        {selected.length > 0 && (
          <button className="btn-secondary w-full mt-2 text-xs" onClick={() => setSelected([])}>
            Annuler la sélection
          </button>
        )}
      </div>

      {/* Modules disponibles */}
      {Object.entries(groups).length === 0 ? (
        <div className="panel text-center py-8">
          <p className="text-gray-400">Aucun module disponible pour la fusion</p>
          <p className="text-gray-600 text-xs mt-1">Il faut au moins 3 modules du même type et niveau</p>
        </div>
      ) : (
        Object.entries(groups).map(([key, mods]) => {
          const [type, lvl] = key.split('_') as [ModuleType, string]
          const cfg = MODULE_CONFIG[type]
          const canCraft = mods.length >= 3 && Number(lvl) < 5
          return (
            <div key={key} className="panel space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-300">
                  {cfg?.icon} {cfg?.label} — Niveau {lvl}
                </span>
                <span className={`text-xs font-mono ${canCraft ? 'text-green-400' : 'text-gray-600'}`}>
                  {mods.length} disponibles{canCraft ? ' — craftable' : ''}
                </span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                {mods.map((mod) => (
                  <ModuleBadge
                    key={mod.id}
                    mod={mod}
                    selected={selected.includes(mod.id)}
                    onClick={canCraft ? () => toggle(mod.id) : undefined}
                  />
                ))}
              </div>
            </div>
          )
        })
      )}
    </div>
  )
}

// ─── Tab Caisses de Butin ─────────────────────────────────────────────────────

function CrateOpenAnimation({ type }: { type: string }) {
  const cfg = LOOT_CRATE_CONFIG[type as keyof typeof LOOT_CRATE_CONFIG] ?? LOOT_CRATE_CONFIG.STANDARD
  return (
    <div className="flex flex-col items-center gap-4 py-6">
      <div
        className="text-7xl animate-bounce"
        style={{ filter: `drop-shadow(0 0 20px ${cfg.glow})` }}
      >
        {cfg.icon}
      </div>
      <p className="text-gray-400 text-sm animate-pulse">Ouverture en cours…</p>
    </div>
  )
}

function RevealModal({ result, onClose }: { result: LootCrateOpenResult; onClose: () => void }) {
  if (result.empty) {
    return (
      <div className="text-center space-y-4 py-4">
        <div className="text-5xl">📭</div>
        <p className="text-gray-300 font-medium">Caisse vide…</p>
        <p className="text-gray-500 text-xs">Parfois le vide, parfois la gloire.</p>
        <button className="btn-secondary w-full" onClick={onClose}>Fermer</button>
      </div>
    )
  }

  const hasShards = Object.values(result.shards).some(v => v > 0)

  return (
    <div className="space-y-4 py-2">
      {result.module && (
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">Module obtenu</p>
          <div className="panel border-accent-blue/40" style={{ boxShadow: '0 0 20px rgba(45,125,210,0.2)' }}>
            <ModuleBadge mod={result.module} />
          </div>
        </div>
      )}
      {hasShards && (
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">Fragments obtenus</p>
          <div className="flex flex-wrap gap-2">
            {Object.entries(result.shards).filter(([, v]) => v > 0).map(([type, count]) => {
              const cfg = MODULE_CONFIG[type as ModuleType]
              return (
                <div key={type} className="flex items-center gap-1.5 bg-surface-tertiary rounded-lg px-2 py-1.5 text-xs">
                  <span>{cfg?.icon ?? '🔧'}</span>
                  <span className="text-gray-300">{cfg?.label ?? type}</span>
                  <span className="font-bold text-yellow-400">+{count}</span>
                </div>
              )
            })}
          </div>
        </div>
      )}
      <button className="btn-primary w-full" onClick={onClose}>
        Continuer
      </button>
    </div>
  )
}

function CratesTab() {
  const qc = useQueryClient()
  const [opening, setOpening] = useState<string | null>(null)
  const [reveal, setReveal] = useState<LootCrateOpenResult | null>(null)

  const { data: crates = [], isLoading } = useQuery({
    queryKey: ['loot-crates'],
    queryFn: modulesApi.crates.list,
    refetchInterval: 60_000,
  })

  const { mutate: openCrate } = useMutation({
    mutationFn: (id: string) => modulesApi.crates.open(id),
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: ['loot-crates'] })
      qc.invalidateQueries({ queryKey: ['modules'] })
      setOpening(null)
      setReveal(result)
    },
    onError: (err) => {
      setOpening(null)
      toast.error(err instanceof ApiError ? err.detail : 'Erreur ouverture')
    },
  })

  const handleOpen = (id: string) => {
    setOpening(id)
    setTimeout(() => openCrate(id), 1200)
  }

  const activeCrate = opening ? crates.find(c => c.id === opening) : null

  return (
    <div className="space-y-4">
      {/* Modal ouverture animée */}
      <Modal
        open={opening !== null}
        onClose={() => {}}
        title={activeCrate ? `${LOOT_CRATE_CONFIG[activeCrate.crate_type as keyof typeof LOOT_CRATE_CONFIG]?.label ?? 'Caisse'}` : 'Ouverture'}
        size="sm"
      >
        {activeCrate && <CrateOpenAnimation type={activeCrate.crate_type} />}
      </Modal>

      {/* Modal révélation */}
      <Modal
        open={reveal !== null}
        onClose={() => setReveal(null)}
        title="🎁 Contenu de la caisse"
        size="sm"
      >
        {reveal && <RevealModal result={reveal} onClose={() => setReveal(null)} />}
      </Modal>

      {isLoading ? (
        <div className="flex justify-center py-10"><LoadingSpinner /></div>
      ) : crates.length === 0 ? (
        <div className="panel text-center py-12">
          <div className="text-4xl mb-3">📭</div>
          <p className="text-gray-400">Aucune caisse de butin</p>
          <p className="text-gray-600 text-xs mt-1">
            Gagnez des caisses en remportant des combats ou en terminant des expéditions
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {crates.map((crate) => {
            const cfg = LOOT_CRATE_CONFIG[crate.crate_type as keyof typeof LOOT_CRATE_CONFIG] ?? LOOT_CRATE_CONFIG.STANDARD
            return (
              <div
                key={crate.id}
                className="panel border transition-all hover:scale-[1.01]"
                style={{ borderColor: `${cfg.color}40`, boxShadow: `0 0 12px ${cfg.glow}` }}
              >
                {/* Type + icône */}
                <div className="flex items-center gap-3 mb-3">
                  <div
                    className="text-3xl w-12 h-12 flex items-center justify-center rounded-lg"
                    style={{ background: `${cfg.color}15`, border: `1px solid ${cfg.color}30` }}
                  >
                    {cfg.icon}
                  </div>
                  <div>
                    <p className="text-sm font-semibold" style={{ color: cfg.color }}>{cfg.label}</p>
                    {crate.source_ship_name && (
                      <p className="text-xs text-gray-500">📜 {crate.source_ship_name}</p>
                    )}
                    <p className="text-xs text-gray-600">{timeAgo(crate.obtained_at)}</p>
                  </div>
                </div>

                {/* Source */}
                <div className="flex items-center gap-1.5 mb-3">
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-surface-tertiary text-gray-400">
                    {crate.source === 'EXPEDITION' ? '🚀 Expédition' : crate.source === 'COMBAT' ? '⚔️ Combat' : crate.source}
                  </span>
                </div>

                <button
                  className="btn-primary w-full text-sm"
                  onClick={() => handleOpen(crate.id)}
                  disabled={opening !== null}
                >
                  Ouvrir
                </button>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ─── Page principale ──────────────────────────────────────────────────────────

export function ModulesPage() {
  const [tab, setTab] = useState('crates')

  const { data: crates = [] } = useQuery({
    queryKey: ['loot-crates'],
    queryFn: modulesApi.crates.list,
    refetchInterval: 60_000,
  })

  const crateCount = crates.length

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Modules</h1>
          <p className="text-xs text-gray-500 mt-0.5">Inventaire, artisanat et caisses de butin</p>
        </div>
        {crateCount > 0 && (
          <div
            className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium"
            style={{ background: 'rgba(167,139,250,0.1)', border: '1px solid rgba(167,139,250,0.3)', color: '#a78bfa' }}
          >
            <span>🎁</span>
            <span>{crateCount} caisse{crateCount > 1 ? 's' : ''} à ouvrir</span>
          </div>
        )}
      </div>

      <Tabs
        tabs={[
          { id: 'crates',    label: `Caisses${crateCount > 0 ? ` (${crateCount})` : ''}`, icon: '🎁' },
          { id: 'inventory', label: 'Inventaire', icon: '🔧' },
          { id: 'craft',     label: 'Artisanat',  icon: '✨' },
        ]}
        active={tab}
        onChange={setTab}
      />

      {tab === 'crates'    && <CratesTab />}
      {tab === 'inventory' && <InventoryTab />}
      {tab === 'craft'     && <CraftTab />}
    </div>
  )
}
