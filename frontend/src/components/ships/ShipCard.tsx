import React from 'react'
import { useNavigate } from 'react-router-dom'
import { cn, rarityColor, xpProgress, fmtShort } from '@/lib/utils'
import { RARITY_CONFIG, GRADE_CONFIG, SHIP_TYPE_CONFIG, type ShipSummary, type ShipDetail, type Rarity } from '@/types'

interface ShipCardProps {
  ship: ShipSummary | ShipDetail
  onClick?: () => void
  selected?: boolean
  compact?: boolean
}

// Dégradés de fond par classe
const CLASS_BG: Record<string, string> = {
  ATTACK:      'from-red-950/40 via-surface-secondary to-surface-secondary',
  DEFENSE:     'from-blue-950/40 via-surface-secondary to-surface-secondary',
  SUPPORT:     'from-green-950/40 via-surface-secondary to-surface-secondary',
  EXPLORATION: 'from-purple-950/40 via-surface-secondary to-surface-secondary',
}
const CLASS_ACCENT: Record<string, string> = {
  ATTACK:      'rgba(239,68,68,0.7)',
  DEFENSE:     'rgba(59,130,246,0.7)',
  SUPPORT:     'rgba(34,197,94,0.7)',
  EXPLORATION: 'rgba(168,85,247,0.7)',
}
const STATUS_CONFIG = {
  DOCKED:   { label: 'AMARRÉ',    dot: '#4ade80', glow: 'rgba(74,222,128,0.6)' },
  IN_FLEET: { label: 'EN ROUTE',  dot: '#60a5fa', glow: 'rgba(96,165,250,0.6)' },
  IN_FORGE: { label: 'EN FORGE',  dot: '#fb923c', glow: 'rgba(251,146,60,0.6)' },
}

function ShipSilhouette({ shipClass }: { shipClass: string }) {
  const color = { ATTACK: '#ef4444', DEFENSE: '#3b82f6', SUPPORT: '#22c55e', EXPLORATION: '#a855f7' }[shipClass] ?? '#6b7280'
  return (
    <svg width="48" height="48" viewBox="0 0 48 48" fill="none" opacity="0.7">
      {shipClass === 'ATTACK' && <>
        <path d="M24 4 L30 20 L44 24 L30 28 L24 44 L18 28 L4 24 L18 20 Z" fill={color} fillOpacity="0.15" stroke={color} strokeWidth="1"/>
        <path d="M24 10 L28 22 L38 24 L28 26 L24 38 L20 26 L10 24 L20 22 Z" fill={color} fillOpacity="0.25"/>
        <circle cx="24" cy="24" r="4" fill={color} fillOpacity="0.5"/>
      </>}
      {shipClass === 'DEFENSE' && <>
        <path d="M12 8 L36 8 L42 24 L36 40 L12 40 L6 24 Z" fill={color} fillOpacity="0.1" stroke={color} strokeWidth="1"/>
        <path d="M16 13 L32 13 L37 24 L32 35 L16 35 L11 24 Z" fill={color} fillOpacity="0.2"/>
        <rect x="20" y="20" width="8" height="8" fill={color} fillOpacity="0.5" rx="1"/>
      </>}
      {shipClass === 'SUPPORT' && <>
        <circle cx="24" cy="24" r="18" fill={color} fillOpacity="0.08" stroke={color} strokeWidth="1"/>
        <circle cx="24" cy="24" r="12" fill={color} fillOpacity="0.12" stroke={color} strokeWidth="0.5"/>
        <path d="M24 12 L28 20 L24 18 L20 20 Z" fill={color} fillOpacity="0.5"/>
        <path d="M24 36 L28 28 L24 30 L20 28 Z" fill={color} fillOpacity="0.5"/>
        <path d="M12 24 L20 20 L18 24 L20 28 Z" fill={color} fillOpacity="0.5"/>
        <path d="M36 24 L28 20 L30 24 L28 28 Z" fill={color} fillOpacity="0.5"/>
      </>}
      {shipClass === 'EXPLORATION' && <>
        <ellipse cx="24" cy="24" rx="20" ry="10" fill={color} fillOpacity="0.08" stroke={color} strokeWidth="1"/>
        <ellipse cx="24" cy="24" rx="4" ry="12" fill={color} fillOpacity="0.2" stroke={color} strokeWidth="0.5"/>
        <circle cx="24" cy="24" r="3" fill={color} fillOpacity="0.6"/>
        <line x1="4" y1="24" x2="44" y2="24" stroke={color} strokeWidth="0.5" opacity="0.4"/>
      </>}
    </svg>
  )
}

export function ShipCard({ ship, onClick, selected, compact }: ShipCardProps) {
  const navigate  = useNavigate()
  const rarity    = ship.rarity as Rarity
  const cfg       = RARITY_CONFIG[rarity]
  const gradeCfg  = GRADE_CONFIG[ship.grade]
  const typeCfg   = SHIP_TYPE_CONFIG[ship.ship_type]
  const statusCfg = STATUS_CONFIG[ship.status as keyof typeof STATUS_CONFIG]
  const isDetail  = 'current_stats' in ship
  const rc        = rarityColor(rarity)
  const classBg   = CLASS_BG[ship.ship_class] ?? CLASS_BG.ATTACK

  const handleClick = () => onClick ? onClick() : navigate(`/hangar/${ship.id}`)

  const rarityGlowClass = {
    COMMON: 'glow-common', UNCOMMON: 'glow-uncommon', RARE: 'glow-rare',
    EPIC: 'glow-epic', LEGENDARY: 'glow-legendary',
  }[rarity]

  return (
    <div
      onClick={handleClick}
      className={cn(
        'ship-card group cursor-pointer transition-all duration-300',
        compact ? 'p-3' : 'p-4',
        selected && rarityGlowClass,
      )}
      style={{
        borderColor: rc,
        borderWidth: selected ? '2px' : '1px',
        background: `linear-gradient(135deg, rgba(${hexToRgb(rc)},0.08) 0%, rgba(13,18,30,0.9) 50%)`,
      }}
    >
      {/* Ligne supérieure lumineuse */}
      <div className="absolute top-0 left-0 right-0 h-px"
        style={{ background: `linear-gradient(90deg, transparent, ${rc}80, transparent)` }} />

      {/* Fond silhouette */}
      <div className="absolute right-2 top-1/2 -translate-y-1/2 opacity-20 group-hover:opacity-30 transition-opacity">
        <ShipSilhouette shipClass={ship.ship_class} />
      </div>

      {/* Contenu */}
      <div className="relative">
        {/* Header */}
        <div className="flex items-start justify-between gap-2 mb-2.5">
          <div>
            <p className="font-semibold text-white text-sm leading-tight">
              {typeCfg?.label ?? ship.ship_type}
            </p>
            <p className="text-[10px] mt-0.5 font-medium tracking-wider uppercase"
              style={{ color: CLASS_ACCENT[ship.ship_class]?.replace('0.7', '1') ?? '#9ca3af' }}>
              {ship.ship_class}
            </p>
          </div>
          <span
            className="badge-rarity text-[10px] px-2 py-0.5 rounded-full shrink-0"
            style={{
              color: rc,
              background: `rgba(${hexToRgb(rc)},0.12)`,
              border: `1px solid rgba(${hexToRgb(rc)},0.3)`,
            }}
          >
            {cfg.label}
          </span>
        </div>

        {/* Grade */}
        <div className="flex items-center justify-between mb-2.5">
          <div className="flex items-center gap-1.5">
            <div className="flex gap-0.5">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className={cn('w-2 h-2 rounded-sm transition-all', i < ship.grade ? '' : 'opacity-20')}
                  style={i < ship.grade ? { background: '#eab308', boxShadow: '0 0 4px rgba(234,179,8,0.6)' } : { background: '#374151' }} />
              ))}
            </div>
            <span className="text-[10px] text-gray-500 font-display">{gradeCfg?.name ?? 'G0'}</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="h-1.5 w-1.5 rounded-full"
              style={{ background: statusCfg?.dot ?? '#6b7280', boxShadow: `0 0 4px ${statusCfg?.glow ?? 'transparent'}` }} />
            <span className="text-[10px] tracking-wider font-display"
              style={{ color: statusCfg?.dot ?? '#6b7280' }}>
              {statusCfg?.label}
            </span>
          </div>
        </div>

        {/* XP bar */}
        {ship.grade < 5 && (
          <div className="mb-3">
            <div className="h-0.5 rounded-full overflow-hidden bg-gray-800">
              <div
                className="h-full rounded-full transition-all duration-700"
                style={{
                  width: `${'combat_xp' in ship ? xpProgress(ship.combat_xp, ship.grade) : 0}%`,
                  background: `linear-gradient(90deg, ${rc}80, ${rc})`,
                }}
              />
            </div>
          </div>
        )}

        {/* Stats rapides sur le détail */}
        {!compact && isDetail && (
          <div className="grid grid-cols-3 gap-2 pt-2.5 border-t border-border/40">
            {[
              { label: 'Coque',    value: (ship as ShipDetail).current_stats.hull,  color: '#ef4444' },
              { label: 'DPS',      value: (ship as ShipDetail).current_stats.dps,   color: '#f97316' },
              { label: 'Vitesse',  value: (ship as ShipDetail).current_stats.speed, color: '#a78bfa' },
            ].map(s => (
              <div key={s.label} className="text-center">
                <p className="text-[9px] text-gray-600 uppercase tracking-wider mb-0.5">{s.label}</p>
                <p className="text-xs font-mono font-semibold" style={{ color: s.color }}>
                  {fmtShort(s.value)}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function hexToRgb(hex: string): string {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `${r},${g},${b}`
}

export function ShipCardSkeleton() {
  return (
    <div className="ship-card p-4 space-y-3 border-border">
      <div className="flex justify-between">
        <div className="space-y-1.5">
          <div className="h-3.5 w-24 rounded shimmer bg-surface-elevated" />
          <div className="h-2.5 w-16 rounded shimmer bg-surface-elevated" />
        </div>
        <div className="h-5 w-16 rounded-full shimmer bg-surface-elevated" />
      </div>
      <div className="h-0.5 w-full rounded shimmer bg-surface-elevated" />
      <div className="grid grid-cols-3 gap-2">
        {[...Array(3)].map((_, i) => <div key={i} className="h-8 rounded shimmer bg-surface-elevated" />)}
      </div>
    </div>
  )
}
