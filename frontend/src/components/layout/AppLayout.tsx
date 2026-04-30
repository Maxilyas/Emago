import React, { useState } from 'react'
import { NavLink, Outlet, Link } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { useGameStore } from '@/stores/gameStore'
import { useGameSocket } from '@/hooks/useGameSocket'
import { CombatReport } from '@/components/combat/CombatReport'
import { NotificationPanel } from '@/components/layout/NotificationPanel'
import { useAuthStore } from '@/stores/authStore'

const NAV_ITEMS = [
  { to: '/dashboard', label: 'Quartier Général', icon: HQIcon,      short: 'QG' },
  { to: '/hangar',    label: 'Hangar',            icon: HangarIcon,  short: 'Hangar' },
  { to: '/buildings', label: 'Bâtiments',         icon: BuildIcon,   short: 'Bâtiments' },
  { to: '/forge',     label: 'Forge',             icon: ForgeIcon,   short: 'Forge' },
  { to: '/galaxy',    label: 'Galaxie',           icon: GalaxyIcon,  short: 'Galaxie' },
  { to: '/ranking',   label: 'Classement',        icon: RankIcon,    short: 'Top' },
]

export function AppLayout() {
  const { wsConnected, pendingCombatResult, setPendingCombatResult, notifications } = useGameStore()
  const [showNotifs, setShowNotifs] = useState(false)
  const { username } = useAuthStore()
  useGameSocket()

  return (
    <div className="min-h-screen flex flex-col lg:flex-row relative z-10">

      {/* ── Sidebar desktop ───────────────────────────────────────────────── */}
      <aside className="hidden lg:flex flex-col w-60 shrink-0 border-r border-border/60"
        style={{ background: 'rgba(5,8,16,0.95)', backdropFilter: 'blur(20px)' }}>

        {/* Logo */}
        <div className="p-6 border-b border-border/60">
          <div className="font-display font-bold tracking-wider">
            <span className="text-3xl text-white">EM</span>
            <span className="text-3xl" style={{ color: '#2d7dd2', textShadow: '0 0 20px rgba(45,125,210,0.8)' }}>AGO</span>
          </div>
          <p className="text-[10px] text-gray-600 mt-1 tracking-widest uppercase font-display">
            Conquête Spatiale
          </p>
        </div>

        {/* Profil joueur */}
        <div className="px-4 py-3 border-b border-border/40 mx-3 mt-3 rounded-lg"
          style={{ background: 'rgba(45,125,210,0.06)', border: '1px solid rgba(45,125,210,0.15)' }}>
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-full flex items-center justify-center text-xs font-bold"
              style={{ background: 'linear-gradient(135deg, #2d7dd2, #7c3aed)', boxShadow: '0 0 10px rgba(45,125,210,0.4)' }}>
              {username?.[0]?.toUpperCase() ?? 'C'}
            </div>
            <div>
              <p className="text-xs font-semibold text-white truncate max-w-[120px]">
                {username ?? 'Commandant'}
              </p>
              <p className="text-[10px] text-gray-500">Commandant</p>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 p-3 space-y-0.5 mt-2">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200 group relative',
                isActive
                  ? 'text-white'
                  : 'text-gray-500 hover:text-gray-200',
              )}
              style={({ isActive }) => isActive ? {
                background: 'linear-gradient(135deg, rgba(45,125,210,0.15), rgba(45,125,210,0.05))',
                border: '1px solid rgba(45,125,210,0.25)',
                boxShadow: '0 0 15px rgba(45,125,210,0.1)',
              } : {}}
            >
              {({ isActive }) => (
                <>
                  {/* Barre latérale active */}
                  {isActive && (
                    <div className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-full"
                      style={{ background: 'linear-gradient(180deg, #2d7dd2, #7c3aed)', boxShadow: '0 0 8px rgba(45,125,210,0.8)' }} />
                  )}
                  <span className={cn('transition-all duration-200', isActive ? 'text-accent-blue' : 'text-gray-600 group-hover:text-gray-400')}>
                    <item.icon size={16} />
                  </span>
                  <span className="font-medium tracking-wide text-xs">{item.label}</span>
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Status WS */}
        <div className="p-4 border-t border-border/40">
          <div className="flex items-center gap-2">
            <div className={cn(
              'h-2 w-2 rounded-full transition-all',
              wsConnected ? 'bg-green-400' : 'bg-red-500 animate-pulse'
            )}
            style={wsConnected ? { boxShadow: '0 0 6px rgba(74,222,128,0.8)' } : {}} />
            <span className="text-[10px] text-gray-600 tracking-wide">
              {wsConnected ? 'SYSTÈME EN LIGNE' : 'RECONNEXION...'}
            </span>
          </div>
        </div>
      </aside>

      {/* ── Zone principale ───────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-h-0 min-w-0">

        {/* Topbar */}
        <header className="flex items-center justify-between px-4 lg:px-6 py-3 border-b border-border/60 shrink-0"
          style={{ background: 'rgba(5,8,16,0.8)', backdropFilter: 'blur(20px)' }}>

          {/* Logo mobile */}
          <div className="lg:hidden font-display font-bold text-xl">
            <span className="text-white">EM</span>
            <span style={{ color: '#2d7dd2' }}>AGO</span>
          </div>

          <div className="hidden lg:block" />

          {/* Actions */}
          <div className="flex items-center gap-2">
            <button onClick={() => setShowNotifs(v => !v)}
              className="relative p-2 rounded-lg text-gray-400 hover:text-white hover:bg-surface-elevated transition-all">
              <BellIcon size={18} />
              {notifications.length > 0 && (
                <span className="notif-dot">{notifications.length > 9 ? '9+' : notifications.length}</span>
              )}
            </button>
            <Link to="/profile" className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-lg text-gray-400 hover:text-white transition-colors text-xs">
              <span className="h-6 w-6 rounded-full flex items-center justify-center text-xs font-bold"
                style={{ background: 'linear-gradient(135deg, #2d7dd2, #7c3aed)' }}>
                {username?.[0]?.toUpperCase() ?? 'C'}
              </span>
              {username}
            </Link>
          </div>
        </header>

        {/* Contenu */}
        <main className="flex-1 overflow-y-auto">
          <div className="p-4 lg:p-6 pb-20 lg:pb-6">
            <Outlet />
          </div>
        </main>
      </div>

      {/* ── Navigation mobile ─────────────────────────────────────────────── */}
      <nav className="lg:hidden fixed bottom-0 left-0 right-0 z-40 border-t border-border/60"
        style={{ background: 'rgba(5,8,16,0.95)', backdropFilter: 'blur(20px)' }}>
        <div className="flex">
          {NAV_ITEMS.map((item) => (
            <NavLink key={item.to} to={item.to}
              className={({ isActive }) => cn(
                'flex-1 flex flex-col items-center gap-0.5 py-2.5 text-[10px] tracking-wide transition-all font-medium',
                isActive ? 'text-accent-blue' : 'text-gray-600',
              )}>
              {({ isActive }) => (
                <>
                  <span className={isActive ? 'text-accent-blue' : 'text-gray-500'}>
                    <item.icon size={18} />
                  </span>
                  {item.short}
                </>
              )}
            </NavLink>
          ))}
        </div>
      </nav>

      {/* Notifs overlay */}
      {showNotifs && (
        <div className="fixed inset-0 z-50 lg:inset-auto lg:top-14 lg:right-4 lg:w-80"
          onClick={() => setShowNotifs(false)}>
          <div onClick={e => e.stopPropagation()}>
            <NotificationPanel onClose={() => setShowNotifs(false)} />
          </div>
        </div>
      )}

      <CombatReport data={pendingCombatResult} onClose={() => setPendingCombatResult(null)} />
    </div>
  )
}

/* ── Icônes SVG inline ───────────────────────────────────────────────────── */
function HQIcon({ size = 20 }: { size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>
  </svg>
}
function HangarIcon({ size = 20 }: { size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>
  </svg>
}
function BuildIcon({ size = 20 }: { size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <rect x="2" y="3" width="6" height="18"/><rect x="9" y="8" width="6" height="13"/><rect x="16" y="5" width="6" height="16"/>
  </svg>
}
function ForgeIcon({ size = 20 }: { size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z"/>
  </svg>
}
function GalaxyIcon({ size = 20 }: { size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="4"/><line x1="4.93" y1="4.93" x2="9.17" y2="9.17"/><line x1="14.83" y1="14.83" x2="19.07" y2="19.07"/><line x1="14.83" y1="9.17" x2="19.07" y2="4.93"/><line x1="4.93" y1="19.07" x2="9.17" y2="14.83"/>
  </svg>
}
function RankIcon({ size = 20 }: { size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
  </svg>
}
function BellIcon({ size = 20 }: { size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
    <path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 01-3.46 0"/>
  </svg>
}
