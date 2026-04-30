import { create } from 'zustand'
import type { CombatResultData, ForgeCompleteData, GradeUpData, ScarEarnedData } from '@/types'

interface Notification {
  id: string
  type: 'combat' | 'forge' | 'grade_up' | 'scar' | 'fleet'
  title: string
  message: string
  timestamp: number
  data?: unknown
}

interface GameState {
  wsConnected: boolean
  notifications: Notification[]
  pendingCombatResult: CombatResultData | null
  setWsConnected: (v: boolean) => void
  addNotification: (n: Omit<Notification, 'id' | 'timestamp'>) => void
  dismissNotification: (id: string) => void
  clearNotifications: () => void
  setPendingCombatResult: (data: CombatResultData | null) => void
}

let notifCounter = 0

export const useGameStore = create<GameState>((set) => ({
  wsConnected: false,
  notifications: [],
  pendingCombatResult: null,

  setWsConnected: (v) => set({ wsConnected: v }),

  addNotification: (n) =>
    set((state) => ({
      notifications: [
        {
          ...n,
          id: `notif-${++notifCounter}`,
          timestamp: Date.now(),
        },
        ...state.notifications.slice(0, 19), // max 20 notifs
      ],
    })),

  dismissNotification: (id) =>
    set((state) => ({
      notifications: state.notifications.filter((n) => n.id !== id),
    })),

  clearNotifications: () => set({ notifications: [] }),

  setPendingCombatResult: (data) => set({ pendingCombatResult: data }),
}))
