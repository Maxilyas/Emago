/**
 * stores/gameStore.ts — v2
 * Agent 6 — Développeur Frontend | Sprint 3
 *
 * Ajouts Sprint 3 :
 *   - notifications[] : pile de notifications WS (max 50)
 *   - addNotification / markAllRead / clearNotifications
 */
import { create } from 'zustand'

interface Notification {
  id: string
  type: string
  title: string
  message: string
  timestamp: Date
  read: boolean
  data?: unknown
}

interface GameState {
  // Ressources actives (mise à jour par WebSocket / polling)
  activeResources: {
    metal: number
    crystal: number
    deuterium: number
    planetId: string | null
    updatedAt: Date | null
  }

  // Notifications WebSocket
  notifications: Notification[]

  // Actions
  setActiveResources: (r: Partial<GameState['activeResources']>) => void
  addNotification: (n: Notification) => void
  markAllRead: () => void
  clearNotifications: () => void
}

export const useGameStore = create<GameState>((set) => ({
  activeResources: {
    metal: 0,
    crystal: 0,
    deuterium: 0,
    planetId: null,
    updatedAt: null,
  },

  notifications: [],

  setActiveResources: (r) =>
    set((s) => ({
      activeResources: { ...s.activeResources, ...r, updatedAt: new Date() },
    })),

  addNotification: (n) =>
    set((s) => ({
      // Garder max 50 notifications (FIFO)
      notifications: [n, ...s.notifications].slice(0, 50),
    })),

  markAllRead: () =>
    set((s) => ({
      notifications: s.notifications.map((n) => ({ ...n, read: true })),
    })),

  clearNotifications: () => set({ notifications: [] }),
}))
