import React from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '@/lib/api'
import { planetsApi, forgeApi } from '@/api'
import { ForgeProgress } from '@/components/forge/ForgeProgress'
import { DailyPanel } from '@/components/daily/DailyPanel'
import { Skeleton } from '@/components/ui'
import { fmtShort, fmt, cn } from '@/lib/utils'
import { useAuthStore } from '@/stores/authStore'
import { useGameStore } from '@/stores/gameStore'

function FleetCountdown({ arrivesAt }: { arrivesAt: string }) {
  const [s, setS] = React.useState(0)
  React.useEffect(() => {
    const up = () => setS(Math.max(0, Math.round((new Date(arrivesAt).getTime() - Date.now()) / 1000)))
    up(); const id = setInterval(up, 1000); return () => clearInterval(id)
  }, [arrivesAt])
  if (s <= 0) return <span className="text-green-400 text-xs font-display">ARRIVÉE</span>
  const h = String(Math.floor(s/3600)).padStart(2,'0')
  const m = String(Math.floor((s%3600)/60)).padStart(2,'0')
  const sec = String(s%60).padStart(2,'0')
  return <span className="text-accent-cyan font-mono text-xs">{h}:{m}:{sec}</span>
}

export function DashboardPage() {
  const qc = useQueryClient()
  const { username } = useAuthStore()
  const { notifications } = useGameStore()

  const { data: planets, isLoading: planetsLoading } = useQuery({
    queryKey: ['planets'], queryFn: planetsApi.list, refetchInterval: 30_000,
  })
  const { data: forgeHistory } = useQuery({
    queryKey: ['forge', 'history'], queryFn: forgeApi.history, refetchInterval: 30_000,
  })
  const { data: fleets } = useQuery({
    queryKey: ['fleets'], queryFn: () => api.get<any[]>('/fleets'), refetchInterval: 10_000,
  })
  const { data: ships } = useQuery({
    queryKey: ['ships'], queryFn: () => api.get<any[]>('/ships'),
  })
  const { data: myRank } = useQuery({
    queryKey: ['ranking', 'me'], queryFn: () => api.get<any>('/ranking/me'),
  })

  const activeForgePre = forgeHistory?.filter(f => !f.is_completed) ?? []
  const { data: activeForgeStatuses } = useQuery({
    queryKey: ['forge', 'active', activeForgePre.map(f => f.forge_id)],
    queryFn: () => Promise.all(activeForgePre.map(f => forgeApi.status(f.forge_id))),
    enabled: activeForgePre.length > 0, refetchInterval: 30_000,
  })

  const homePlanet = planets?.[0] ?? null

  return (
    <div className="space-y-5 animate-fade-in">

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <p className="section-title mb-1">Quartier Général</p>
          <h1 className="text-2xl font-bold text-white">
            Commandant <span className="font-display" style={{ color: '#2d7dd2' }}>{username?.toUpperCase()}</span>
          </h1>
        </div>
        {myRank && (
          <div className="panel-glass px-4 py-3 text-right">
            <p className="text-[10px] text-gray-600 font-display">RANG</p>
            <p className="text-2xl font-bold font-display text-accent-blue">#{myRank.rank}</p>
            <p className="text-xs text-gray-500 font-mono">{fmt(myRank.score)} pts</p>
          </div>
        )}
      </div>

      {/* Daily compact */}
      <DailyPanel compact />

      {/* Planète principale */}
      {planetsLoading ? <Skeleton className="h-28" /> : homePlanet ? (
        <Link to={`/planets/${homePlanet.id}`}
          className="block panel panel-glow hover:border-accent-blue/40 transition-all duration-300 group">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2.5">
              <div className="h-2 w-2 rounded-full bg-green-400"
                style={{ boxShadow: '0 0 8px rgba(74,222,128,0.8)', animation: 'pulse 2s infinite' }} />
              <span className="text-xs font-display text-white">{homePlanet.name}</span>
              <span className="text-[10px] text-yellow-500 bg-yellow-900/20 border border-yellow-800/40 px-2 py-0.5 rounded-full font-display">NATALE</span>
            </div>
            <span className="text-xs text-gray-600 group-hover:text-accent-blue transition-colors font-display">GÉRER →</span>
          </div>
          <div className="grid grid-cols-3 gap-4">
            {[
              { icon: '⛏️', label: 'Métal',     val: homePlanet.metal,     color: '#94a3b8' },
              { icon: '💎', label: 'Cristal',   val: homePlanet.crystal,   color: '#7dd3fc' },
              { icon: '⚗️', label: 'Deutérium', val: homePlanet.deuterium, color: '#86efac' },
            ].map(r => (
              <div key={r.label} className="text-center">
                <p className="text-xs text-gray-600 mb-1">{r.icon} {r.label}</p>
                <p className="text-sm font-mono font-bold" style={{ color: r.color }}>{fmtShort(r.val)}</p>
              </div>
            ))}
          </div>
        </Link>
      ) : null}

      {/* Stats empire */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: 'Vaisseaux', value: ships?.length ?? 0,    icon: '🚀', to: '/hangar',   color: '#2d7dd2' },
          { label: 'Flottes',   value: fleets?.length ?? 0,   icon: '✈️', to: '/galaxy',  color: '#06b6d4' },
          { label: 'En forge',  value: activeForgePre.length, icon: '🔨', to: '/forge',   color: '#f97316' },
          { label: 'Planètes',  value: planets?.length ?? 0,  icon: '🌍', to: `/planets/${homePlanet?.id ?? ''}`, color: '#10b981' },
        ].map(stat => (
          <Link key={stat.label} to={stat.to}
            className="panel text-center hover:bg-surface-elevated transition-all duration-200 group relative">
            <div className="absolute top-0 left-0 right-0 h-px"
              style={{ background: `linear-gradient(90deg, transparent, ${stat.color}50, transparent)` }} />
            <p className="text-2xl mb-2">{stat.icon}</p>
            <p className="text-2xl font-bold font-display" style={{ color: stat.color }}>{stat.value}</p>
            <p className="text-[10px] text-gray-600 uppercase tracking-widest mt-1 group-hover:text-gray-400 transition-colors">
              {stat.label}
            </p>
          </Link>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">

        {/* Flottes en transit */}
        {fleets && fleets.length > 0 && (
          <div>
            <div className="flex items-center justify-between mb-3">
              <p className="section-title">Flottes en transit</p>
              <Link to="/galaxy" className="text-[10px] text-accent-blue font-display">CARTE →</Link>
            </div>
            <div className="space-y-2">
              {fleets.slice(0, 4).map((fleet: any) => (
                <div key={fleet.fleet_id} className="panel py-2.5 flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2.5">
                    <div className="h-7 w-7 rounded-lg flex items-center justify-center text-sm"
                      style={{ background: fleet.mission === 'ATTACK' ? 'rgba(239,68,68,0.15)' : 'rgba(45,125,210,0.15)',
                        border: `1px solid ${fleet.mission === 'ATTACK' ? 'rgba(239,68,68,0.3)' : 'rgba(45,125,210,0.3)'}` }}>
                      {fleet.mission === 'ATTACK' ? '⚔️' : '📦'}
                    </div>
                    <div>
                      <p className="text-xs font-display text-white">{fleet.mission}</p>
                      <p className="text-[10px] text-gray-600">G{fleet.target_galaxy}·S{fleet.target_system}·P{fleet.target_position}</p>
                    </div>
                  </div>
                  <FleetCountdown arrivesAt={fleet.arrives_at} />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Forges actives */}
        {activeForgeStatuses && activeForgeStatuses.length > 0 && (
          <div>
            <p className="section-title mb-3">Forge en cours</p>
            <div className="space-y-2">
              {activeForgeStatuses.map(forge => (
                <ForgeProgress key={forge.forge_id} forge={forge}
                  onComplete={() => {
                    qc.invalidateQueries({ queryKey: ['forge', 'history'] })
                    qc.invalidateQueries({ queryKey: ['ships'] })
                  }} />
              ))}
            </div>
          </div>
        )}

        {/* Activité récente */}
        {notifications.length > 0 && (
          <div>
            <p className="section-title mb-3">Activité récente</p>
            <div className="space-y-1.5">
              {notifications.slice(0, 5).map(n => (
                <div key={n.id} className="flex items-start gap-2.5 px-3 py-2 rounded-lg"
                  style={{ background: 'rgba(20,28,42,0.5)', border: '1px solid rgba(35,50,70,0.4)' }}>
                  <span className="text-sm shrink-0">
                    {n.type === 'combat' ? '⚔️' : n.type === 'forge' ? '🔨' : n.type === 'grade_up' ? '⬆️' : '🔔'}
                  </span>
                  <div className="min-w-0">
                    <p className="text-xs text-white truncate">{n.title}</p>
                    <p className="text-[10px] text-gray-600 truncate">{n.message}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
