import React, { useMemo } from 'react'
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
import type { PlanetSummary } from '@/types'

// ─── Helpers ─────────────────────────────────────────────────────────────────

function useCountdown(targetIso: string) {
  const [s, setS] = React.useState(0)
  React.useEffect(() => {
    const up = () => setS(Math.max(0, Math.round((new Date(targetIso).getTime() - Date.now()) / 1000)))
    up()
    const id = setInterval(up, 1000)
    return () => clearInterval(id)
  }, [targetIso])
  return s
}

function fmtCountdownHMS(s: number): string {
  if (s <= 0) return 'TERMINÉ'
  const h = String(Math.floor(s / 3600)).padStart(2, '0')
  const m = String(Math.floor((s % 3600) / 60)).padStart(2, '0')
  const sec = String(s % 60).padStart(2, '0')
  return `${h}:${m}:${sec}`
}

function timeAgo(isoDate: string): string {
  const diff = Date.now() - new Date(isoDate).getTime()
  const m = Math.floor(diff / 60_000)
  if (m < 1) return 'À l\'instant'
  if (m < 60) return `Il y a ${m}min`
  const h = Math.floor(m / 60)
  if (h < 24) return `Il y a ${h}h`
  return `Il y a ${Math.floor(h / 24)}j`
}

// ─── Widget : Ressources de l'Empire ─────────────────────────────────────────

function EmpireResourcesWidget({ planets, loading }: { planets?: PlanetSummary[]; loading: boolean }) {
  const totals = useMemo(() => {
    if (!planets?.length) return { metal: 0, crystal: 0, deuterium: 0 }
    return planets.reduce(
      (acc, p) => ({ metal: acc.metal + p.metal, crystal: acc.crystal + p.crystal, deuterium: acc.deuterium + p.deuterium }),
      { metal: 0, crystal: 0, deuterium: 0 },
    )
  }, [planets])

  if (loading) return <Skeleton className="h-32" />

  return (
    <div className="panel panel-glow">
      <div className="flex items-center justify-between mb-3">
        <p className="section-title">Ressources de l'Empire</p>
        <span className="text-xs text-gray-600">{planets?.length ?? 0} planète(s)</span>
      </div>

      {/* Totaux empire */}
      <div className="grid grid-cols-3 gap-3 mb-4 pb-4 border-b border-border/40">
        {[
          { icon: '⛏️', label: 'Métal',     val: totals.metal,     color: '#94a3b8' },
          { icon: '💎', label: 'Cristal',   val: totals.crystal,   color: '#7dd3fc' },
          { icon: '⚗️', label: 'Deutérium', val: totals.deuterium, color: '#86efac' },
        ].map(r => (
          <div key={r.label} className="text-center">
            <p className="text-[10px] text-gray-600 mb-1 font-display">{r.icon} {r.label}</p>
            <p className="text-base font-mono font-bold" style={{ color: r.color }}>{fmtShort(r.val)}</p>
          </div>
        ))}
      </div>

      {/* Liste planètes */}
      <div className="space-y-1">
        {(planets ?? []).map(p => (
          <Link
            key={p.id}
            to={`/buildings?planet=${p.id}`}
            className="flex items-center justify-between px-2 py-1.5 rounded-md hover:bg-surface-elevated transition-colors group"
          >
            <div className="flex items-center gap-2 min-w-0">
              <span className="text-xs shrink-0">{p.is_homeworld ? '🏠' : '🪐'}</span>
              <span className="text-xs text-gray-300 truncate">{p.name}</span>
              {p.is_homeworld && (
                <span className="text-[9px] text-yellow-500 bg-yellow-900/20 px-1.5 py-0.5 rounded font-display shrink-0">NATALE</span>
              )}
            </div>
            <div className="flex items-center gap-3 shrink-0">
              <span className="text-[11px] font-mono" style={{ color: '#94a3b8' }}>{fmtShort(p.metal)}</span>
              <span className="text-[11px] font-mono" style={{ color: '#7dd3fc' }}>{fmtShort(p.crystal)}</span>
              <span className="text-[11px] font-mono" style={{ color: '#86efac' }}>{fmtShort(p.deuterium)}</span>
              <span className="text-[10px] text-gray-600 group-hover:text-accent-blue font-display transition-colors">GÉRER →</span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}

// ─── Widget : Recherche en cours ──────────────────────────────────────────────

function ResearchWidget({ research }: { research: any | null }) {
  const s = useCountdown(research?.completes_at ?? '')
  const started = research ? new Date(research.started_at).getTime() : 0
  const ends    = research ? new Date(research.completes_at).getTime() : 1
  const pct = research ? Math.min(100, Math.max(0, ((Date.now() - started) / (ends - started)) * 100)) : 0

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <p className="section-title">Recherche</p>
        <Link to="/tech" className="text-[10px] text-accent-blue font-display">ARBRE →</Link>
      </div>
      {research ? (
        <div className="panel space-y-3">
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-lg flex items-center justify-center text-base shrink-0"
              style={{ background: 'rgba(124,58,237,0.15)', border: '1px solid rgba(124,58,237,0.3)' }}>
              🔬
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-white truncate">{research.tech_label}</p>
              <p className="text-xs text-gray-500">→ Niveau {research.target_level}</p>
            </div>
            <span className={cn('ml-auto font-mono text-xs shrink-0', s <= 0 ? 'text-green-400' : 'text-accent-cyan')}>
              {s <= 0 ? 'TERMINÉ ✓' : fmtCountdownHMS(s)}
            </span>
          </div>
          <div className="h-1.5 bg-surface-border rounded-full overflow-hidden">
            <div className="h-full rounded-full transition-all duration-1000"
              style={{ width: `${pct}%`, background: 'linear-gradient(90deg, #7c3aed, #a855f7)' }} />
          </div>
        </div>
      ) : (
        <Link to="/tech"
          className="panel hover:bg-surface-elevated transition-all flex items-center gap-3 group"
          style={{ borderColor: 'rgba(124,58,237,0.15)' }}>
          <span className="text-xl">🔬</span>
          <div>
            <p className="text-sm text-gray-400">Aucune recherche en cours</p>
            <p className="text-[10px] text-purple-400 font-display group-hover:text-purple-300 transition-colors">EXPLORER L'ARBRE →</p>
          </div>
        </Link>
      )}
    </div>
  )
}

// ─── Widget : Expéditions actives ─────────────────────────────────────────────

const DURATION_LABEL: Record<string, string> = {
  SHORT: 'Courte (1h)',
  MEDIUM: 'Moyenne (4h)',
  LONG: 'Longue (12h)',
}

function ExpeditionsWidget({ expeditions }: { expeditions: any[] }) {
  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <p className="section-title">Expéditions ({expeditions.length})</p>
        <Link to="/expeditions" className="text-[10px] text-accent-blue font-display">GÉRER →</Link>
      </div>
      <div className="space-y-2">
        {expeditions.slice(0, 3).map(exp => (
          <ExpeditionRow key={exp.expedition_id} exp={exp} />
        ))}
        {expeditions.length > 3 && (
          <p className="text-xs text-gray-600 text-center pt-1">+{expeditions.length - 3} autres</p>
        )}
      </div>
    </div>
  )
}

function ExpeditionRow({ exp }: { exp: any }) {
  const s = useCountdown(exp.returns_at)
  return (
    <div className="panel py-2.5 flex items-center justify-between gap-3">
      <div className="flex items-center gap-2.5">
        <div className="h-7 w-7 rounded-lg flex items-center justify-center text-sm shrink-0"
          style={{ background: 'rgba(124,58,237,0.12)', border: '1px solid rgba(124,58,237,0.25)' }}>
          🚀
        </div>
        <div>
          <p className="text-xs text-white">{exp.ship_ids.length} vaisseau{exp.ship_ids.length > 1 ? 'x' : ''}</p>
          <p className="text-[10px] text-gray-600">{DURATION_LABEL[exp.duration] ?? exp.duration}</p>
        </div>
      </div>
      <span className={cn('font-mono text-xs shrink-0', s <= 0 ? 'text-green-400' : 'text-accent-cyan')}>
        {s <= 0 ? 'RETOUR ✓' : fmtCountdownHMS(s)}
      </span>
    </div>
  )
}

// ─── Widget : Dernier combat ──────────────────────────────────────────────────

const OUTCOME_CONFIG: Record<string, { icon: string; label: string; bg: string; border: string }> = {
  ATTACKER_WIN: { icon: '⚔️', label: 'Victoire attaquant', bg: 'rgba(239,68,68,0.12)',    border: 'rgba(239,68,68,0.25)' },
  DEFENDER_WIN: { icon: '🛡️', label: 'Victoire défenseur', bg: 'rgba(45,125,210,0.12)',   border: 'rgba(45,125,210,0.25)' },
  DRAW:         { icon: '🤝', label: 'Match nul',           bg: 'rgba(107,114,128,0.12)', border: 'rgba(107,114,128,0.25)' },
}

function LastCombatWidget({ combat }: { combat: any }) {
  const cfg = OUTCOME_CONFIG[combat.outcome] ?? OUTCOME_CONFIG.DRAW
  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <p className="section-title">Dernier combat</p>
        <Link to="/combat" className="text-[10px] text-accent-blue font-display">HISTORIQUE →</Link>
      </div>
      <Link to={`/combat/${combat.combat_id}`}
        className="panel hover:bg-surface-elevated transition-all block group">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-lg flex items-center justify-center text-base shrink-0"
              style={{ background: cfg.bg, border: `1px solid ${cfg.border}` }}>
              {cfg.icon}
            </div>
            <div>
              <p className="text-sm font-semibold text-white">{cfg.label}</p>
              <p className="text-xs text-gray-500">{combat.total_rounds} rounds</p>
            </div>
          </div>
          <div className="text-right shrink-0">
            <p className="text-[10px] text-gray-600">{timeAgo(combat.fought_at)}</p>
            <p className="text-[10px] text-accent-blue font-display group-hover:text-accent-cyan transition-colors">RAPPORT →</p>
          </div>
        </div>
      </Link>
    </div>
  )
}

// ─── Page principale ──────────────────────────────────────────────────────────

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
  const { data: techTree } = useQuery({
    queryKey: ['tech', 'tree'], queryFn: () => api.get<any>('/tech/tree'), refetchInterval: 30_000,
  })
  const { data: expeditions = [] } = useQuery({
    queryKey: ['expeditions', 'active'],
    queryFn: () => api.get<any[]>('/expeditions/active'),
    refetchInterval: 15_000,
  })
  const { data: combatHistory } = useQuery({
    queryKey: ['combat', 'history', 'latest'],
    queryFn: () => api.get<any[]>('/combat/history?limit=1'),
    staleTime: 60_000,
    refetchInterval: 60_000,
  })

  const activeForgePre = forgeHistory?.filter(f => !f.is_completed) ?? []
  const { data: activeForgeStatuses } = useQuery({
    queryKey: ['forge', 'active', activeForgePre.map(f => f.forge_id)],
    queryFn: () => Promise.all(activeForgePre.map(f => forgeApi.status(f.forge_id))),
    enabled: activeForgePre.length > 0, refetchInterval: 30_000,
  })

  const activeResearch = techTree?.active_research ?? null
  const lastCombat     = combatHistory?.[0] ?? null
  const homePlanet     = planets?.[0] ?? null

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

      {/* Ressources de l'Empire */}
      <EmpireResourcesWidget planets={planets} loading={planetsLoading} />

      {/* Stats empire */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: 'Vaisseaux', value: ships?.length ?? 0,    icon: '🚀', to: '/hangar',                                          color: '#2d7dd2' },
          { label: 'Flottes',   value: fleets?.length ?? 0,   icon: '✈️', to: '/galaxy',                                         color: '#06b6d4' },
          { label: 'En forge',  value: activeForgePre.length, icon: '🔨', to: '/forge',                                           color: '#f97316' },
          { label: 'Planètes',  value: planets?.length ?? 0,  icon: '🌍', to: `/buildings?planet=${homePlanet?.id ?? ''}`,        color: '#10b981' },
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

      {/* Widgets en grille */}
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
                      style={{
                        background: fleet.mission === 'ATTACK' ? 'rgba(239,68,68,0.15)' : 'rgba(45,125,210,0.15)',
                        border: `1px solid ${fleet.mission === 'ATTACK' ? 'rgba(239,68,68,0.3)' : 'rgba(45,125,210,0.3)'}`,
                      }}>
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
            <div className="flex items-center justify-between mb-3">
              <p className="section-title">Forge en cours</p>
              <Link to="/forge" className="text-[10px] text-accent-blue font-display">FORGE →</Link>
            </div>
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

        {/* Recherche en cours */}
        <ResearchWidget research={activeResearch} />

        {/* Expéditions actives */}
        {expeditions.length > 0 && <ExpeditionsWidget expeditions={expeditions} />}

        {/* Dernier combat */}
        {lastCombat && <LastCombatWidget combat={lastCombat} />}

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

function FleetCountdown({ arrivesAt }: { arrivesAt: string }) {
  const s = useCountdown(arrivesAt)
  if (s <= 0) return <span className="text-green-400 text-xs font-display">ARRIVÉE</span>
  return <span className="text-accent-cyan font-mono text-xs">{fmtCountdownHMS(s)}</span>
}
