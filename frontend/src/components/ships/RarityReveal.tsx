/**
 * components/ships/RarityReveal.tsx
 * Agent 6 — Sprint UX
 *
 * Overlay de révélation de rareté après construction d'un vaisseau.
 * Remplace le simple toast — crée un moment émotionnel fort.
 *
 * Usage dans BuildModal.onSuccess :
 *   setReveal(res)  →  affiche cet overlay
 *   onDismiss()     →  ferme + appelle onBuilt()
 */
import React, { useEffect, useState } from 'react'
import { RARITY_CONFIG, SHIP_TYPE_CONFIG, type Rarity } from '@/types'

interface RevealData {
  rarity: string
  ship_class: string
  ship_type: string
  base_stats: {
    hull: number
    shield: number
    dps: number
    speed: number
    cargo: number
    stealth: number
  }
  slots_total: number
  slots_premium: number
  pedigree_applied?: boolean
}

interface Props {
  data: RevealData | null
  onDismiss: () => void
}

const RARITY_GLOW: Record<string, string> = {
  COMMON:    '0,0,0',
  UNCOMMON:  '76,175,80',
  RARE:      '33,150,243',
  EPIC:      '156,39,176',
  LEGENDARY: '255,215,0',
}

const RARITY_ANIM_DELAY: Record<string, number> = {
  COMMON: 400, UNCOMMON: 600, RARE: 900, EPIC: 1200, LEGENDARY: 1800,
}

export function RarityReveal({ data, onDismiss }: Props) {
  const [phase, setPhase] = useState<'flash' | 'reveal' | 'stats'>('flash')

  useEffect(() => {
    if (!data) return
    setPhase('flash')
    const t1 = setTimeout(() => setPhase('reveal'), RARITY_ANIM_DELAY[data.rarity] ?? 600)
    const t2 = setTimeout(() => setPhase('stats'), (RARITY_ANIM_DELAY[data.rarity] ?? 600) + 600)
    return () => { clearTimeout(t1); clearTimeout(t2) }
  }, [data])

  if (!data) return null

  const rarity   = data.rarity as Rarity
  const cfg      = RARITY_CONFIG[rarity]
  const typeCfg  = SHIP_TYPE_CONFIG[data.ship_type]
  const rgb      = RARITY_GLOW[rarity] ?? '107,114,128'

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center"
      style={{ background: 'rgba(0,0,0,0.92)', backdropFilter: 'blur(16px)' }}
      onClick={phase === 'stats' ? onDismiss : undefined}
    >
      {/* Flash initial */}
      {phase === 'flash' && (
        <div
          className="w-32 h-32 rounded-full animate-ping"
          style={{ background: `rgba(${rgb},0.3)`, boxShadow: `0 0 60px rgba(${rgb},0.6)` }}
        />
      )}

      {/* Révélation rareté */}
      {(phase === 'reveal' || phase === 'stats') && (
        <div className="text-center space-y-6 animate-fade-in px-6 max-w-sm w-full">

          {/* Glow + badge rareté */}
          <div className="relative flex items-center justify-center">
            <div
              className="absolute w-48 h-48 rounded-full opacity-30 animate-pulse"
              style={{ background: `radial-gradient(circle, rgba(${rgb},0.6), transparent)` }}
            />
            <div className="relative">
              <div
                className="text-6xl mb-2 select-none"
                style={{ filter: `drop-shadow(0 0 20px rgba(${rgb},0.8))` }}
              >
                {typeCfg?.icon ?? '🚀'}
              </div>
              <div
                className="px-4 py-1.5 rounded-full font-bold text-sm tracking-widest uppercase"
                style={{
                  background: `rgba(${rgb},0.15)`,
                  border: `2px solid rgba(${rgb},0.6)`,
                  color: cfg.color,
                  boxShadow: `0 0 20px rgba(${rgb},0.4)`,
                }}
              >
                {cfg.label}
              </div>
            </div>
          </div>

          {/* Nom du vaisseau */}
          <div>
            <p className="text-2xl font-bold text-white">{typeCfg?.label ?? data.ship_type}</p>
            <p className="text-sm mt-1" style={{ color: cfg.color }}>{data.ship_class}</p>
            {data.pedigree_applied && (
              <p className="text-xs text-yellow-400 mt-1">👑 Pedigree appliqué — +5% sur la meilleure stat</p>
            )}
          </div>

          {/* Stats (phase finale) */}
          {phase === 'stats' && (
            <div
              className="grid grid-cols-3 gap-2 text-center animate-fade-in"
              style={{ opacity: phase === 'stats' ? 1 : 0, transition: 'opacity 0.5s' }}
            >
              {[
                { label: 'Coque',    value: data.base_stats.hull,   icon: '❤️' },
                { label: 'Bouclier', value: data.base_stats.shield, icon: '🛡️' },
                { label: 'DPS',      value: data.base_stats.dps,    icon: '⚔️' },
                { label: 'Vitesse',  value: Math.round(data.base_stats.speed), icon: '⚡' },
                { label: 'Cargo',    value: data.base_stats.cargo,  icon: '📦' },
                { label: 'Slots',    value: `${data.slots_total} (${data.slots_premium}★)`, icon: '🔧' },
              ].map(s => (
                <div
                  key={s.label}
                  className="rounded-xl p-2"
                  style={{ background: `rgba(${rgb},0.08)`, border: `1px solid rgba(${rgb},0.2)` }}
                >
                  <p className="text-base">{s.icon}</p>
                  <p className="text-sm font-bold text-white">{s.value}</p>
                  <p className="text-[10px] text-gray-500 uppercase tracking-wide">{s.label}</p>
                </div>
              ))}
            </div>
          )}

          {/* CTA */}
          {phase === 'stats' && (
            <button
              onClick={onDismiss}
              className="w-full py-3 rounded-xl font-bold text-white transition-all"
              style={{
                background: `rgba(${rgb},0.2)`,
                border: `1px solid rgba(${rgb},0.4)`,
                boxShadow: `0 0 15px rgba(${rgb},0.2)`,
              }}
            >
              Voir dans le hangar →
            </button>
          )}
        </div>
      )}
    </div>
  )
}
