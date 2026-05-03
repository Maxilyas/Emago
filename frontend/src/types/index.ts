// ============================================================
// Types Emago — v1.1
// Ajouts RPG : ShipTrait, champs name/trait/is_drift,
//              ForgeCompleteData enrichi, ForgeCompleteEvent
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

// ── Trait narratif RPG v1.1 ──────────────────────────────────────────────────
export interface ShipTrait {
  key: string
  name: string
  description: string
}

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
  // Phase 3
  trait: string | null
  is_corrupted: boolean
  player_module_id?: string
  reinstall_charges?: number
}

export interface CurrentStats extends BaseStats {
  grade: number
  grade_bonus_pct: number
  shield_regen_per_round: number
  cap_reached: string[]
  modules: ModuleDetail[]
  slots_total: number
  slots_premium: number
  // Phase 3 — doctrines & résonances
  doctrine: string | null
  doctrine_active: boolean
  resonances: string[]
  evasion_chance: number
  damage_reduction: number
  riposte_chance: number
}

// ── Inventaire de modules (Phase 3) ─────────────────────────────────────────
export type ModuleObtainedFrom = 'EXPEDITION' | 'COMBAT_LOOT' | 'CRAFTED' | 'DAILY_REWARD'
export type LootCrateType = 'STANDARD' | 'PREMIUM' | 'ADMIRAL'

export interface PlayerModule {
  id: string
  module_type: ModuleType
  level: 1 | 2 | 3 | 4 | 5
  trait: string | null
  trait_value: number | null
  bonus_trait: string | null
  bonus_trait_2: string | null
  is_corrupted: boolean
  corruption_malus_stat: string | null
  corruption_malus_value: number | null
  reinstall_charges: number
  is_destroyed: boolean
  obtained_from: ModuleObtainedFrom
  memory_ship_name: string | null
  obtained_at: string
}

export interface LootCrate {
  id: string
  crate_type: LootCrateType
  source: string
  source_ship_name: string | null
  obtained_at: string
}

export interface LootCrateOpenResult {
  crate_id: string
  module: PlayerModule | null
  shards: Record<string, number>
  empty: boolean
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
  // ── Champs RPG v1.1 ──
  name: string | null       // "Astraeus Noir" ou null (COMMON/UNCOMMON)
  trait: ShipTrait | null   // null pour les vaisseaux antérieurs à migration 0006
  is_drift: boolean         // true = issu d'une Forge Dérive
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
  current_stats: CurrentStats  // NE JAMAIS calculer côté client
  // ── Champs RPG v1.1 ──
  name: string | null
  trait: ShipTrait | null
  is_drift: boolean
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
  // ── Champs RPG v1.1 ──
  trait: ShipTrait
  name: string | null
  is_drift: boolean
}

// Modules
export interface ModuleSlot {
  slot: number
  type: ModuleType
  level: number
  affinity_bonus: boolean
}

export interface InstallModuleRequest {
  module_id: string
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

// ── WebSocket events ─────────────────────────────────────────────────────────

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
  // ── Champs RPG v1.1 ──
  trait: ShipTrait | null
  name: string | null
  is_drift: boolean
}

/** Alias typé pour l'event WS forge.complete — utilisé dans NotificationPanel */
export interface ForgeCompleteEvent {
  type: 'forge.complete'
  data: ForgeCompleteData
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

// ── Config UI ────────────────────────────────────────────────────────────────

export const RARITY_CONFIG: Record<Rarity, { color: string; label: string; tw: string }> = {
  COMMON:    { color: '#9E9E9E', label: 'Commun',     tw: 'text-gray-400 border-gray-500' },
  UNCOMMON:  { color: '#4CAF50', label: 'Peu commun', tw: 'text-green-400 border-green-500' },
  RARE:      { color: '#2196F3', label: 'Rare',       tw: 'text-blue-400 border-blue-500' },
  EPIC:      { color: '#9C27B0', label: 'Épique',     tw: 'text-purple-400 border-purple-500' },
  LEGENDARY: { color: '#FFD700', label: 'Légendaire', tw: 'text-yellow-400 border-yellow-400' },
}

export const GRADE_CONFIG: Record<number, { name: string; xp: number }> = {
  0: { name: 'Recrue',  xp: 0 },
  1: { name: 'Vétéran', xp: 500 },
  2: { name: 'Élite',   xp: 2000 },
  3: { name: 'Légion',  xp: 6000 },
  4: { name: 'Légende', xp: 15000 },
  5: { name: 'Spectre', xp: 40000 },
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
  CARGO:     { label: 'Cargo amélioré',  stat: 'cargo',        icon: '📦' },
}

export const FORGE_COSTS: Record<ShipType, { metal: number; crystal: number; deuterium: number }> = {
  frigate_attack:      { metal: 9000,  crystal: 3000,  deuterium: 0 },
  frigate_defense:     { metal: 18000, crystal: 6000,  deuterium: 0 },
  frigate_support:     { metal: 6000,  crystal: 6000,  deuterium: 1500 },
  frigate_exploration: { metal: 6000,  crystal: 3000,  deuterium: 3000 },
  cruiser_attack:      { metal: 60000, crystal: 21000, deuterium: 6000 },
  cruiser_defense:     { metal: 90000, crystal: 30000, deuterium: 6000 },
}

export const DOCTRINE_CONFIG: Record<string, {
  label: string; icon: string; color: string; description: string
  module_type: ModuleType; effects: Array<{ text: string; positive: boolean }>
}> = {
  BERSERKER: {
    label: 'Berserker', icon: '⚔️', color: '#ef4444',
    description: '+20% DPS · −25% bouclier',
    module_type: 'CANNON',
    effects: [
      { text: '+20% DPS', positive: true },
      { text: '−25% Bouclier', positive: false },
    ],
  },
  FORTERESSE: {
    label: 'Forteresse', icon: '🏰', color: '#3b82f6',
    description: '−40% vitesse · 50% réd. dégâts',
    module_type: 'ARMOR',
    effects: [
      { text: '50% réduction des dégâts', positive: true },
      { text: '−40% Vitesse', positive: false },
    ],
  },
  FANTOME: {
    label: 'Fantôme', icon: '👻', color: '#8b5cf6',
    description: '15% évasion · cargo = 0',
    module_type: 'PROPELLER',
    effects: [
      { text: '15% chance d\'esquive', positive: true },
      { text: 'Cargo annulé (= 0)', positive: false },
    ],
  },
  AMPLIFICATEUR: {
    label: 'Amplificateur', icon: '📡', color: '#22d3ee',
    description: '×2 aura soutien · −30% DPS',
    module_type: 'EMITTER',
    effects: [
      { text: '×2 Aura de soutien', positive: true },
      { text: '−30% DPS', positive: false },
    ],
  },
}

export const RESONANCE_CONFIG: Record<string, { label: string; icon: string; description: string }> = {
  BASTION:    { label: 'Bastion',    icon: '🔒', description: 'BLINDAGE + BOUCLIER — boosts ×1.10' },
  RIPOSTE:    { label: 'Riposte',   icon: '⚡', description: 'CANON + BOUCLIER — 5 % contre-tir' },
  VELOCITE:   { label: 'Vélocité',  icon: '🚀', description: 'PROPULSEUR + CARGO — boosts ×1.10' },
  OVERCHARGE: { label: 'Surcharge', icon: '💥', description: 'CANON + ÉMETTEUR — boosts ×1.10' },
}

export const TRAIT_CONFIG: Record<string, { label: string; color: string; description: string }> = {
  battle_hardened: {
    label: 'Endurci au combat', color: '#f97316',
    description: '+10% au boost de base — forgé dans les combats, chaque installation renforce sa résistance.',
  },
  overclocked: {
    label: 'Surcadencé', color: '#eab308',
    description: '+15% au boost de base, mais la surchauffe use le module : −1 charge de réinstallation.',
  },
  pristine: {
    label: 'Pristine', color: '#22d3ee',
    description: 'Entretenu à la perfection. +2 charges de réinstallation supplémentaires.',
  },
  resonant: {
    label: 'Résonant', color: '#a78bfa',
    description: 'Répond à une fréquence secondaire : active le bonus d\'affinité d\'une 2ᵉ classe (+15% de boost).',
  },
  lightweight: {
    label: 'Allégé', color: '#4ade80',
    description: 'Construction allégée. +5% au boost de base + bonus de vitesse additionnel (+3% absolu).',
  },
  military_grade: {
    label: 'Grade militaire', color: '#ef4444',
    description: 'Fabrication militaire haut de gamme. +12% au boost de base — réservé aux modules niveau III+.',
  },
}

// Coûts d'artisanat (niveau résultant) → [primary, secondary, deuterium]
export const CRAFT_COST: Record<number, [number, number, number]> = {
  2: [500,    150,     0],
  3: [1_500,  500,     0],
  4: [4_500,  1_500,  500],
  5: [12_000, 4_000, 1_500],
}

// Ressource primaire et secondaire par type de module
export const MODULE_PRIMARY_RESOURCE: Record<ModuleType, string> = {
  CANNON:    'crystal',
  SHIELD:    'crystal',
  ARMOR:     'metal',
  PROPELLER: 'metal',
  EMITTER:   'deuterium',
  CARGO:     'deuterium',
}

export const MODULE_SECONDARY_RESOURCE: Record<ModuleType, string> = {
  CANNON:    'metal',
  SHIELD:    'metal',
  ARMOR:     'crystal',
  PROPELLER: 'crystal',
  EMITTER:   'metal',
  CARGO:     'crystal',
}

export const RESOURCE_CONFIG: Record<string, { label: string; icon: string; color: string }> = {
  metal:     { label: 'Métal',     icon: '⛏️',  color: '#9ca3af' },
  crystal:   { label: 'Cristal',   icon: '💎',  color: '#60a5fa' },
  deuterium: { label: 'Deutérium', icon: '⚗️',  color: '#34d399' },
}

export const LOOT_CRATE_CONFIG: Record<LootCrateType, { label: string; icon: string; color: string; glow: string }> = {
  STANDARD: { label: 'Caisse Standard', icon: '📦', color: '#6b7280', glow: 'rgba(107,114,128,0.4)' },
  PREMIUM:  { label: 'Caisse Premium',  icon: '💎', color: '#a78bfa', glow: 'rgba(167,139,250,0.5)' },
  ADMIRAL:  { label: 'Caisse Amiral',   icon: '👑', color: '#ffd700', glow: 'rgba(255,215,0,0.6)' },
}

// XP nécessaire pour le prochain grade
export function xpForNextGrade(currentGrade: number): number | null {
  const next = GRADE_CONFIG[currentGrade + 1]
  return next ? next.xp : null
}