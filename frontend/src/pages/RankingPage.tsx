// src/pages/RankingPage.tsx
import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { rankingApi } from '@/api'
import { LoadingSpinner, EmptyState } from '@/components/ui'
import { fmt } from '@/lib/utils'
import { useAuthStore } from '@/stores/authStore'

export function RankingPage() {
  const { playerId } = useAuthStore()

  const { data: ranking, isLoading } = useQuery({
    queryKey: ['ranking'],
    queryFn: () => rankingApi.list(100),
    refetchInterval: 60_000,
  })

  const { data: myRank } = useQuery({
    queryKey: ['ranking', 'me'],
    queryFn: rankingApi.me,
    enabled: !!playerId,
  })

  if (isLoading) return <div className="flex justify-center py-20"><LoadingSpinner size="lg" /></div>

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-white">🏆 Classement</h1>
        <p className="text-sm text-gray-400 mt-0.5">Mis à jour toutes les 10 minutes</p>
      </div>

      {/* Mon rang */}
      {myRank && (
        <div className="panel border border-accent-blue/30 bg-accent-blue/5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-gray-400">Votre position</p>
              <p className="text-2xl font-bold text-accent-blue">#{myRank.rank}</p>
            </div>
            <div className="text-right">
              <p className="text-xs text-gray-400">Score</p>
              <p className="text-lg font-mono text-white">{fmt(myRank.score)}</p>
            </div>
          </div>
        </div>
      )}

      {/* Tableau */}
      {!ranking || ranking.length === 0 ? (
        <EmptyState icon="🏆" title="Aucun joueur classé" />
      ) : (
        <div className="panel overflow-hidden p-0">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-surface-border">
                <th className="text-left text-xs text-gray-500 font-medium px-4 py-3">#</th>
                <th className="text-left text-xs text-gray-500 font-medium px-4 py-3">Commandant</th>
                <th className="text-left text-xs text-gray-500 font-medium px-4 py-3 hidden sm:table-cell">Alliance</th>
                <th className="text-right text-xs text-gray-500 font-medium px-4 py-3">Score</th>
              </tr>
            </thead>
            <tbody>
              {ranking.map((entry) => {
                const isMe = entry.player_id === playerId
                return (
                  <tr
                    key={entry.player_id}
                    className={`border-b border-surface-border/50 last:border-0 ${
                      isMe ? 'bg-accent-blue/10' : 'hover:bg-surface-tertiary transition-colors'
                    }`}
                  >
                    <td className="px-4 py-3">
                      <span className={`font-mono font-bold ${
                        entry.rank === 1 ? 'text-yellow-400' :
                        entry.rank === 2 ? 'text-gray-300' :
                        entry.rank === 3 ? 'text-amber-600' : 'text-gray-500'
                      }`}>
                        {entry.rank === 1 ? '🥇' : entry.rank === 2 ? '🥈' : entry.rank === 3 ? '🥉' : `#${entry.rank}`}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`font-medium ${isMe ? 'text-accent-blue' : 'text-white'}`}>
                        {entry.username}{isMe && ' (vous)'}
                      </span>
                    </td>
                    <td className="px-4 py-3 hidden sm:table-cell text-gray-500">
                      {entry.alliance_tag ?? '—'}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-white">
                      {fmt(entry.score)}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
