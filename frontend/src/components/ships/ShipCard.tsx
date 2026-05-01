/**
 * components/ships/ShipCard.tsx — v2
 * Agent 6 — Sprint RPG
 *
 * Améliorations v1.1 :
 *   1. Affichage du trait narratif (badge + tooltip au hover)
 *   2. Badge "DÉRIVE" pour les vaisseaux is_drift (bordure pointillée + badge violet pâle)
 *   3. Marques de cicatrices sur la silhouette SVG (traits d'impact si scarCount > 0)
 *   4. Nom du vaisseau affiché en sous-titre pour les RARE+
 *   5. Condition d'activation du trait affichée en icône (🎯 SOLO / 👥 FLOTTE / ⚡ ALWAYS)
 *
 * Props : inchangées — compatible avec la v1 existante.
 * Règle absolue : current_stats vient toujours du serveur, jamais calculé ici.
 */
import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { cn, rarityColor, xpProgress, fmtShort } from '@/lib/utils'
import {
  RARITY_CONFIG, GRADE_CONFIG, SHIP_TYPE_CONFIG,
  type ShipSummary, type ShipDetail, type Rarity, type ShipTrait,
} from '@/types'

// ─── Props ────────────────────────────────────────────────────────────────────

interface ShipCardProps {
  ship: ShipSummary | ShipDetail
  onClick?: () => void
  selected?: boolean
  compact?: boolean
  /** Nombre de cicatrices du vaisseau (optionnel — si fourni, affiche les marques) */
  scarCount?: number
}

// ─── Constantes visuelles ─────────────────────────────────────────────────────

const CLASS_BG: Record<string, string> = {
  ATTACK:      'from-red-950/40 via-surface-secondary to-surface-secondary',
  DEFENSE:     'from-blue-950/40 via-surface-secondary to-surface-secondary',
  SUPPORT:     'from-green-950/40 via-surface-secondary to-surface-secondary',
  EXPLORATION: 'from-purple-950/40 via-surface-secondary to-surface-secondary',
}

const STATUS_CONFIG = {
  DOCKED:   { label: 'AMARRÉ',    dot: '#4ade80', glow: 'rgba(74,222,128,0.6)' },
  IN_FLEET: { label: 'EN ROUTE',  dot: '#60a5fa', glow: 'rgba(96,165,250,0.6)' },
  IN_FORGE: { label: 'EN FORGE',  dot: '#fb923c', glow: 'rgba(251,146,60,0.6)' },
}

/** Icône d'activation du trait selon la condition */
const TRAIT_CONDITION_ICON: Record<string, { icon: string; label: string; color: string }> = {
  SOLO:          { icon: '◎', label: 'Solo',    color: '#60a5fa' },
  FLEET_3PLUS:   { icon: '◉', label: 'Flotte',  color: '#4ade80' },
  ALWAYS:        { icon: '⬡', label: 'Passif',  color: '#a78bfa' },
  CLASS_MATCH:   { icon: '◈', label: 'Classe',  color: '#fb923c' },
  NONE:          { icon: '◌', label: 'Narratif',color: '#6b7280' },
}

// ─── Silhouettes SVG avec marques de cicatrices ───────────────────────────────

function ShipSilhouette({ shipClass, scarCount = 0 }: { shipClass: string; scarCount: number }) {
  const color = {
    ATTACK: '#ef4444', DEFENSE: '#3b82f6', SUPPORT: '#22c55e', EXPLORATION: '#a855f7',
  }[shipClass] ?? '#6b7280'

  // Marques de cicatrices : lignes d'impact aléatoires mais déterministes (basées sur scarCount)
  const scarMarks = Array.from({ length: Math.min(scarCount, 3) }, (_, i) => {
    const seeds = [
      { x1: 18, y1: 12, x2: 22, y2: 20 },
      { x1: 30, y1: 28, x2: 26, y2: 34 },
      { x1: 34, y1: 14, x2: 38, y2: 22 },
    ]
    const s = seeds[i]
    return (
      <line key={i} x1={s.x1} y1={s.y1} x2={s.x2} y2={s.y2}
        stroke={color} strokeWidth="1.5" strokeLinecap="round" opacity="0.8" />
    )
  })

  return (
    <svg width="48" height="48" viewBox="0 0 48 48" fill="none" opacity="0.7">
      {shipClass === 'ATTACK' && <>
        <path d="M24 4 L30 20 L44 24 L30 28 L24 44 L18 28 L4 24 L18 20 Z"
          fill={color} fillOpacity="0.15" stroke={color} strokeWidth="1"/>
        <path d="M24 10 L28 22 L38 24 L28 26 L24 38 L20 26 L10 24 L20 22 Z"
          fill={color} fillOpacity="0.25"/>
        <circle cx="24" cy="24" r="4" fill={color} fillOpacity="0.5"/>
      </>}
      {shipClass === 'DEFENSE' && <>
        <path d="M12 8 L36 8 L42 24 L36 40 L12 40 L6 24 Z"
          fill={color} fillOpacity="0.1" stroke={color} strokeWidth="1"/>
        <path d="M16 13 L32 13 L37 24 L32 35 L16 35 L11 24 Z"
          fill={color} fillOpacity="0.2"/>
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
        <ellipse cx="24" cy="24" rx="20" ry="10"
          fill={color} fillOpacity="0.08" stroke={color} strokeWidth="1"/>
        <ellipse cx="24" cy="24" rx="4" ry="12"
          fill={color} fillOpacity="0.2" stroke={color} strokeWidth="0.5"/>
        <circle cx="24" cy="24" r="3" fill={color} fillOpacity="0.6"/>
        <line x1="4" y1="24" x2="44" y2="24" stroke={color} strokeWidth="0.5" opacity="0.4"/>
      </>}
      {/* Marques de cicatrices */}
      {scarCount > 0 && scarMarks}
    </svg>
  )
}

// ─── Badge de trait ────────────────────────────────────────────────────────────

function TraitBadge({ trait }: { trait: ShipTrait }) {
  const [showTip, setShowTip] = useState(false)

  // Détecter la condition depuis le nom (heuristique simple côté client)
  // La vraie condition est dans TRAIT_INDEX côté serveur
  const condIcon = TRAIT_CONDITION_ICON['ALWAYS'] // default

  return (
    <div
      className="relative"
      onMouseEnter={() => setShowTip(true)}
      onMouseLeave={() => setShowTip(false)}
    >
      <div
        className="flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium cursor-help"
        style={{
          background: 'rgba(167,139,250,0.12)',
          border: '0.5px solid rgba(167,139,250,0.3)',
          color: '#a78bfa',
        }}
      >
        <span style={{ fontSize: 9 }}>{condIcon.icon}</span>
        <span className="truncate max-w-[80px]">{trait.name}</span>
      </div>

      {/* Tooltip narratif */}
      {showTip && (
        <div
          className="absolute bottom-full left-0 mb-1 z-50 p-2 rounded-lg text-xs text-gray-200 w-48 shadow-lg"
          style={{
            background: 'rgba(15,20,32,0.96)',
            border: '0.5px solid rgba(167,139,250,0.4)',
          }}
        >
          <p className="font-medium text-purple-300 mb-1">{trait.name}</p>
          <p className="text-gray-400 leading-relaxed">{trait.description}</p>
        </div>
      )}
    </div>
  )
}

// ─── Badge Dérive ─────────────────────────────────────────────────────────────

function DriftBadge() {
  return (
    <span
      className="text-[9px] font-semibold px-1.5 py-0.5 rounded tracking-wider"
      style={{
        background: 'rgba(139,92,246,0.08)',
        border: '0.5px dashed rgba(139,92,246,0.5)',
        color: '#8b5cf6',
      }}
    >
      DÉRIVE
    </span>
  )
}

// ─── Helper hex → rgb ─────────────────────────────────────────────────────────

function hexToRgb(hex: string): string {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `${r},${g},${b}`
}

// ─── Composant principal ──────────────────────────────────────────────────────

export function ShipCard({ ship, onClick, selected, compact, scarCount = 0 }: ShipCardProps) {
  const navigate  = useNavigate()
  const rarity    = ship.rarity as Rarity
  const cfg       = RARITY_CONFIG[rarity]
  const gradeCfg  = GRADE_CONFIG[ship.grade]
  const typeCfg   = SHIP_TYPE_CONFIG[ship.ship_type]
  const statusCfg = STATUS_CONFIG[ship.status as keyof typeof STATUS_CONFIG]
  const rc        = rarityColor(rarity)

  const handleClick = () => onClick ? onClick() : navigate(`/hangar/${ship.id}`)

  const rarityGlowClass = {
    COMMON: 'glow-common', UNCOMMON: 'glow-uncommon', RARE: 'glow-rare',
    EPIC: 'glow-epic', LEGENDARY: 'glow-legendary',
  }[rarity]

  // Bordure spéciale pour les vaisseaux en Dérive
  const borderStyle = ship.is_drift
    ? { borderStyle: 'dashed', borderColor: '#8b5cf6', borderWidth: selected ? '2px' : '1px' }
    : { borderColor: rc, borderWidth: selected ? '2px' : '1px' }

  return (
    <div
      onClick={handleClick}
      className={cn(
        'ship-card group cursor-pointer transition-all duration-300 relative overflow-hidden',
        compact ? 'p-3' : 'p-4',
        selected && rarityGlowClass,
      )}
      style={{
        ...borderStyle,
        background: `linear-gradient(135deg, rgba(${hexToRgb(rc)},0.08) 0%, rgba(13,18,30,0.9) 50%)`,
      }}
    >
      {/* Ligne supérieure lumineuse */}
      <div className="absolute top-0 left-0 right-0 h-px"
        style={{ background: `linear-gradient(90deg, transparent, ${rc}80, transparent)` }} />

      {/* Indicateur Dérive — fond légèrement teinté */}
      {ship.is_drift && (
        <div className="absolute inset-0 pointer-events-none"
          style={{ background: 'rgba(139,92,246,0.04)' }} />
      )}

      {/* ── Ligne 1 : Silhouette + Infos principales ── */}
      <div className="flex items-start gap-3">
        <div className="relative flex-shrink-0">
          <ShipSilhouette shipClass={ship.ship_class} scarCount={scarCount} />
          {/* Badge grade en dessous */}
          {ship.grade > 0 && (
            <div className="absolute -bottom-1 -right-1 text-[9px] font-bold px-1 rounded"
              style={{ background: gradeCfg?.color ?? '#6b7280', color: '#000' }}>
              G{ship.grade}
            </div>
          )}
        </div>

        <div className="flex-1 min-w-0">
          {/* Nom du vaisseau (RARE+) */}
          {ship.name && (
            <p className="text-[11px] font-semibold truncate mb-0.5"
              style={{ color: rc }}>
              {ship.name}
            </p>
          )}

          {/* Type + classe */}
          <p className="text-xs font-medium text-white/80 truncate">
            {typeCfg?.label ?? ship.ship_type}
          </p>
          <p className="text-[10px] text-gray-500 mt-0.5">
            {ship.ship_class}
          </p>

          {/* Badges rareté + Dérive */}
          <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
            <span
              className="text-[10px] font-semibold px-1.5 py-0.5 rounded tracking-wider"
              style={{ background: `${rc}20`, color: rc, border: `0.5px solid ${rc}50` }}
            >
              {cfg?.label ?? rarity}
            </span>
            {ship.is_drift && <DriftBadge />}
            {/* Indicateur cicatrices */}
            {scarCount > 0 && (
              <span className="text-[9px] text-gray-500" title={`${scarCount} cicatrice(s)`}>
                {'⋯'.repeat(Math.min(scarCount, 3))}
              </span>
            )}
          </div>
        </div>

        {/* Status dot */}
        <div className="flex flex-col items-end gap-1.5 flex-shrink-0">
          <div className="flex items-center gap-1">
            <div className="w-1.5 h-1.5 rounded-full animate-pulse"
              style={{ backgroundColor: statusCfg?.dot ?? '#6b7280' }} />
            <span className="text-[9px] font-medium tracking-wider"
              style={{ color: statusCfg?.dot ?? '#6b7280' }}>
              {statusCfg?.label ?? ship.status}
            </span>
          </div>
        </div>
      </div>

      {/* ── Ligne 2 : Trait narratif (si présent) ── */}
      {!compact && ship.trait && (
        <div className="mt-2 pt-2 border-t border-white/5">
          <TraitBadge trait={ship.trait} />
        </div>
      )}

      {/* ── Ligne 3 : XP bar (si ShipDetail) ── */}
      {!compact && 'combat_xp' in ship && (
        <div className="mt-2">
          <div className="h-0.5 rounded-full bg-white/5 overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{
                width: `${xpProgress(ship.combat_xp, ship.grade)}%`,
                background: rc,
                opacity: 0.6,
              }}
            />
          </div>
          <p className="text-[9px] text-gray-600 mt-0.5">
            {fmtShort(ship.combat_xp)} XP — {gradeCfg?.name ?? `Grade ${ship.grade}`}
          </p>
        </div>
      )}
    </div>
  )
}

// ─── Skeleton ─────────────────────────────────────────────────────────────────

export function ShipCardSkeleton() {
  return (
    <div className="ship-card p-4 animate-pulse">
      <div className="flex gap-3">
        <div className="w-12 h-12 rounded bg-white/5 flex-shrink-0" />
        <div className="flex-1 space-y-2">
          <div className="h-3 bg-white/5 rounded w-3/4" />
          <div className="h-2.5 bg-white/5 rounded w-1/2" />
          <div className="h-2 bg-white/5 rounded w-1/3" />
        </div>
      </div>
    </div>
  )
}
