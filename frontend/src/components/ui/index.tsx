import React from 'react'
import { cn } from '@/lib/utils'

// ─── LoadingSpinner ───────────────────────────────────────────────────────────
export function LoadingSpinner({ size = 'md', className }: { size?: 'sm' | 'md' | 'lg'; className?: string }) {
  const s = { sm: 'h-4 w-4', md: 'h-8 w-8', lg: 'h-12 w-12' }[size]
  return (
    <div className={cn('animate-spin rounded-full border-2 border-surface-border border-t-accent-blue', s, className)} />
  )
}

// ─── Skeleton ─────────────────────────────────────────────────────────────────
export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('shimmer bg-surface-tertiary rounded-lg', className)} />
}

// ─── Badge ────────────────────────────────────────────────────────────────────
interface BadgeProps { children: React.ReactNode; variant?: 'default' | 'success' | 'warning' | 'danger'; className?: string }
export function Badge({ children, variant = 'default', className }: BadgeProps) {
  const vars = {
    default: 'bg-surface-elevated text-gray-300',
    success: 'bg-green-900/50 text-green-400',
    warning: 'bg-yellow-900/50 text-yellow-400',
    danger:  'bg-red-900/50 text-red-400',
  }
  return <span className={cn('rarity-badge', vars[variant], className)}>{children}</span>
}

// ─── StatBar ──────────────────────────────────────────────────────────────────
interface StatBarProps { label: string; value: number; max: number; color?: string; capped?: boolean }
export function StatBar({ label, value, max, color = '#2d7dd2', capped = false }: StatBarProps) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-gray-400">
        <span className={cn(capped && 'text-orange-400 flex items-center gap-1')}>
          {label}{capped && <span title="Plafond +150% atteint">🔒</span>}
        </span>
        <span className="text-white font-mono">{value.toLocaleString('fr-FR')}</span>
      </div>
      <div className="stat-bar">
        <div
          className="stat-bar-fill"
          style={{ width: `${pct}%`, backgroundColor: capped ? '#f97316' : color }}
        />
      </div>
    </div>
  )
}

// ─── Modal ────────────────────────────────────────────────────────────────────
interface ModalProps { open: boolean; onClose: () => void; title?: string; children: React.ReactNode; size?: 'sm' | 'md' | 'lg' }
export function Modal({ open, onClose, title, children, size = 'md' }: ModalProps) {
  if (!open) return null
  const widths = { sm: 'max-w-sm', md: 'max-w-lg', lg: 'max-w-2xl' }
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" />
      <div
        className={cn('relative panel w-full animate-slide-up', widths[size])}
        onClick={(e) => e.stopPropagation()}
      >
        {title && (
          <div className="flex items-center justify-between mb-4 pb-3 border-b border-surface-border">
            <h2 className="text-lg font-semibold text-white">{title}</h2>
            <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors text-xl leading-none">×</button>
          </div>
        )}
        {children}
      </div>
    </div>
  )
}

// ─── ProgressBar ──────────────────────────────────────────────────────────────
interface ProgressBarProps { value: number; max?: number; color?: string; className?: string; animated?: boolean }
export function ProgressBar({ value, max = 100, color = '#2d7dd2', className, animated }: ProgressBarProps) {
  const pct = Math.min(100, (value / max) * 100)
  return (
    <div className={cn('h-2 bg-surface-border rounded-full overflow-hidden', className)}>
      <div
        className={cn('h-full rounded-full transition-all duration-1000', animated && 'forge-active')}
        style={{ width: `${pct}%`, backgroundColor: color }}
      />
    </div>
  )
}

// ─── EmptyState ───────────────────────────────────────────────────────────────
export function EmptyState({ icon, title, message, action }: {
  icon?: string; title: string; message?: string; action?: React.ReactNode
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center space-y-3">
      {icon && <span className="text-5xl">{icon}</span>}
      <p className="text-gray-300 font-medium">{title}</p>
      {message && <p className="text-gray-500 text-sm max-w-xs">{message}</p>}
      {action}
    </div>
  )
}

// ─── Tooltip ─────────────────────────────────────────────────────────────────
export function Tooltip({ children, text }: { children: React.ReactNode; text: string }) {
  return (
    <div className="relative group inline-block">
      {children}
      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-gray-900 text-xs text-white rounded whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50 border border-surface-border">
        {text}
      </div>
    </div>
  )
}

// ─── Tab ──────────────────────────────────────────────────────────────────────
interface TabsProps { tabs: { id: string; label: string; icon?: string }[]; active: string; onChange: (id: string) => void }
export function Tabs({ tabs, active, onChange }: TabsProps) {
  return (
    <div className="flex gap-1 p-1 bg-surface-tertiary rounded-lg">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onChange(tab.id)}
          className={cn(
            'flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-all',
            active === tab.id
              ? 'bg-accent-blue text-white'
              : 'text-gray-400 hover:text-white hover:bg-surface-elevated',
          )}
        >
          {tab.icon && <span>{tab.icon}</span>}
          {tab.label}
        </button>
      ))}
    </div>
  )
}
