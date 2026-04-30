/**
 * DailyPanel.tsx
 * Agent 6 — Frontend
 *
 * Panneau de connexion quotidienne et missions journalières.
 * Affiché dans le Dashboard et comme overlay au login.
 */
import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { api } from '@/lib/api'
import { ApiError } from '@/lib/api'
import { fmt } from '@/lib/utils'

interface DailyMission {
  id: string; label: string; desc: string
  target: number; progress: number
  completed: boolean; claimed: boolean
  reward: Record<string, number>
}

interface DailyStatus {
  streak: number
  last_login: string | null
  can_claim_login: boolean
  missions: DailyMission[]
  offline_gains: Record<string, number> | null
}

interface LoginReward {
  streak: number; reward: Record<string, number>
  next_reward: Record<string, number> | null
  already_claimed: boolean; message: string
}

// Semaine de récompenses (pour affichage visuel)
const WEEK_DAYS = ['L', 'Ma', 'Me', 'J', 'V', 'S', 'D']
const STREAK_LABELS: Record<number, string> = {
  1: '2k ⛏️', 2: '3k ⛏️', 3: '5k ⛏️',
  4: '8k ⛏️', 5: '12k ⛏️', 6: '20k ⛏️', 7: '🎉 Jackpot',
}

// ─── Composant Streak Week ────────────────────────────────────────────────────
function StreakWeek({ streak }: { streak: number }) {
  const day = ((streak - 1) % 7) + 1
  return (
    <div className="flex gap-1.5">
      {WEEK_DAYS.map((label, i) => {
        const dayNum  = i + 1
        const isDone  = streak > 0 && dayNum <= day
        const isToday = dayNum === day
        return (
          <div key={i} className="flex-1 flex flex-col items-center gap-1">
            <div
              className={`h-8 w-8 rounded-lg flex items-center justify-center text-xs font-bold transition-all ${
                isToday ? 'scale-110' : ''
              }`}
              style={isDone ? {
                background: 'linear-gradient(135deg, #2d7dd2, #7c3aed)',
                boxShadow: isToday ? '0 0 12px rgba(45,125,210,0.6)' : 'none',
              } : {
                background: 'rgba(30,40,55,0.6)',
                border: '1px solid rgba(45,58,80,0.5)',
              }}>
              {isDone ? (isToday ? '⚡' : '✓') : label}
            </div>
            <p className="text-[9px] text-gray-700">{STREAK_LABELS[dayNum]}</p>
          </div>
        )
      })}
    </div>
  )
}

// ─── Composant Mission Row ────────────────────────────────────────────────────
function MissionRow({ mission, onClaim }: { mission: DailyMission; onClaim: (id: string) => void }) {
  const pct = Math.min(100, (mission.progress / mission.target) * 100)
  const reward = mission.reward

  return (
    <div className={`flex items-center gap-3 p-3 rounded-xl border transition-all ${
      mission.claimed ? 'opacity-50' : mission.completed ? '' : ''
    }`}
    style={{
      background: mission.completed && !mission.claimed ? 'rgba(45,125,210,0.06)' : 'rgba(20,28,42,0.5)',
      borderColor: mission.completed && !mission.claimed ? 'rgba(45,125,210,0.3)' : 'rgba(35,50,70,0.4)',
    }}>
      {/* Indicateur */}
      <div className={`h-8 w-8 rounded-lg shrink-0 flex items-center justify-center text-sm ${
        mission.claimed ? 'bg-gray-800' : mission.completed ? '' : 'bg-gray-800/60'
      }`}
      style={mission.completed && !mission.claimed ? {
        background: 'linear-gradient(135deg, rgba(45,125,210,0.2), rgba(45,125,210,0.1))',
        border: '1px solid rgba(45,125,210,0.3)',
      } : {}}>
        {mission.claimed ? '✓' : mission.completed ? '🎁' : '○'}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <p className={`text-sm font-medium ${mission.claimed ? 'text-gray-600 line-through' : 'text-white'}`}>
          {mission.label}
        </p>
        <p className="text-[10px] text-gray-600 mt-0.5">{mission.desc}</p>
        {!mission.completed && (
          <div className="mt-1.5">
            <div className="h-0.5 bg-gray-800 rounded-full overflow-hidden">
              <div className="h-full rounded-full bg-accent-blue transition-all duration-500"
                style={{ width: `${pct}%` }} />
            </div>
            <p className="text-[9px] text-gray-700 mt-0.5">{mission.progress}/{mission.target}</p>
          </div>
        )}
      </div>

      {/* Récompense + bouton */}
      <div className="text-right shrink-0">
        <div className="text-[10px] text-gray-500 mb-1">
          {Object.entries(reward).map(([k, v]) => (
            <span key={k} className="block">{k === 'metal' ? '⛏️' : k === 'crystal' ? '💎' : '⚗️'} {fmt(v)}</span>
          ))}
        </div>
        {mission.completed && !mission.claimed && (
          <button
            onClick={() => onClaim(mission.id)}
            className="px-3 py-1 rounded-lg text-[10px] font-display tracking-wider transition-all"
            style={{ background: 'linear-gradient(135deg, #2d7dd2, #7c3aed)', color: 'white', boxShadow: '0 0 10px rgba(45,125,210,0.3)' }}>
            RÉCLAMER
          </button>
        )}
      </div>
    </div>
  )
}

// ─── Panel principal ──────────────────────────────────────────────────────────
export function DailyPanel({ compact = false }: { compact?: boolean }) {
  const qc = useQueryClient()

  const { data: status, isLoading } = useQuery({
    queryKey: ['daily', 'status'],
    queryFn: () => api.get<DailyStatus>('/daily/status'),
    refetchInterval: 60_000,
  })

  const { mutate: claimLogin, isPending: claimingLogin } = useMutation({
    mutationFn: () => api.post<LoginReward>('/daily/login', {}),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['daily'] })
      qc.invalidateQueries({ queryKey: ['planets'] })
      toast.success(res.message, {
        duration: 6000,
        icon: res.streak === 7 ? '🎉' : '⚡',
      })
    },
    onError: (err) => toast.error(err instanceof ApiError ? err.detail : 'Erreur'),
  })

  const { mutate: claimMission } = useMutation({
    mutationFn: (missionId: string) => api.post(`/daily/missions/${missionId}/claim`, {}),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['daily'] })
      qc.invalidateQueries({ queryKey: ['planets'] })
      toast.success('Mission accomplie ! Ressources ajoutées.', { icon: '🎁' })
    },
    onError: (err) => toast.error(err instanceof ApiError ? err.detail : 'Erreur'),
  })

  if (isLoading) return null

  if (!status) return null

  if (compact) {
    // Version compacte pour le dashboard
    const pendingMissions = status.missions.filter(m => m.completed && !m.claimed).length
    const totalCompleted  = status.missions.filter(m => m.completed).length
    return (
      <div className="panel cursor-pointer hover:bg-surface-elevated transition-colors"
        style={{ borderColor: status.can_claim_login ? 'rgba(45,125,210,0.4)' : 'rgba(35,50,70,0.4)' }}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl flex items-center justify-center text-xl"
              style={{ background: 'rgba(45,125,210,0.12)', border: '1px solid rgba(45,125,210,0.25)' }}>
              {status.can_claim_login ? '⚡' : '🔥'}
            </div>
            <div>
              <p className="text-sm font-semibold text-white">
                {status.can_claim_login ? 'Connexion quotidienne disponible !' : `Streak : ${status.streak} jour${status.streak > 1 ? 's' : ''}`}
              </p>
              <p className="text-[10px] text-gray-500">
                Missions : {totalCompleted}/3 — {pendingMissions > 0 ? `${pendingMissions} à réclamer !` : 'En cours...'}
              </p>
            </div>
          </div>
          {status.can_claim_login && (
            <button onClick={() => claimLogin()} disabled={claimingLogin}
              className="btn-primary text-xs py-1.5 px-3">
              Réclamer
            </button>
          )}
        </div>
      </div>
    )
  }

  // Version complète
  return (
    <div className="space-y-4">
      {/* Streak */}
      <div className="panel panel-glow">
        <div className="flex items-center justify-between mb-4">
          <div>
            <p className="section-title mb-1">Connexion quotidienne</p>
            <p className="text-white font-semibold">
              🔥 Streak : <span className="text-accent-blue font-display">{status.streak}</span> jour{status.streak > 1 ? 's' : ''}
            </p>
          </div>
          {status.can_claim_login && (
            <button onClick={() => claimLogin()} disabled={claimingLogin}
              className="btn-primary">
              ⚡ Réclamer
            </button>
          )}
        </div>
        <StreakWeek streak={status.streak} />
        {!status.can_claim_login && (
          <p className="text-[10px] text-gray-600 text-center mt-3">Revenez demain pour continuer votre streak !</p>
        )}
      </div>

      {/* Gains hors-ligne */}
      {status.offline_gains && Object.keys(status.offline_gains).length > 0 && (
        <div className="panel" style={{ borderColor: 'rgba(16,185,129,0.3)', background: 'rgba(16,185,129,0.05)' }}>
          <p className="text-sm font-semibold text-green-400 mb-2">💰 Ressources accumulées pendant votre absence</p>
          <div className="flex gap-4 text-sm">
            {status.offline_gains.metal     && <span className="text-gray-300">⛏️ +{fmt(status.offline_gains.metal)}</span>}
            {status.offline_gains.crystal   && <span className="text-gray-300">💎 +{fmt(status.offline_gains.crystal)}</span>}
            {status.offline_gains.deuterium && <span className="text-gray-300">⚗️ +{fmt(status.offline_gains.deuterium)}</span>}
          </div>
        </div>
      )}

      {/* Missions */}
      <div>
        <p className="section-title mb-3">Missions journalières</p>
        <div className="space-y-2">
          {status.missions.map(m => (
            <MissionRow key={m.id} mission={m} onClaim={claimMission} />
          ))}
        </div>
        <p className="text-[10px] text-gray-700 text-center mt-3">Nouvelles missions à minuit UTC</p>
      </div>
    </div>
  )
}
