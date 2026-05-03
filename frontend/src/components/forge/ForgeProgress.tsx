/**
 * ForgeProgress — affiche l'avancement d'une opération de forge.
 * Le countdown est calculé depuis completed_at (timestamp absolu) pour rester
 * correct après un refresh — eta_seconds du serveur est figé à la création.
 */
import React from 'react'
import { ProgressBar } from '@/components/ui'
import { fmtCountdown, fmtDate } from '@/lib/utils'
import type { ForgeStatusResponse } from '@/types'

const FORGE_TOTAL_SECONDS = 8 * 3600

interface Props {
  forge: ForgeStatusResponse
  onComplete?: () => void
}

export function ForgeProgress({ forge, onComplete }: Props) {
  const [remaining, setRemaining] = React.useState(() =>
    Math.max(0, Math.round((new Date(forge.completed_at).getTime() - Date.now()) / 1000)),
  )
  const completedRef = React.useRef(false)

  React.useEffect(() => {
    completedRef.current = false
    const tick = () => {
      const left = Math.max(0, Math.round((new Date(forge.completed_at).getTime() - Date.now()) / 1000))
      setRemaining(left)
      if (left <= 0 && !completedRef.current) {
        completedRef.current = true
        onComplete?.()
      }
    }
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [forge.completed_at]) // eslint-disable-line react-hooks/exhaustive-deps

  const isComplete = !!forge.result_ship_id || remaining <= 0
  const pct = isComplete
    ? 100
    : Math.round(Math.max(0, Math.min(100, ((FORGE_TOTAL_SECONDS - remaining) / FORGE_TOTAL_SECONDS) * 100)))

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
