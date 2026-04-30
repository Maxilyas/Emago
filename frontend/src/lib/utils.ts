import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { formatDistanceToNow, format } from 'date-fns'
import { fr } from 'date-fns/locale'
import { RARITY_CONFIG, type Rarity } from '@/types'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Format nombre avec séparateur de milliers */
export function fmt(n: number, decimals = 0): string {
  return n.toLocaleString('fr-FR', { maximumFractionDigits: decimals })
}

/** Formate en K/M si grand */
export function fmtShort(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000)     return `${(n / 1_000).toFixed(1)}k`
  return `${Math.round(n)}`
}

/** Countdown HH:MM:SS depuis nb de secondes */
export function fmtCountdown(seconds: number): string {
  if (seconds <= 0) return '00:00:00'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  return [h, m, s].map(v => String(v).padStart(2, '0')).join(':')
}

/** Retourne la couleur CSS d'une rareté */
export function rarityColor(rarity: Rarity): string {
  return RARITY_CONFIG[rarity].color
}

/** Retourne les classes Tailwind pour le texte/bordure d'une rareté */
export function rarityTw(rarity: Rarity): string {
  return RARITY_CONFIG[rarity].tw
}

/** Retourne la couleur de border inline pour box-shadow */
export function rarityGlow(rarity: Rarity): string {
  const color = RARITY_CONFIG[rarity].color
  if (rarity === 'LEGENDARY') return `0 0 12px ${color}66, 0 0 24px ${color}33`
  return `0 0 8px ${color}44`
}

/** Date relative */
export function timeAgo(dateStr: string): string {
  return formatDistanceToNow(new Date(dateStr), { addSuffix: true, locale: fr })
}

/** Date formattée */
export function fmtDate(dateStr: string): string {
  return format(new Date(dateStr), 'dd/MM/yyyy HH:mm', { locale: fr })
}

/** Calcule le % XP pour la prochaine progression de grade */
export function xpProgress(currentXp: number, currentGrade: number): number {
  const thresholds = [0, 500, 2000, 6000, 15000, 40000]
  if (currentGrade >= 5) return 100
  const prev = thresholds[currentGrade]
  const next = thresholds[currentGrade + 1]
  return Math.min(100, ((currentXp - prev) / (next - prev)) * 100)
}

/** Clamp une valeur entre min et max */
export function clamp(val: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, val))
}
