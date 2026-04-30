// ============================================================
// Types Emago — calés 1:1 sur FRONTEND_SPEC.md
// ============================================================

// Auth
export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: 'bearer'
}

// Rareté & Grade
export type Rarity = 'COMMON' | 'UNCOMMON' | 'RARE' | 'EPIC' | 'LEGENDARY'
export type ShipClass = 'ATTACK' | 'DEFENSE' | 'SUPPORT' | 'EXPLORATION'
export type ShipStatus = 'DOCKED' | 'IN_FLEET' | 'IN_FORGE'
export type ModuleType = 'PROPELLER' | 'ARMOR' | 'CANNON' | 'EMITTER' | 'SHIELD' | 'CARGO'
export type FleetMission = 'ATTACK' | 'TRANSPORT' | 'ESPIONAGE' | 'COLONIZE' | 'RECALL'

export type ShipType =
  | 'frigate_attack' | 'frigate_defense' | 'frigate_support'
  | 'frigate_exploration' | 'cruiser_attack' | 'cruiser_defense'

// Stats
export interface BaseStats {
  hull: number
  shield: number
  dps: number
  speed: number
  cargo: number
  stealth: number
  support_aura: number
}

export interface ModuleDetail {
  slot: number
  type: ModuleType
  level: 1 | 2 | 3 | 4 | 5
  affinity_bonus: boolean
  boost_applied: number
}

export interface CurrentStats extends BaseStats {
  grade: number
  grade_bonus_pct: number
  shield_regen_per_round: number
  cap_reached: string[]
  modules: ModuleDetail[]
  slots_total: number
  slots_premium: number
}

// Vaisseaux
export interface ShipSummary {
  id: string
  ship_type: ShipType
  ship_class: ShipClass
  rarity: Rarity
  grade: number
  status: ShipStatus
  planet_id: string | null
}

export interface ShipDetail {
  id: string
  ship_type: ShipType
  ship_class: ShipClass
  rarity: Rarity
  grade: number
  combat_xp: number
  status: ShipStatus
  parent_ship_id: string | null
  base_stats: BaseStats
  current_stats: CurrentStats
}

export interface BuildShipRequest {
  ship_type: ShipType
  planet_id: string
  parent_ship_id?: string | null
}

export interface BuildShipResponse {
  ship_id: string
  rarity: Rarity
  ship_class: ShipClass
  base_stats: BaseStats
  slots_total: number
  slots_premium: number
  pedigree_applied: boolean
}

// Modules
export interface ModuleSlot {
  slot: number
  type: ModuleType
  level: number
  affinity_bonus: boolean
}

export interface InstallModuleRequest {
  module_type: ModuleType
  level: 1 | 2 | 3 | 4 | 5
}

// Forge
export interface ForgeStatusResponse {
  forge_id: string
  completed_at: string
  progress_pct: number
  eta_seconds: number
  result_ship_id?: string | null
}

export interface ForgeHistoryItem {
  forge_id: string
  ship_a_id: string
  ship_b_id: string
  result_ship_id: string | null
  started_at: string
  completed_at: string
  is_completed: boolean
}

// Planètes
export interface PlanetSummary {
  id: string
  name: string
  galaxy: number
  system: number
  position: number
  is_homeworld: boolean
  metal: number
  crystal: number
  deuterium: number
}

export interface ProductionRates {
  metal_per_hour: number
  crystal_per_hour: number
  deuterium_per_hour: number
  energy_produced: number
  energy_factor: number
}

export interface PlanetDetail extends PlanetSummary {
  metal_capacity: number
  crystal_capacity: number
  deut_capacity: number
  buildings: Record<string, number>
  production_rates: ProductionRates
  resources_last_updated_at: string
}

// Flottes
export interface FleetResponse {
  fleet_id: string
  mission: FleetMission
  origin_planet_id: string
  target_galaxy: number
  target_system: number
  target_position: number
  departed_at: string
  arrives_at: string
  ship_count: number
}

// Classement
export interface RankingEntry {
  rank: number
  player_id: string
  username: string
  score: number
  alliance_tag: string | null
}

// WebSocket events
export interface WsEvent<T = unknown> {
  type: string
  data: T
}

export interface ForgeCompleteData {
  forge_id: string
  new_ship_id: string
  rarity: Rarity
  base_stats: BaseStats
  combat_xp: number
  slots_total: number
  slots_premium: number
}

export interface CombatResultData {
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

export interface GradeUpData {
  ship_id: string
  owner_id: string
  old_grade: number
  new_grade: number
  combat_xp: number
}

export interface ScarEarnedData {
  ship_id: string
  owner_id: string
  tag: string
}

export interface FleetArrivedData {
  fleet_id: string
  mission: FleetMission
  target_planet_id: string | null
}

// Config UI
export const RARITY_CONFIG: Record<Rarity, { color: string; label: string; tw: string }> = {
  COMMON:    { color: '#9E9E9E', label: 'Commun',     tw: 'text-gray-400 border-gray-500' },
  UNCOMMON:  { color: '#4CAF50', label: 'Peu commun', tw: 'text-green-400 border-green-500' },
  RARE:      { color: '#2196F3', label: 'Rare',       tw: 'text-blue-400 border-blue-500' },
  EPIC:      { color: '#9C27B0', label: 'Épique',     tw: 'text-purple-400 border-purple-500' },
  LEGENDARY: { color: '#FFD700', label: 'Légendaire', tw: 'text-yellow-400 border-yellow-400' },
}

export const GRADE_CONFIG: Record<number, { name: string; xp: number }> = {
  0: { name: 'Recrue',   xp: 0 },
  1: { name: 'Vétéran',  xp: 500 },
  2: { name: 'Élite',    xp: 2000 },
  3: { name: 'Légion',   xp: 6000 },
  4: { name: 'Légende',  xp: 15000 },
  5: { name: 'Spectre',  xp: 40000 },
}

export const SHIP_TYPE_CONFIG: Record<ShipType, { label: string; icon: string; class: ShipClass }> = {
  frigate_attack:      { label: 'Frégate Attaque',     icon: '⚔️', class: 'ATTACK' },
  frigate_defense:     { label: 'Frégate Défense',     icon: '🛡️', class: 'DEFENSE' },
  frigate_support:     { label: 'Frégate Soutien',     icon: '💊', class: 'SUPPORT' },
  frigate_exploration: { label: 'Frégate Exploration', icon: '🔭', class: 'EXPLORATION' },
  cruiser_attack:      { label: 'Croiseur Attaque',    icon: '⚔️', class: 'ATTACK' },
  cruiser_defense:     { label: 'Croiseur Défense',    icon: '🛡️', class: 'DEFENSE' },
}

export const MODULE_CONFIG: Record<ModuleType, { label: string; stat: string; icon: string }> = {
  PROPELLER: { label: 'Propulseur',      stat: 'speed',        icon: '🚀' },
  ARMOR:     { label: 'Blindage',        stat: 'hull',         icon: '🔩' },
  CANNON:    { label: 'Canon',           stat: 'dps',          icon: '💥' },
  EMITTER:   { label: 'Émetteur',        stat: 'support_aura', icon: '📡' },
  SHIELD:    { label: 'Bouclier',        stat: 'shield',       icon: '🛡️' },
  CARGO:     { label: 'Cargo amélioré', stat: 'cargo',        icon: '📦' },
}

export const FORGE_COSTS: Record<ShipType, { metal: number; crystal: number; deuterium: number }> = {
  frigate_attack:      { metal: 9000,  crystal: 3000,  deuterium: 0 },
  frigate_defense:     { metal: 18000, crystal: 6000,  deuterium: 0 },
  frigate_support:     { metal: 6000,  crystal: 6000,  deuterium: 1500 },
  frigate_exploration: { metal: 6000,  crystal: 3000,  deuterium: 3000 },
  cruiser_attack:      { metal: 60000, crystal: 21000, deuterium: 6000 },
  cruiser_defense:     { metal: 90000, crystal: 30000, deuterium: 6000 },
}

// XP nécessaire pour le prochain grade
export function xpForNextGrade(currentGrade: number): number | null {
  const next = GRADE_CONFIG[currentGrade + 1]
  return next ? next.xp : null
}
