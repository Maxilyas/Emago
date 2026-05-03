import React, { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { shipsApi } from '@/api/ships'
import { modulesApi } from '@/api/modules'
import { ShipStatPanel } from '@/components/ships/ShipStatPanel'
import { Modal, LoadingSpinner, Tabs } from '@/components/ui'
import { ApiError } from '@/lib/api'
import {
  RARITY_CONFIG, MODULE_CONFIG, TRAIT_CONFIG,
  type Rarity, type PlayerModule, type ModuleType, type ShipDetail,
} from '@/types'
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

// ─── constantes partagées ─────────────────────────────────────────────────────
const LEVEL_COLORS: Record<number, string> = {
  1: 'text-gray-400 bg-gray-800',
  2: 'text-green-400 bg-green-900/30',
  3: 'text-blue-400 bg-blue-900/30',
  4: 'text-purple-400 bg-purple-900/30',
  5: 'text-yellow-400 bg-yellow-900/30',
}

const STAT_LABEL: Record<string, string> = {
  hull: 'Coque', shield: 'Bouclier', dps: 'DPS',
  speed: 'Vitesse', cargo: 'Cargo', stealth: 'Furtivité', support_aura: 'Aura soutien',
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
    <div className="panel space-y-3">
      <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">Gestion des modules</h3>
      <div className="space-y-2">
        {Array.from({ length: slots_total }).map((_, i) => {
          const installed = modules.find((m) => m.slot === i)
          const isPremium = i >= premiumStart
          const cfg = installed ? MODULE_CONFIG[installed.type] : null
          const traitCfg = installed?.trait ? TRAIT_CONFIG[installed.trait] : null
          const stat = installed ? MODULE_CONFIG[installed.type]?.stat : null

          return (
            <div
              key={i}
              className={`p-3 rounded-lg border ${
                isPremium ? 'border-yellow-500/30 bg-yellow-900/10' : 'border-surface-border'
              }`}
            >
              <div className="flex items-start gap-3">
                <div className="text-xs text-gray-500 w-6 pt-0.5 shrink-0">
                  #{i + 1}{isPremium && <span className="text-yellow-500"> ✦</span>}
                </div>

                {installed && cfg ? (
                  <>
                    <div className="flex-1 min-w-0">
                      {/* Ligne principale */}
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-medium">{cfg.icon} {cfg.label}</span>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded font-mono font-semibold ${LEVEL_COLORS[installed.level]}`}>
                          Nv.{installed.level}
                        </span>
                        {installed.is_corrupted && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded text-red-400 bg-red-900/20">☠ Corrompu</span>
                        )}
                      </div>
                      {/* Ligne stats */}
                      <div className="flex items-center gap-2 mt-1 flex-wrap">
                        <span className="text-xs text-green-400 font-mono">
                          +{installed.boost_applied.toFixed(1)}% {stat ? STAT_LABEL[stat] : ''}
                        </span>
                        {installed.affinity_bonus && (
                          <span className="text-[10px] text-green-300 bg-green-900/20 px-1.5 py-0.5 rounded">Affinité ×1.15</span>
                        )}
                        {traitCfg && (
                          <span
                            className="text-[10px] px-1.5 py-0.5 rounded-full"
                            style={{ color: traitCfg.color, background: `${traitCfg.color}20` }}
                          >
                            {traitCfg.label}
                          </span>
                        )}
                        {installed.reinstall_charges !== undefined && (
                          <span className={`text-[10px] font-mono ${installed.reinstall_charges <= 1 ? 'text-red-400' : 'text-gray-500'}`}>
                            {installed.reinstall_charges}× charges
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="flex gap-1.5 shrink-0">
                      <button onClick={() => onInstall(i)} className="btn-secondary text-xs px-2 py-1">Remplacer</button>
                      <button onClick={() => onRemove(i)} className="btn-danger text-xs px-2 py-1">Retirer</button>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="flex-1">
                      <p className="text-sm text-gray-500 italic">
                        {isPremium ? 'Slot premium — Niveaux IV–V' : 'Slot vide — Niveaux I–III'}
                      </p>
                    </div>
                    <button onClick={() => onInstall(i)} className="btn-secondary text-xs px-2 py-1">Installer</button>
                  </>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ─── Estimation du boost côté client (approximation) ─────────────────────────
const _MOD_BOOST_RATE: Record<number, number> = { 1: 0.08, 2: 0.14, 3: 0.22, 4: 0.32, 5: 0.44 }
const _TRAIT_MULT: Record<string, number> = {
  battle_hardened: 1.10, overclocked: 1.15, military_grade: 1.12, lightweight: 1.05,
}
const _AFFINITY_CLASS: Partial<Record<ModuleType, string>> = {
  PROPELLER: 'EXPLORATION', ARMOR: 'DEFENSE', CANNON: 'ATTACK',
  EMITTER: 'SUPPORT', SHIELD: 'DEFENSE', CARGO: 'EXPLORATION',
}

function estimateBoostRate(mod: PlayerModule, shipClass: string): number {
  let rate = _MOD_BOOST_RATE[mod.level] ?? 0
  if (mod.trait && _TRAIT_MULT[mod.trait]) rate *= _TRAIT_MULT[mod.trait]
  if (mod.bonus_trait && _TRAIT_MULT[mod.bonus_trait]) rate *= _TRAIT_MULT[mod.bonus_trait]
  if (_AFFINITY_CLASS[mod.module_type] === shipClass) rate *= 1.15
  return rate
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

  const shipData = qc.getQueryData<ShipDetail>(['ship', shipId])

  const available = inventory.filter((m: PlayerModule) => {
    if (m.is_destroyed || m.reinstall_charges <= 0) return false
    if (isPremiumSlot) return true
    return m.level <= 3
  })

  const filtered = filterType === 'ALL'
    ? available
    : available.filter((m: PlayerModule) => m.module_type === filterType)

  const selectedModule: PlayerModule | undefined = selected
    ? available.find((m: PlayerModule) => m.id === selected)
    : undefined

  const { mutate, isPending } = useMutation({
    mutationFn: () => shipsApi.modules.install(shipId, slot, { module_id: selected! }),
    onSuccess: (res) => {
      qc.setQueryData(['ship', shipId], (old: any) => old ? { ...old, current_stats: res.current_stats } : old)
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
    <Modal open={open} onClose={onClose} title={`🔧 Installer dans le slot #${slot + 1}`} size="lg">
      <div className="space-y-3">
        <p className="text-xs text-gray-500">
          {isPremiumSlot ? '✦ Slot premium — tous les niveaux autorisés' : 'Slot standard — niveaux I à III uniquement'}
        </p>

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
              const cfg = MODULE_CONFIG[type as ModuleType]
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
        <div className="max-h-56 overflow-y-auto space-y-1.5 pr-1">
          {isLoading ? (
            <div className="flex justify-center py-6"><LoadingSpinner /></div>
          ) : filtered.length === 0 ? (
            <div className="text-center py-6">
              <p className="text-gray-400 text-sm">Aucun module disponible</p>
              <p className="text-gray-600 text-xs mt-1">Obtenez des modules via les expéditions, combats ou caisses de butin</p>
            </div>
          ) : (
            filtered.map((mod: PlayerModule) => {
              const cfg = MODULE_CONFIG[mod.module_type]
              const stat = cfg?.stat ?? ''
              const traitCfg = mod.trait ? TRAIT_CONFIG[mod.trait] : null
              const bonusCfg = mod.bonus_trait ? TRAIT_CONFIG[mod.bonus_trait] : null
              const isSelected = selected === mod.id
              const boostPct = shipData
                ? (estimateBoostRate(mod, shipData.ship_class) * 100).toFixed(1)
                : null

              return (
                <button
                  key={mod.id}
                  onClick={() => setSelected(isSelected ? null : mod.id)}
                  className={`w-full text-left p-3 rounded-lg border transition-all ${
                    isSelected ? 'border-accent-blue bg-accent-blue/10' : 'border-surface-border hover:border-gray-500'
                  }`}
                >
                  {/* Ligne principale */}
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-base">{cfg?.icon ?? '🔧'}</span>
                      <span className="text-sm font-medium text-gray-100">{cfg?.label ?? mod.module_type}</span>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded font-semibold font-mono ${LEVEL_COLORS[mod.level]}`}>
                        Nv.{mod.level}
                      </span>
                    </div>
                    <span className={`text-[10px] font-mono shrink-0 ${mod.reinstall_charges <= 1 ? 'text-red-400' : 'text-gray-500'}`}>
                      {mod.reinstall_charges}× charges
                    </span>
                  </div>

                  {/* Ligne effet */}
                  <div className="mt-1 flex items-center gap-2 flex-wrap">
                    {boostPct !== null && (
                      <span className="text-xs text-green-400 font-mono">~+{boostPct}% {STAT_LABEL[stat] ?? stat}</span>
                    )}
                    {traitCfg && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full" style={{ color: traitCfg.color, background: `${traitCfg.color}20` }}>
                        {traitCfg.label}
                      </span>
                    )}
                    {bonusCfg && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full" style={{ color: bonusCfg.color, background: `${bonusCfg.color}20` }}>
                        {bonusCfg.label}
                      </span>
                    )}
                    {mod.is_corrupted && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded text-red-400 bg-red-900/20">
                        ☠ Corrompu — {mod.corruption_malus_stat ?? '?'} pénalisé
                      </span>
                    )}
                    {mod.memory_ship_name && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded text-purple-400 bg-purple-900/20">
                        📜 {mod.memory_ship_name}
                      </span>
                    )}
                  </div>
                </button>
              )
            })
          )}
        </div>

        {/* Preview stat si module sélectionné */}
        {selectedModule && shipData && (() => {
          const stat = MODULE_CONFIG[selectedModule.module_type]?.stat ?? ''
          const statLabel = STAT_LABEL[stat] ?? stat
          const currentVal = (shipData.current_stats as any)[stat] as number | undefined
          const baseVal = (shipData.base_stats as any)[stat] as number | undefined
          if (!currentVal || !baseVal) return null
          const delta = Math.round(baseVal * estimateBoostRate(selectedModule, shipData.ship_class))
          const estimated = currentVal + delta
          return (
            <div className="rounded-lg border border-accent-blue/30 bg-accent-blue/5 p-3">
              <p className="text-xs font-semibold text-accent-blue mb-1.5">✦ Aperçu estimé</p>
              <div className="flex items-center gap-2 text-sm">
                <span className="text-gray-400">{statLabel} :</span>
                <span className="font-mono text-gray-300">{currentVal.toLocaleString('fr-FR')}</span>
                <span className="text-gray-600">→</span>
                <span className="font-mono text-green-400">~{estimated.toLocaleString('fr-FR')}</span>
                <span className="text-xs text-green-500 font-mono">+{delta.toLocaleString('fr-FR')}</span>
              </div>
              <p className="text-[10px] text-gray-600 mt-1">Estimation — résultats exacts calculés par le serveur</p>
            </div>
          )
        })()}

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
