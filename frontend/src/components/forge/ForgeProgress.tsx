/**
 * ForgeProgress — affiche l'avancement d'une opération de forge.
 * Le countdown s'interpole côté client mais GET /forge/:id reste la vérité.
 */
import React from 'react'
import { useCountdown } from '@/hooks/useCountdown'
import { ProgressBar } from '@/components/ui'
import { fmtCountdown, fmtDate } from '@/lib/utils'
import type { ForgeStatusResponse } from '@/types'

interface Props {
  forge: ForgeStatusResponse
  onComplete?: () => void
}

export function ForgeProgress({ forge, onComplete }: Props) {
  const { remaining, pct, done } = useCountdown(forge.eta_seconds, onComplete)
  const isComplete = forge.is_completed ?? done

  return (
    <div className="panel space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xl">🔨</span>
          <div>
            <p className="font-semibold text-sm">
              {isComplete ? 'Forge terminée !' : 'Forge en cours…'}
            </p>
            <p className="text-xs text-gray-500">
              Fin prévue : {fmtDate(forge.completed_at)}
            </p>
          </div>
        </div>
        <span className={`text-sm font-mono ${isComplete ? 'text-green-400' : 'text-orange-400'}`}>
          {isComplete ? '✓ Terminée' : fmtCountdown(remaining)}
        </span>
      </div>

      <ProgressBar
        value={isComplete ? 100 : pct}
        max={100}
        color={isComplete ? '#4CAF50' : '#f97316'}
        animated={!isComplete}
      />

      <p className="text-xs text-gray-500 text-right">{isComplete ? 100 : pct}% — Durée totale : 8 heures</p>
    </div>
  )
}
