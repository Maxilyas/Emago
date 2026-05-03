/**
 * ModuleHoverCard — carte détaillée affichée au hover d'un module inventaire.
 * Wraps children dans un Tooltip avec le contenu enrichi.
 */
import React from 'react'
import { Tooltip } from '@/components/ui'
import { MODULE_CONFIG, TRAIT_CONFIG, type PlayerModule } from '@/types'

const STAT_LABEL: Record<string, string> = {
  hull: 'Coque', shield: 'Bouclier', dps: 'DPS',
  speed: 'Vitesse', cargo: 'Cargo', stealth: 'Furtivité', support_aura: 'Aura soutien',
}

const LEVEL_STYLE: Record<number, { color: string; bg: string }> = {
  1: { color: '#9ca3af', bg: 'rgba(156,163,175,0.1)' },
  2: { color: '#4ade80', bg: 'rgba(74,222,128,0.1)' },
  3: { color: '#60a5fa', bg: 'rgba(96,165,250,0.1)' },
  4: { color: '#c084fc', bg: 'rgba(192,132,252,0.1)' },
  5: { color: '#fbbf24', bg: 'rgba(251,191,36,0.1)' },
}

const BASE_BOOST_RATE: Record<number, number> = { 1: 0.08, 2: 0.14, 3: 0.22, 4: 0.32, 5: 0.44 }
const TRAIT_BOOST_MULT: Record<string, number> = {
  battle_hardened: 1.10, overclocked: 1.15, military_grade: 1.12, lightweight: 1.05,
}
const AFFINITY_CLASS: Partial<Record<string, string>> = {
  PROPELLER: 'EXPLORATION', ARMOR: 'DEFENSE', CANNON: 'ATTACK',
  EMITTER: 'SUPPORT', SHIELD: 'DEFENSE', CARGO: 'EXPLORATION',
}

export function estimateBoostRate(mod: PlayerModule, shipClass?: string): number {
  let rate = BASE_BOOST_RATE[mod.level] ?? 0
  if (mod.trait && TRAIT_BOOST_MULT[mod.trait]) rate *= TRAIT_BOOST_MULT[mod.trait]
  if (mod.bonus_trait && TRAIT_BOOST_MULT[mod.bonus_trait]) rate *= TRAIT_BOOST_MULT[mod.bonus_trait]
  if (shipClass && AFFINITY_CLASS[mod.module_type] === shipClass) rate *= 1.15
  return rate
}

export function ModuleHoverCard({ children, mod, shipClass }: {
  children: React.ReactNode
  mod: PlayerModule
  shipClass?: string
}) {
  const cfg = MODULE_CONFIG[mod.module_type]
  const stat = cfg?.stat ?? ''
  const statLabel = STAT_LABEL[stat] ?? stat
  const hasAffinity = !!shipClass && AFFINITY_CLASS[mod.module_type] === shipClass
  const boostPct = (estimateBoostRate(mod, shipClass) * 100).toFixed(1)
  const lvlStyle = LEVEL_STYLE[mod.level] ?? LEVEL_STYLE[1]
  const traits = [mod.trait, mod.bonus_trait, mod.bonus_trait_2].filter(Boolean) as string[]

  const content = (
    <div className="min-w-[210px] max-w-xs space-y-2.5 text-xs">
      {/* En-tête : icône + nom + niveau + charges */}
      <div className="flex items-start gap-2.5">
        <span className="text-xl mt-0.5">{cfg?.icon ?? '🔧'}</span>
        <div className="flex-1">
          <div className="font-semibold text-white text-sm">{cfg?.label ?? mod.module_type}</div>
          <div className="flex items-center gap-2 mt-1">
            <span
              className="px-1.5 py-0.5 rounded font-mono font-semibold text-[10px]"
              style={{ color: lvlStyle.color, background: lvlStyle.bg }}
            >
              Nv.{mod.level}
            </span>
            <span style={{ color: mod.reinstall_charges <= 1 ? '#f87171' : '#6b7280' }}>
              {mod.reinstall_charges}× charges
            </span>
          </div>
        </div>
      </div>

      {/* Stat & boost estimé */}
      <div className="border-t border-white/10 pt-2 space-y-1">
        <div className="text-gray-400">
          Améliore le <span className="text-white font-medium">{statLabel}</span>
        </div>
        <div className="text-green-400 font-mono font-semibold">
          ~+{boostPct}% {statLabel}
        </div>
        {hasAffinity ? (
          <div className="text-green-300 text-[10px]">✓ Affinité active — ×1.15 inclus</div>
        ) : (
          <div className="text-gray-600 text-[10px]">Affinité : +15% si classe correspondante</div>
        )}
      </div>

      {/* Traits */}
      {traits.length > 0 && (
        <div className="border-t border-white/10 pt-2 space-y-2">
          {traits.map(t => {
            const tc = TRAIT_CONFIG[t]
            if (!tc) return null
            return (
              <div key={t}>
                <span className="font-semibold" style={{ color: tc.color }}>{tc.label}</span>
                <p className="text-gray-400 mt-0.5 leading-relaxed">{tc.description}</p>
              </div>
            )
          })}
        </div>
      )}

      {/* Corruption */}
      {mod.is_corrupted && (
        <div className="border-t border-red-900/50 pt-2">
          <div className="font-semibold text-red-400">☠ Module corrompu</div>
          {mod.corruption_malus_stat != null && mod.corruption_malus_value != null ? (
            <p className="text-red-300 mt-0.5">
              Pénalité permanente : −{(mod.corruption_malus_value * 100).toFixed(0)}%{' '}
              {STAT_LABEL[mod.corruption_malus_stat] ?? mod.corruption_malus_stat}
            </p>
          ) : (
            <p className="text-red-300 mt-0.5">Malus sur une stat du vaisseau</p>
          )}
        </div>
      )}

      {/* Mémoire d'origine */}
      {mod.memory_ship_name && (
        <div className="border-t border-white/10 pt-2 text-purple-400">
          📜 Mémoire : <span className="font-medium">{mod.memory_ship_name}</span>
          <p className="text-gray-500 mt-0.5">Événement lors duquel ce module a été obtenu</p>
        </div>
      )}
    </div>
  )

  return (
    <Tooltip content={content} className="w-full">
      {children}
    </Tooltip>
  )
}
