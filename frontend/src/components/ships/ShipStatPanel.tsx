/**
 * ShipStatPanel — affiche les current_stats complètes d'un vaisseau.
 * Géré par le serveur — jamais calculé côté client.
 */
import React from 'react'
import { StatBar, Badge } from '@/components/ui'
import { GRADE_CONFIG, MODULE_CONFIG, type CurrentStats, type Rarity } from '@/types'
import { rarityColor, xpProgress, fmt } from '@/lib/utils'

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
            />
          )
        })}
      </div>

      {/* Modules installés */}
      {stats.modules.length > 0 && (
        <div className="panel">
          <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wide mb-3">Modules</h3>
          <div className="space-y-2">
            {stats.modules.map((mod) => {
              const modCfg = MODULE_CONFIG[mod.type]
              return (
                <div key={mod.slot} className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <span className="text-base">{modCfg?.icon ?? '🔧'}</span>
                    <span className="text-gray-300">{modCfg?.label ?? mod.type}</span>
                    <span className="text-xs text-gray-500">Nv.{mod.level}</span>
                    {mod.affinity_bonus && (
                      <span className="text-xs text-green-400 bg-green-900/30 px-1 rounded">Affinité</span>
                    )}
                  </div>
                  <span className="text-green-400 font-mono text-xs">+{mod.boost_applied.toFixed(1)}%</span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Slots disponibles */}
      <div className="panel">
        <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wide mb-3">Emplacements</h3>
        <div className="flex gap-2 flex-wrap">
          {Array.from({ length: stats.slots_total }).map((_, i) => {
            const isOccupied = stats.modules.some((m) => m.slot === i)
            const isPremium  = i >= stats.slots_total - stats.slots_premium
            const installed  = stats.modules.find((m) => m.slot === i)
            return (
              <div
                key={i}
                className={`h-10 w-10 rounded-lg border flex items-center justify-center text-sm ${
                  isOccupied
                    ? 'border-accent-blue bg-blue-900/30'
                    : isPremium
                    ? 'border-yellow-500/50 bg-yellow-900/10 border-dashed'
                    : 'border-surface-border'
                }`}
                title={isPremium ? 'Slot premium (niveaux IV–V)' : `Slot ${i}`}
              >
                {isOccupied ? MODULE_CONFIG[installed!.type]?.icon ?? '🔧' : isPremium ? '✦' : '·'}
              </div>
            )
          })}
        </div>
        {stats.slots_premium > 0 && (
          <p className="text-xs text-yellow-500 mt-2">✦ = slot premium (modules niveaux IV–V)</p>
        )}
      </div>
    </div>
  )
}
