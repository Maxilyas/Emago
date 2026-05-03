/**
 * ShipStatPanel — affiche les current_stats complètes d'un vaisseau.
 * Géré par le serveur — jamais calculé côté client.
 */
import React from 'react'
import { StatBar, Badge, TraitBadge } from '@/components/ui'
import { InstalledModuleHoverCard } from '@/components/ships/ModuleHoverCard'
import {
  GRADE_CONFIG, MODULE_CONFIG, DOCTRINE_CONFIG, RESONANCE_CONFIG, TRAIT_CONFIG,
  type CurrentStats, type Rarity,
} from '@/types'
import { rarityColor, xpProgress, fmt } from '@/lib/utils'

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

interface Props {
  stats: CurrentStats
  baseStats: Record<string, number>
  rarity: Rarity
  combatXp: number
  grade: number
}

const STAT_MAX: Record<string, number> = {
  hull: 10000, shield: 5000, dps: 3000, speed: 200,
  cargo: 50000, stealth: 100, support_aura: 50,
}

const STAT_LABELS: Record<string, { label: string; icon: string; color: string }> = {
  hull:         { label: 'Coque',        icon: '❤️',  color: '#ef4444' },
  shield:       { label: 'Bouclier',     icon: '🛡️',  color: '#3b82f6' },
  dps:          { label: 'DPS',          icon: '⚔️',  color: '#f97316' },
  speed:        { label: 'Vitesse',      icon: '⚡',  color: '#a78bfa' },
  cargo:        { label: 'Cargo',        icon: '📦',  color: '#6b7280' },
  stealth:      { label: 'Furtivité',    icon: '👁️',  color: '#8b5cf6' },
  support_aura: { label: 'Aura soutien', icon: '💫',  color: '#22d3ee' },
}

export function ShipStatPanel({ stats, baseStats, rarity, combatXp, grade }: Props) {
  const color = rarityColor(rarity)
  const gradeCfg = GRADE_CONFIG[grade]
  const nextGrade = GRADE_CONFIG[grade + 1]

  return (
    <div className="space-y-4">
      {/* Grade + XP */}
      <div className="panel">
        <div className="flex items-center justify-between mb-2">
          <div>
            <span className="text-yellow-400 mr-1">{'★'.repeat(grade)}{'☆'.repeat(5 - grade)}</span>
            <span className="font-semibold">{gradeCfg?.name ?? 'Spectre'}</span>
          </div>
          <span className="text-xs text-gray-400 font-mono">{fmt(combatXp)} XP</span>
        </div>
        {nextGrade && (
          <div className="space-y-1">
            <div className="flex justify-between text-xs text-gray-500">
              <span>Prochain grade : {nextGrade.name}</span>
              <span>{fmt(nextGrade.xp - combatXp)} XP restants</span>
            </div>
            <div className="h-1.5 bg-surface-border rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{ width: `${xpProgress(combatXp, grade)}%`, backgroundColor: color }}
              />
            </div>
          </div>
        )}
        {stats.grade_bonus_pct > 0 && (
          <p className="text-xs text-green-400 mt-2">
            Bonus grade : +{stats.grade_bonus_pct}% toutes stats
          </p>
        )}
        {stats.shield_regen_per_round > 0 && (
          <p className="text-xs text-blue-400">Régén. bouclier : {stats.shield_regen_per_round * 100}%/round</p>
        )}
      </div>

      {/* Stats principales */}
      <div className="panel space-y-3">
        <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">Stats effectives</h3>
        {Object.entries(STAT_LABELS).map(([key, cfg]) => {
          const val = stats[key as keyof CurrentStats] as number
          const base = baseStats[key] as number | undefined
          const isCapped = stats.cap_reached.includes(key)
          return (
            <StatBar
              key={key}
              label={`${cfg.icon} ${cfg.label}`}
              value={val}
              max={STAT_MAX[key] ?? 100}
              color={cfg.color}
              capped={isCapped}
              base={base !== undefined && base > 0 ? Math.round(base) : undefined}
            />
          )
        })}
      </div>

      {/* Doctrines — toujours visible */}
      {(() => {
        const typeCounts = stats.modules.reduce((acc, m) => {
          acc[m.type] = (acc[m.type] ?? 0) + 1
          return acc
        }, {} as Record<string, number>)

        return (
          <div className="panel">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Doctrines</h3>
              <span className="text-[10px] text-gray-600">4 modules du même type = doctrine active</span>
            </div>
            <div className="space-y-2.5">
              {Object.entries(DOCTRINE_CONFIG).map(([key, doc]) => {
                const count = typeCounts[doc.module_type] ?? 0
                const isActive = stats.doctrine === key && stats.doctrine_active
                const modCfg = MODULE_CONFIG[doc.module_type]
                return (
                  <div
                    key={key}
                    className={`rounded-lg p-2.5 border transition-all ${
                      isActive ? 'border' : 'border-surface-border bg-surface-tertiary/30'
                    }`}
                    style={isActive ? {
                      borderColor: `${doc.color}50`,
                      background: `${doc.color}08`,
                      boxShadow: `0 0 12px ${doc.color}15`,
                    } : undefined}
                  >
                    {/* Titre + progress */}
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className="text-sm">{doc.icon}</span>
                      <span className="text-xs font-semibold" style={{ color: isActive ? doc.color : '#9ca3af' }}>
                        {doc.label}
                      </span>
                      <span className="text-[10px] text-gray-600">({modCfg?.label})</span>
                      {isActive && (
                        <span className="ml-auto text-[10px] font-bold text-green-400 bg-green-900/20 px-1.5 py-0.5 rounded">✓ ACTIVE</span>
                      )}
                    </div>
                    {/* Barre de progression */}
                    <div className="flex items-center gap-2 mb-1.5">
                      <div className="flex gap-0.5">
                        {Array.from({ length: 4 }).map((_, i) => (
                          <div
                            key={i}
                            className="w-4 h-1.5 rounded-sm transition-all"
                            style={{ backgroundColor: i < count ? doc.color : '#1f2937' }}
                          />
                        ))}
                      </div>
                      <span className="text-[10px] font-mono" style={{ color: count >= 4 ? doc.color : '#6b7280' }}>
                        {count}/4
                      </span>
                    </div>
                    {/* Effets */}
                    <div className="flex flex-wrap gap-1.5">
                      {doc.effects.map((eff, i) => (
                        <span
                          key={i}
                          className={`text-[10px] px-1.5 py-0.5 rounded ${
                            eff.positive
                              ? 'text-green-300 bg-green-900/20'
                              : 'text-red-300 bg-red-900/20'
                          }`}
                        >
                          {eff.text}
                        </span>
                      ))}
                    </div>
                    {/* Flags combat actifs si doctrine active */}
                    {isActive && (
                      <div className="flex flex-wrap gap-1.5 mt-1">
                        {stats.evasion_chance > 0 && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-purple-900/20 text-purple-300">
                            👻 {(stats.evasion_chance * 100).toFixed(0)}% évasion
                          </span>
                        )}
                        {stats.damage_reduction > 0 && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-900/20 text-blue-300">
                            🛡 {(stats.damage_reduction * 100).toFixed(0)}% réd. dégâts
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        )
      })()}

      {/* Résonances actives */}
      {stats.resonances && stats.resonances.length > 0 && (
        <div className="panel">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2">Résonances actives</h3>
          <div className="space-y-1.5">
            {stats.resonances.map((resId) => {
              const res = RESONANCE_CONFIG[resId]
              if (!res) return null
              return (
                <div key={resId} className="flex items-center gap-2 text-xs">
                  <span>{res.icon}</span>
                  <span className="text-amber-300 font-medium">{res.label}</span>
                  <span className="text-gray-500">— {res.description}</span>
                </div>
              )
            })}
            {stats.riposte_chance > 0 && (
              <div className="flex items-center gap-2 text-xs mt-1">
                <span>⚡</span>
                <span className="text-yellow-300">{(stats.riposte_chance * 100).toFixed(0)}% contre-tir actif</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Emplacements — grille unifiée avec hover card */}
      <div className="panel">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wide">Emplacements</h3>
          <span className="text-xs text-gray-600">
            {stats.modules.length}/{stats.slots_total} occupés
          </span>
        </div>
        <div className="grid grid-cols-2 gap-2">
          {Array.from({ length: stats.slots_total }).map((_, i) => {
            const mod = stats.modules.find((m) => m.slot === i)
            const isPremium = i >= stats.slots_total - stats.slots_premium
            const cfg = mod ? MODULE_CONFIG[mod.type] : null
            const stat = mod ? MODULE_CONFIG[mod.type]?.stat : null
            const traitCfg = mod?.trait ? TRAIT_CONFIG[mod.trait] : null

            if (mod && cfg) {
              const allTraits = [mod.trait, mod.bonus_trait, mod.bonus_trait_2].filter(Boolean) as string[]
              return (
                <InstalledModuleHoverCard key={i} mod={mod}>
                  <div className={`p-2.5 rounded-lg border cursor-default ${
                    isPremium
                      ? 'border-yellow-500/30 bg-yellow-900/10'
                      : 'border-accent-blue/40 bg-blue-900/10'
                  }`}>
                    {/* Header slot + level */}
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-[10px] text-gray-500">
                        #{i + 1}{isPremium && <span className="text-yellow-500"> ✦</span>}
                      </span>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded font-mono font-semibold ${LEVEL_COLORS[mod.level]}`}>
                        Nv.{mod.level}
                      </span>
                    </div>
                    {/* Module icon + name */}
                    <div className="flex items-center gap-1.5 mb-1">
                      <span className="text-base leading-none">{cfg.icon}</span>
                      <span className="text-xs font-medium text-gray-200 truncate">{cfg.label}</span>
                    </div>
                    {/* Boost */}
                    <div className="text-[10px] text-green-400 font-mono mb-1.5">
                      +{mod.boost_applied.toFixed(1)}% {stat ? STAT_LABEL[stat] : ''}
                      {mod.affinity_bonus && (
                        <span className="text-green-600 ml-1">×aff.</span>
                      )}
                    </div>
                    {/* Traits */}
                    {allTraits.length > 0 && (
                      <div className="flex flex-wrap gap-1 mb-1">
                        {allTraits.map(t => {
                          const tc = TRAIT_CONFIG[t]
                          if (!tc) return null
                          return (
                            <span
                              key={t}
                              className="text-[10px] px-1 py-0.5 rounded border"
                              style={{ color: tc.color, background: `${tc.color}15`, borderColor: `${tc.color}30` }}
                            >
                              {tc.label}
                            </span>
                          )
                        })}
                      </div>
                    )}
                    {/* Corruption malus — visible directement */}
                    {mod.is_corrupted && (
                      <div className="flex items-center gap-1 mt-0.5">
                        <span className="text-[10px] text-red-400 font-medium">☠</span>
                        {mod.corruption_malus_stat && mod.corruption_malus_value != null ? (
                          <span className="text-[10px] text-red-400 font-mono">
                            −{(mod.corruption_malus_value * 100).toFixed(0)}%{' '}
                            {STAT_LABEL[mod.corruption_malus_stat] ?? mod.corruption_malus_stat}
                          </span>
                        ) : (
                          <span className="text-[10px] text-red-500">corrompu</span>
                        )}
                      </div>
                    )}
                    {/* Charges faibles */}
                    {mod.reinstall_charges !== null && mod.reinstall_charges !== undefined && mod.reinstall_charges <= 1 && (
                      <div className="text-[10px] text-red-400 font-mono mt-0.5">{mod.reinstall_charges}× charge restante</div>
                    )}
                  </div>
                </InstalledModuleHoverCard>
              )
            }

            return (
              <div
                key={i}
                className={`p-2.5 rounded-lg border ${
                  isPremium
                    ? 'border-yellow-500/20 border-dashed bg-yellow-900/5'
                    : 'border-surface-border/40'
                }`}
              >
                <div className="text-[10px] text-gray-600 mb-1.5">
                  #{i + 1}{isPremium && <span className="text-yellow-700"> ✦</span>}
                </div>
                <p className="text-xs text-gray-600 italic">Vide</p>
                <p className="text-[10px] text-gray-700 mt-0.5">{isPremium ? 'Niv. IV–V' : 'Niv. I–III'}</p>
              </div>
            )
          })}
        </div>
        {stats.slots_premium > 0 && (
          <p className="text-[10px] text-yellow-700 mt-2">✦ Slot premium — modules niveaux IV–V</p>
        )}
      </div>
    </div>
  )
}
