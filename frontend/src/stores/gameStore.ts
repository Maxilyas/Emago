/**
 * stores/gameStore.ts — v1.1
 * Agent 6 — Développeur Frontend | Sprint RPG
 *
 * Ajouts v1.1 :
 *   - pendingCombatResult   : déjà présent (inchangé)
 *   - spectreData           : NOUVEAU — déclenche SpectreAwakening quand grade_up → 5
 *   - pendingForgeResult    : NOUVEAU — stocke le résultat forge.complete pour
 *                             afficher un toast enrichi (nom, Dérive) depuis AppLayout
 *
 * Architecture : les overlays fullscreen (CombatReport, SpectreAwakening) sont montés
 * dans AppLayout pour être disponibles sur toutes les routes. Le store est le canal
 * de communication entre useWsEventHandlers (NotificationPanel) et AppLayout.
 */
import { create } from 'zustand'
import type { SpectreAwakeningData } from '@/components/ships/SpectreAwakening'

// ─── Types ────────────────────────────────────────────────────────────────────

interface Notification {
  id: string
  type: string
  title: string
  message: string
  timestamp: Date
  read: boolean
  data?: unknown
}

/** Données minimales du résultat forge stockées pour l'affichage AppLayout */
export interface PendingForgeResult {
  forge_id: string
  new_ship_id: string
  rarity: string
  name: string | null
  is_drift: boolean
  trait: { key: string; name: string; description: string } | null
}

/** État complet d'un rapport de combat (existant — inchangé) */
export interface PendingCombatResult {
  combat_id: string
  winner: 'ATTACKER' | 'DEFENDER' | 'DRAW'
  total_rounds: number
  attacker_power: number
  defender_power: number
  ships_lost: { attacker: string[]; defender: string[] }
  xp_diff: Record<string, number>
  loot: { metal?: number; crystal?: number; deuterium?: number }
  grade_ups: Array<{ ship_id: string; owner_id: string; old_grade: number; new_grade: number; combat_xp: number }>
  scars: Array<{ ship_id: string; owner_id: string; tag: string }>
  synergies: { attacker: string[]; defender: string[] }
}

interface GameState {
  // Connexion WebSocket
  wsConnected: boolean

  // Planète active pour la barre de ressources persistante
  activePlanetId: string | null

  // Ressources actives
  activeResources: {
    metal: number
    crystal: number
    deuterium: number
    planetId: string | null
    updatedAt: Date | null
  }

  // Overlays WS
  pendingCombatResult: PendingCombatResult | null
  spectreData: SpectreAwakeningData | null
  pendingForgeResult: PendingForgeResult | null

  // Notifications
  notifications: Notification[]

  // Actions
  setActivePlanetId: (id: string) => void
  setActiveResources: (r: Partial<GameState['activeResources']>) => void
  setPendingCombatResult: (d: PendingCombatResult | null) => void
  setWsConnected: (v: boolean) => void
  setSpectreData: (d: SpectreAwakeningData | null) => void
  setPendingForgeResult: (d: PendingForgeResult | null) => void
  addNotification: (n: Notification) => void
  markAllRead: () => void
  clearNotifications: () => void
}

// ─── Store ────────────────────────────────────────────────────────────────────

export const useGameStore = create<GameState>((set) => ({
  wsConnected: false,

  activePlanetId: null,

  activeResources: {
    metal: 0,
    crystal: 0,
    deuterium: 0,
    planetId: null,
    updatedAt: null,
  },

  pendingCombatResult: null,
  spectreData:         null,    // ← NOUVEAU
  pendingForgeResult:  null,    // ← NOUVEAU

  notifications: [],

  setActiveResources: (r) =>
    set((s) => ({
      activeResources: { ...s.activeResources, ...r, updatedAt: new Date() },
    })),

  setActivePlanetId:      (id) => set({ activePlanetId: id }),
  setPendingCombatResult: (d) => set({ pendingCombatResult: d }),
  setWsConnected:         (v) => set({ wsConnected: v }),
  setSpectreData:         (d) => set({ spectreData: d }),          // ← NOUVEAU
  setPendingForgeResult:  (d) => set({ pendingForgeResult: d }),   // ← NOUVEAU

  addNotification: (n) =>
    set((s) => ({
      notifications: [n, ...s.notifications].slice(0, 50),
    })),

  markAllRead: () =>
    set((s) => ({
      notifications: s.notifications.map((n) => ({ ...n, read: true })),
    })),

  clearNotifications: () => set({ notifications: [] }),
}))