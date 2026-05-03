// ─── AppLayout.tsx — v1.1 (Sprint RPG)
// Agent 6 — Développeur Frontend
//
// Ajouts Sprint 4 (inchangés) :
//   - Alliances + Combat dans NAV_ITEMS
//   - CombatReport overlay + bouton "Voir rapport complet"
//
// Ajouts v1.1 :
//   - SpectreAwakening overlay (grade_up → grade 5)
//   - Toast enrichi pour pendingForgeResult (Dérive vs normal)

import React, { useEffect } from 'react'
import { NavLink, Outlet, Link, useNavigate } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { useGameStore } from '@/stores/gameStore'
import { useGameSocket } from '@/hooks/useGameSocket'
import { CombatReport } from '@/components/combat/CombatReport'
import { NotificationPanel } from '@/components/layout/NotificationPanel'
import { SpectreAwakening } from '@/components/ships/SpectreAwakening'
import { useAuthStore } from '@/stores/authStore'
import { GlobalResourceBar } from '@/components/layout/GlobalResourceBar'

const NAV_ITEMS = [
  { to: '/dashboard',   label: 'Quartier Général', short: 'QG',        Icon: HomeIcon },
  { to: '/hangar',      label: 'Hangar',            short: 'Hangar',    Icon: HangarIcon },
  { to: '/buildings',   label: 'Bâtiments',         short: 'Bâtiments', Icon: BuildIcon },
  { to: '/expeditions', label: 'Expéditions',       short: 'Expéd.',    Icon: RocketIcon },
  { to: '/tech',        label: 'Technologies',      short: 'Tech',      Icon: TechIcon },
  { to: '/forge',       label: 'Forge',             short: 'Forge',     Icon: ForgeIcon },
  { to: '/galaxy',      label: 'Galaxie',           short: 'Galaxie',   Icon: GalaxyIcon },
  { to: '/alliances',   label: 'Alliances',         short: 'Alliances', Icon: AllianceIcon },  // ← Sprint 4
  { to: '/ranking',     label: 'Classement',        short: 'Top',       Icon: RankIcon },
  { to: '/combat',      label: 'Combats',           short: 'Combats',   Icon: CombatIcon },    // ← Sprint 4
]

export function AppLayout() {
  const {
    wsConnected,
    pendingCombatResult, setPendingCombatResult,
    spectreData, setSpectreData,
    pendingForgeResult, setPendingForgeResult,
    notifications,
  } = useGameStore()
  const { username } = useAuthStore()
  const navigate = useNavigate()
  useGameSocket()

  // Toast forge enrichi — déclenché quand pendingForgeResult arrive
  // (le toast Dérive a un style distinct, toast normal pour forge standard)
  useEffect(() => {
    if (!pendingForgeResult) return
    // Le toast est déjà émis dans handleForgeComplete (NotificationPanel).
    // On remet juste pendingForgeResult à null après consommation.
    setPendingForgeResult(null)
  }, [pendingForgeResult, setPendingForgeResult])

  const handleViewFullReport = (combatId: string) => {
    setPendingCombatResult(null)
    navigate(`/combat/${combatId}`)
  }

  return (
    <div className="min-h-screen flex flex-col lg:flex-row relative z-10">

      {/* ── Sidebar desktop ────────────────────────────────────────────────── */}
      <aside className="hidden lg:flex flex-col w-60 shrink-0 border-r border-border/60"
        style={{ background: 'rgba(5,8,16,0.95)', backdropFilter: 'blur(20px)' }}>

        {/* Logo */}
        <div className="p-6 border-b border-border/60">
          <div className="font-display font-bold tracking-wider">
            <span className="text-3xl text-white">EM</span>
            <span className="text-3xl" style={{ color: '#2d7dd2', textShadow: '0 0 20px rgba(45,125,210,0.8)' }}>AGO</span>
          </div>
          <p className="text-[10px] text-gray-600 mt-1 tracking-widest uppercase font-display">Conquête Spatiale</p>
        </div>

        {/* Profil */}
        <div className="px-3 py-3 border-b border-border/40 mx-3 mt-3 rounded-lg"
          style={{ background: 'rgba(45,125,210,0.06)', border: '1px solid rgba(45,125,210,0.15)' }}>
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0"
              style={{ background: 'linear-gradient(135deg, #2d7dd2, #7c3aed)', boxShadow: '0 0 10px rgba(45,125,210,0.4)' }}>
              {username?.[0]?.toUpperCase() ?? 'C'}
            </div>
            <div className="min-w-0">
              <p className="text-xs font-semibold text-white truncate">{username ?? 'Commandant'}</p>
              <p className="text-[10px] text-gray-500">Commandant</p>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 p-3 space-y-0.5 mt-2 overflow-y-auto">
          {NAV_ITEMS.map((item) => (
            <NavLink key={item.to} to={item.to}
              className={({ isActive }) => cn(
                'flex items-center gap-3 px-3 py-2 rounded-lg text-xs transition-all duration-200 group relative',
                isActive ? 'text-white' : 'text-gray-500 hover:text-gray-200',
              )}
              style={({ isActive }) => isActive ? {
                background: 'linear-gradient(135deg, rgba(45,125,210,0.15), rgba(45,125,210,0.05))',
                border: '1px solid rgba(45,125,210,0.25)',
                boxShadow: '0 0 15px rgba(45,125,210,0.1)',
              } : {}}>
              {({ isActive }) => (
                <>
                  {isActive && <div className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-4 rounded-full"
                    style={{ background: 'linear-gradient(180deg, #2d7dd2, #7c3aed)', boxShadow: '0 0 8px rgba(45,125,210,0.8)' }} />}
                  <span className={cn('transition-all duration-200', isActive ? 'text-accent-blue' : 'text-gray-600 group-hover:text-gray-400')}>
                    <item.Icon size={15} />
                  </span>
                  <span className="font-medium tracking-wide">{item.label}</span>
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* WS Status */}
        <div className="p-4 border-t border-border/40">
          <div className="flex items-center gap-2">
            <div className={cn('h-2 w-2 rounded-full', wsConnected ? 'bg-green-400' : 'bg-red-500 animate-pulse')}
              style={wsConnected ? { boxShadow: '0 0 6px rgba(74,222,128,0.8)' } : {}} />
            <span className="text-[10px] text-gray-600 tracking-wide font-display">
              {wsConnected ? 'SYSTÈME EN LIGNE' : 'RECONNEXION...'}
            </span>
          </div>
        </div>
      </aside>

      {/* ── Zone principale ─────────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-h-0 min-w-0">

        {/* Topbar */}
        <header className="flex items-center justify-between px-4 lg:px-6 py-3 border-b border-border/60 shrink-0"
          style={{ background: 'rgba(5,8,16,0.8)', backdropFilter: 'blur(20px)' }}>
          <div className="lg:hidden font-display font-bold text-xl">
            <span className="text-white">EM</span><span style={{ color: '#2d7dd2' }}>AGO</span>
          </div>
          <div className="hidden lg:block" />
          <div className="flex items-center gap-2">
            <NotificationPanel />
          </div>
        </header>

        {/* ── Barre de ressources persistante ──────────────────────────── */}
        <div className="shrink-0 border-b border-border/40 px-4 lg:px-6 py-2"
          style={{ background: 'rgba(5,8,16,0.85)' }}>
          <GlobalResourceBar />
        </div>

        <main className="flex-1 overflow-y-auto">
          <div className="p-4 lg:p-6 pb-24 lg:pb-6"><Outlet /></div>
        </main>
      </div>

      {/* ── Navigation mobile ────────────────────────────────────────────────── */}
      <nav className="lg:hidden fixed bottom-0 left-0 right-0 z-40 border-t border-border/60 overflow-x-auto"
        style={{ background: 'rgba(5,8,16,0.97)', backdropFilter: 'blur(20px)' }}>
        <div className="flex min-w-max">
          {NAV_ITEMS.map((item) => (
            <NavLink key={item.to} to={item.to}
              className={({ isActive }) => cn(
                'flex flex-col items-center gap-0.5 px-3 py-2.5 text-[9px] tracking-wide transition-all font-display min-w-[52px]',
                isActive ? 'text-accent-blue' : 'text-gray-600',
              )}>
              {({ isActive }) => (
                <>
                  <span className={isActive ? 'text-accent-blue' : 'text-gray-500'}>
                    <item.Icon size={17} />
                  </span>
                  {item.short}
                </>
              )}
            </NavLink>
          ))}
        </div>
      </nav>

      {/* ── CombatReport overlay (résultat WS immédiat) ──────────────────────── */}
      {/* Ajout Sprint 4 : bouton "Voir rapport complet" → /combat/:id          */}
      <CombatReport
        data={pendingCombatResult}
        onClose={() => setPendingCombatResult(null)}
        onViewFull={pendingCombatResult?.combat_id
          ? () => handleViewFullReport(pendingCombatResult.combat_id)
          : undefined
        }
      />

      {/* ── SpectreAwakening overlay (grade_up → grade 5) — v1.1 ─────────────── */}
      <SpectreAwakening
        data={spectreData}
        onDismiss={() => setSpectreData(null)}
      />
    </div>
  )
}

// ─── Icônes SVG ──────────────────────────────────────────────────────────────

function HomeIcon({ size = 20 }: { size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
}
function HangarIcon({ size = 20 }: { size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
}
function BuildIcon({ size = 20 }: { size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><rect x="2" y="3" width="6" height="18"/><rect x="9" y="8" width="6" height="13"/><rect x="16" y="5" width="6" height="16"/></svg>
}
function RocketIcon({ size = 20 }: { size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 00-2.91-.09z"/><path d="M12 15l-3-3a22 22 0 012-3.95A12.88 12.88 0 0122 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 01-4 2z"/><path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/><path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/></svg>
}
function TechIcon({ size = 20 }: { size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.07 4.93l-1.41 1.41M5.34 18.66l-1.41 1.41M4.93 4.93l1.41 1.41M18.66 18.66l1.41 1.41M2 12h2M20 12h2M12 2v2M12 20v2"/></svg>
}
function ForgeIcon({ size = 20 }: { size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z"/></svg>
}
function GalaxyIcon({ size = 20 }: { size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="4"/><line x1="4.93" y1="4.93" x2="9.17" y2="9.17"/><line x1="14.83" y1="14.83" x2="19.07" y2="19.07"/><line x1="14.83" y1="9.17" x2="19.07" y2="4.93"/><line x1="4.93" y1="19.07" x2="9.17" y2="14.83"/></svg>
}
function RankIcon({ size = 20 }: { size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
}
// ← Sprint 4 : nouvelles icônes
function AllianceIcon({ size = 20 }: { size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg>
}
function CombatIcon({ size = 20 }: { size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M14.5 17.5L3 6V3h3l11.5 11.5"/><path d="M13 19l6-6"/><path d="M2 2l20 20"/><path d="M9.5 6.5l5 5"/></svg>
}