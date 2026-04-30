import React, { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { shipsApi } from '@/api/ships'
import { ShipStatPanel } from '@/components/ships/ShipStatPanel'
import { Modal, LoadingSpinner, Badge, Tabs } from '@/components/ui'
import { ApiError } from '@/lib/api'
import { RARITY_CONFIG, MODULE_CONFIG, type ModuleType, type Rarity } from '@/types'
import { rarityColor, rarityGlow, fmt, timeAgo } from '@/lib/utils'

const MODULE_LEVELS = [1, 2, 3, 4, 5] as const

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

// ─── Modal installation ───────────────────────────────────────────────────────
function InstallModuleModal({ open, slot, shipId, isPremiumSlot, onClose, onInstalled }: {
  open: boolean; slot: number; shipId: string; isPremiumSlot: boolean
  onClose: () => void; onInstalled: () => void
}) {
  const [moduleType, setModuleType] = useState<ModuleType>('CANNON')
  const [level, setLevel] = useState<1 | 2 | 3 | 4 | 5>(1)
  const qc = useQueryClient()

  const allowedLevels = isPremiumSlot ? MODULE_LEVELS : MODULE_LEVELS.slice(0, 3) as unknown as typeof MODULE_LEVELS

  const { mutate, isPending } = useMutation({
    mutationFn: () => shipsApi.modules.install(shipId, slot, { module_type: moduleType, level }),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['ship', shipId] })
      const capped = res.cap_reached.length > 0
      toast.success(
        capped ? `Module installé — cap +150% atteint sur : ${res.cap_reached.join(', ')}` : 'Module installé !',
        { duration: 4000 }
      )
      onInstalled()
    },
    onError: (err) => toast.error(err instanceof ApiError ? err.detail : 'Erreur'),
  })

  return (
    <Modal open={open} onClose={onClose} title={`🔧 Installer dans le slot #${slot + 1}`} size="sm">
      <div className="space-y-4">
        <div>
          <label className="block text-sm text-gray-400 mb-2">Type de module</label>
          <div className="grid grid-cols-2 gap-2">
            {(Object.entries(MODULE_CONFIG) as [ModuleType, typeof MODULE_CONFIG[ModuleType]][]).map(([type, cfg]) => (
              <button
                key={type}
                onClick={() => setModuleType(type)}
                className={`p-2 rounded-lg border text-left text-sm transition-all ${
                  moduleType === type
                    ? 'border-accent-blue bg-accent-blue/10 text-accent-blue'
                    : 'border-surface-border text-gray-300 hover:border-gray-500'
                }`}
              >
                {cfg.icon} {cfg.label}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-sm text-gray-400 mb-2">Niveau</label>
          <div className="flex gap-2">
            {MODULE_LEVELS.map((l) => {
              const disabled = !allowedLevels.includes(l)
              return (
                <button
                  key={l}
                  onClick={() => !disabled && setLevel(l)}
                  disabled={disabled}
                  title={disabled ? 'Slot standard — niveau IV/V nécessite un slot premium' : `Niveau ${l}`}
                  className={`flex-1 py-2 rounded-lg border text-sm font-medium transition-all ${
                    level === l && !disabled
                      ? 'border-accent-blue bg-accent-blue/10 text-accent-blue'
                      : disabled
                      ? 'border-surface-border text-gray-700 cursor-not-allowed'
                      : 'border-surface-border text-gray-300 hover:border-gray-500'
                  }`}
                >
                  {l === 4 || l === 5 ? `${l}✦` : l}
                </button>
              )
            })}
          </div>
          {isPremiumSlot && <p className="text-xs text-yellow-500 mt-1">✦ Slot premium — niveaux IV et V autorisés</p>}
        </div>

        <button className="btn-primary w-full" disabled={isPending} onClick={() => mutate()}>
          {isPending ? '⏳ Installation…' : '🔧 Installer'}
        </button>
      </div>
    </Modal>
  )
}
