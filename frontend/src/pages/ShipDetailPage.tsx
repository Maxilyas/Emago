import React, { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { shipsApi } from '@/api/ships'
import { modulesApi } from '@/api/modules'
import { ShipStatPanel } from '@/components/ships/ShipStatPanel'
import { Modal, LoadingSpinner, Tabs } from '@/components/ui'
import { ApiError } from '@/lib/api'
import { RARITY_CONFIG, MODULE_CONFIG, TRAIT_CONFIG, type Rarity, type PlayerModule } from '@/types'
import { rarityColor, rarityGlow, fmt, timeAgo } from '@/lib/utils'

export function ShipDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [tab, setTab] = useState('stats')
  const [installSlot, setInstallSlot] = useState<number | null>(null)

  const { data: ship, isLoading } = useQuery({
    queryKey: ['ship', id],
    queryFn: () => shipsApi.get(id!),
    enabled: !!id,
    refetchOnWindowFocus: false,
  })

  const { data: scars } = useQuery({
    queryKey: ['ship', id, 'scars'],
    queryFn: () => shipsApi.scars(id!),
    enabled: !!id && tab === 'scars',
  })

  const { mutate: demolish, isPending: demolishing } = useMutation({
    mutationFn: () => shipsApi.demolish(id!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ships'] })
      toast.success('Vaisseau démoli')
      navigate('/hangar')
    },
    onError: (err) => toast.error(err instanceof ApiError ? err.detail : 'Erreur'),
  })

  const { mutate: removeModule } = useMutation({
    mutationFn: (slot: number) => shipsApi.modules.remove(id!, slot),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ship', id] })
      toast.success('Module retiré')
    },
    onError: (err) => toast.error(err instanceof ApiError ? err.detail : 'Erreur'),
  })

  if (isLoading) return (
    <div className="flex items-center justify-center py-20">
      <LoadingSpinner size="lg" />
    </div>
  )

  if (!ship) return <p className="text-center text-gray-400 py-20">Vaisseau introuvable</p>

  const rarity = ship.rarity as Rarity
  const cfg = RARITY_CONFIG[rarity]
  const color = rarityColor(rarity)

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <button onClick={() => navigate('/hangar')} className="text-gray-400 hover:text-white transition-colors">
          ← Retour
        </button>
        {ship.status === 'DOCKED' && (
          <button
            className="btn-danger text-xs"
            disabled={demolishing}
            onClick={() => {
              if (confirm('Démolir ce vaisseau ? Cette action est irréversible.')) demolish()
            }}
          >
            🗑️ Démolir
          </button>
        )}
      </div>

      {/* Card header vaisseau */}
      <div
        className="panel border-2 relative overflow-hidden"
        style={{ borderColor: color, boxShadow: rarityGlow(rarity) }}
      >
        {rarity === 'LEGENDARY' && (
          <div
            className="absolute inset-0 opacity-10 pointer-events-none"
            style={{ background: `radial-gradient(ellipse at 50% 0%, ${color}, transparent 70%)` }}
          />
        )}
        <div className="relative flex items-center gap-4">
          <div className="text-5xl">🚀</div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span
                className="rarity-badge"
                style={{ color, borderColor: color, border: '1px solid' }}
              >
                {cfg.label}
              </span>
              <span className="text-xs text-gray-400 bg-surface-tertiary px-2 py-0.5 rounded-full">
                {ship.ship_class}
              </span>
              <span className="text-xs text-gray-400">{ship.status}</span>
            </div>
            <p className="text-lg font-bold mt-1">{ship.ship_type.replace('_', ' ')}</p>
            <p className="text-xs text-gray-500 mt-0.5">
              {'★'.repeat(ship.grade)}{'☆'.repeat(5 - ship.grade)} Grade {ship.grade} · {fmt(ship.combat_xp)} XP
            </p>
          </div>
        </div>
        {ship.parent_ship_id && (
          <div className="mt-3 text-xs text-purple-400 bg-purple-900/20 rounded px-2 py-1">
            🧬 Pedigree — héritier d'un ancêtre Grade 3+
          </div>
        )}
      </div>

      {/* Tabs */}
      <Tabs
        tabs={[
          { id: 'stats', label: 'Stats', icon: '📊' },
          { id: 'modules', label: 'Modules', icon: '🔧' },
          { id: 'scars', label: 'Cicatrices', icon: '🩹' },
        ]}
        active={tab}
        onChange={setTab}
      />

      {/* Contenu par tab */}
      {tab === 'stats' && (
        <ShipStatPanel
          stats={ship.current_stats}
          baseStats={ship.base_stats as unknown as Record<string, number>}
          rarity={rarity}
          combatXp={ship.combat_xp}
          grade={ship.grade}
        />
      )}

      {tab === 'modules' && (
        <ModuleManager
          ship={ship}
          onInstall={(slot) => setInstallSlot(slot)}
          onRemove={(slot) => removeModule(slot)}
        />
      )}

      {tab === 'scars' && (
        <div className="space-y-2">
          {!scars || scars.length === 0 ? (
            <div className="panel text-center py-8">
              <p className="text-gray-400">Aucune cicatrice pour l'instant</p>
              <p className="text-gray-600 text-xs mt-1">Les cicatrices s'obtiennent en survivant à des combats difficiles</p>
            </div>
          ) : (
            scars.map((scar) => (
              <div key={scar.scar_id} className="panel flex items-start gap-3">
                <span className="text-2xl shrink-0">🩹</span>
                <div>
                  <p className="text-sm font-medium text-purple-300 italic">"{scar.narrative}"</p>
                  <p className="text-xs text-gray-500 mt-1">{timeAgo(scar.earned_at)}</p>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Modal installation module */}
      <InstallModuleModal
        open={installSlot !== null}
        slot={installSlot ?? 0}
        shipId={id!}
        isPremiumSlot={
          installSlot !== null &&
          installSlot >= ship.current_stats.slots_total - ship.current_stats.slots_premium
        }
        onClose={() => setInstallSlot(null)}
        onInstalled={() => {
          qc.invalidateQueries({ queryKey: ['ship', id] })
          setInstallSlot(null)
        }}
      />
    </div>
  )
}

// ─── Module Manager ──────────────────────────────────────────────────────────
function ModuleManager({ ship, onInstall, onRemove }: {
  ship: ReturnType<typeof useQuery<import('@/types').ShipDetail>>['data'] & object
  onInstall: (slot: number) => void
  onRemove: (slot: number) => void
}) {
  if (!ship) return null
  const { slots_total, slots_premium, modules } = ship.current_stats
  const premiumStart = slots_total - slots_premium

  return (
    <div className="panel space-y-4">
      <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">Gestion des modules</h3>
      <div className="space-y-2">
        {Array.from({ length: slots_total }).map((_, i) => {
          const installed = modules.find((m) => m.slot === i)
          const isPremium = i >= premiumStart
          const cfg = installed ? MODULE_CONFIG[installed.type] : null

          return (
            <div
              key={i}
              className={`flex items-center gap-3 p-3 rounded-lg border ${
                isPremium
                  ? 'border-yellow-500/30 bg-yellow-900/10'
                  : 'border-surface-border'
              }`}
            >
              <div className="text-xs text-gray-500 w-6 shrink-0">
                #{i + 1}{isPremium && ' ✦'}
              </div>

              {installed && cfg ? (
                <>
                  <div className="flex-1">
                    <p className="text-sm font-medium">{cfg.icon} {cfg.label}</p>
                    <p className="text-xs text-gray-500">
                      Niveau {installed.level} · +{installed.boost_applied.toFixed(1)}%
                      {installed.affinity_bonus && <span className="text-green-400 ml-1">affinité</span>}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => onInstall(i)}
                      className="btn-secondary text-xs px-2 py-1"
                    >
                      Remplacer
                    </button>
                    <button
                      onClick={() => onRemove(i)}
                      className="btn-danger text-xs px-2 py-1"
                    >
                      Retirer
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <div className="flex-1">
                    <p className="text-sm text-gray-500 italic">
                      {isPremium ? 'Slot premium — Niveaux IV–V' : 'Slot vide — Niveaux I–III'}
                    </p>
                  </div>
                  <button
                    onClick={() => onInstall(i)}
                    className="btn-secondary text-xs px-2 py-1"
                  >
                    Installer
                  </button>
                </>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ─── Modal installation depuis l'inventaire ───────────────────────────────────
function InstallModuleModal({ open, slot, shipId, isPremiumSlot, onClose, onInstalled }: {
  open: boolean; slot: number; shipId: string; isPremiumSlot: boolean
  onClose: () => void; onInstalled: () => void
}) {
  const [selected, setSelected] = useState<string | null>(null)
  const [filterType, setFilterType] = useState<string>('ALL')
  const qc = useQueryClient()

  const { data: inventory = [], isLoading } = useQuery({
    queryKey: ['modules', 'inventory'],
    queryFn: modulesApi.inventory,
    enabled: open,
  })

  const available = inventory.filter((m: PlayerModule) => {
    if (m.is_destroyed || m.reinstall_charges <= 0) return false
    if (isPremiumSlot) return true
    return m.level <= 3
  })

  const filtered = filterType === 'ALL'
    ? available
    : available.filter((m: PlayerModule) => m.module_type === filterType)

  const { mutate, isPending } = useMutation({
    mutationFn: () => shipsApi.modules.install(shipId, slot, { module_id: selected! }),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['ship', shipId] })
      qc.invalidateQueries({ queryKey: ['modules'] })
      const capped = res.cap_reached.length > 0
      toast.success(
        capped ? `Module installé — cap +150% atteint sur : ${res.cap_reached.join(', ')}` : 'Module installé !',
        { duration: 4000 }
      )
      setSelected(null)
      onInstalled()
    },
    onError: (err) => toast.error(err instanceof ApiError ? err.detail : 'Erreur'),
  })

  const presentTypes = [...new Set(available.map((m: PlayerModule) => m.module_type))]

  return (
    <Modal open={open} onClose={onClose} title={`🔧 Installer dans le slot #${slot + 1}`} size="md">
      <div className="space-y-3">
        {isPremiumSlot && (
          <p className="text-xs text-yellow-500">✦ Slot premium — tous les niveaux autorisés</p>
        )}
        {!isPremiumSlot && (
          <p className="text-xs text-gray-500">Slot standard — niveaux I à III uniquement</p>
        )}

        {/* Filtres type */}
        {presentTypes.length > 1 && (
          <div className="flex flex-wrap gap-1.5">
            <button
              onClick={() => setFilterType('ALL')}
              className={`text-xs px-2.5 py-1 rounded-lg border transition-all ${
                filterType === 'ALL' ? 'border-accent-blue bg-accent-blue/10 text-accent-blue' : 'border-surface-border text-gray-500'
              }`}
            >
              Tous
            </button>
            {presentTypes.map((type) => {
              const cfg = MODULE_CONFIG[type as keyof typeof MODULE_CONFIG]
              return (
                <button
                  key={type}
                  onClick={() => setFilterType(type)}
                  className={`text-xs px-2.5 py-1 rounded-lg border transition-all ${
                    filterType === type ? 'border-accent-blue bg-accent-blue/10 text-accent-blue' : 'border-surface-border text-gray-500'
                  }`}
                >
                  {cfg?.icon} {cfg?.label ?? type}
                </button>
              )
            })}
          </div>
        )}

        {/* Liste modules */}
        <div className="max-h-64 overflow-y-auto space-y-1.5 pr-1">
          {isLoading ? (
            <div className="flex justify-center py-6"><LoadingSpinner /></div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-6">
              <p className="text-gray-400 text-sm">Aucun module disponible</p>
              <p className="text-gray-600 text-xs mt-1">
                Obtenez des modules via les expéditions, combats ou caisses de butin
              </p>
            </div>
          ) : (
            filtered.map((mod: PlayerModule) => {
              const cfg = MODULE_CONFIG[mod.module_type]
              const traitCfg = mod.trait ? TRAIT_CONFIG[mod.trait] : null
              const isSelected = selected === mod.id
              return (
                <button
                  key={mod.id}
                  onClick={() => setSelected(isSelected ? null : mod.id)}
                  className={`w-full text-left p-2.5 rounded-lg border transition-all ${
                    isSelected
                      ? 'border-accent-blue bg-accent-blue/10'
                      : 'border-surface-border hover:border-gray-500'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span>{cfg?.icon ?? '🔧'}</span>
                      <span className="text-sm text-gray-200">{cfg?.label ?? mod.module_type}</span>
                      <span className="text-xs text-gray-500">Nv.{mod.level}</span>
                    </div>
                    <span className="text-xs text-gray-500 font-mono">{mod.reinstall_charges}×</span>
                  </div>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {traitCfg && (
                      <span
                        className="text-[10px] px-1.5 py-0.5 rounded-full"
                        style={{ color: traitCfg.color, background: `${traitCfg.color}20` }}
                      >
                        {traitCfg.label}
                      </span>
                    )}
                    {mod.is_corrupted && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full text-red-400 bg-red-900/20">
                        ☠ Corrompu
                      </span>
                    )}
                    {mod.memory_ship_name && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full text-purple-400 bg-purple-900/20">
                        📜 {mod.memory_ship_name}
                      </span>
                    )}
                  </div>
                </button>
              )
            })
          )}
        </div>

        <button
          className="btn-primary w-full"
          disabled={!selected || isPending}
          onClick={() => mutate()}
        >
          {isPending ? '⏳ Installation…' : selected ? '🔧 Installer ce module' : 'Sélectionnez un module'}
        </button>
      </div>
    </Modal>
  )
}
