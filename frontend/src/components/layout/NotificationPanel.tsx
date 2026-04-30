import React from 'react'
import { useGameStore } from '@/stores/gameStore'
import { timeAgo } from '@/lib/utils'

export function NotificationPanel({ onClose }: { onClose: () => void }) {
  const { notifications, dismissNotification, clearNotifications } = useGameStore()

  return (
    <div className="panel w-full shadow-2xl animate-slide-up">
      <div className="flex items-center justify-between mb-3">
        <h2 className="font-semibold text-sm">Notifications</h2>
        <div className="flex gap-2">
          {notifications.length > 0 && (
            <button onClick={clearNotifications} className="text-xs text-gray-500 hover:text-red-400 transition-colors">
              Tout effacer
            </button>
          )}
          <button onClick={onClose} className="text-gray-400 hover:text-white">×</button>
        </div>
      </div>

      {notifications.length === 0 ? (
        <p className="text-sm text-gray-500 text-center py-6">Aucune notification</p>
      ) : (
        <div className="space-y-2 max-h-80 overflow-y-auto">
          {notifications.map((n) => (
            <div key={n.id} className="flex gap-3 p-2 bg-surface-tertiary rounded-lg group">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-white leading-tight">{n.title}</p>
                <p className="text-xs text-gray-400 mt-0.5 truncate">{n.message}</p>
                <p className="text-xs text-gray-600 mt-1">{timeAgo(new Date(n.timestamp).toISOString())}</p>
              </div>
              <button
                onClick={() => dismissNotification(n.id)}
                className="text-gray-600 hover:text-white opacity-0 group-hover:opacity-100 transition-opacity"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
