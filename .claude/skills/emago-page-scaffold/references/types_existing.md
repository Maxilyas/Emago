# Types globaux Emago — `frontend/src/types/index.ts`

Cheatsheet des types réutilisables. Toujours importer depuis `@/types` plutôt que redéfinir.

## Auth

```ts
TokenResponse  // { access_token, refresh_token, token_type: 'bearer' }
```

## Enums (literal unions)

```ts
Rarity        = 'COMMON' | 'UNCOMMON' | 'RARE' | 'EPIC' | 'LEGENDARY'
ShipClass     = 'ATTACK' | 'DEFENSE' | 'SUPPORT' | 'EXPLORATION'
ShipStatus    = 'DOCKED' | 'IN_FLEET' | 'IN_FORGE'
ModuleType    = 'PROPELLER' | 'ARMOR' | 'CANNON' | 'EMITTER' | 'SHIELD' | 'CARGO'
FleetMission  = 'ATTACK' | 'TRANSPORT' | 'ESPIONAGE' | 'COLONIZE' | 'RECALL'
ShipType      = 'frigate_attack' | 'frigate_defense' | 'frigate_support'
              | 'frigate_exploration' | 'cruiser_attack' | 'cruiser_defense'
```

## Ships

```ts
ShipTrait              // { key, name, description }
BaseStats              // { hull, shield, dps, speed, cargo, stealth, support_aura }
ModuleDetail           // { slot, type, level, affinity_bonus, boost_applied }
CurrentStats           // BaseStats + grade, grade_bonus_pct, shield_regen_per_round, cap_reached, modules, slots_total, slots_premium

ShipSummary            // id, ship_type, ship_class, rarity, grade, status, planet_id, name, trait, is_drift
ShipDetail             // ShipSummary + combat_xp, parent_ship_id, base_stats, current_stats

BuildShipRequest       // ship_type, planet_id, parent_ship_id?
BuildShipResponse      // ship_id, rarity, ship_class, base_stats, slots_total, slots_premium, pedigree_applied, trait, name, is_drift

ModuleSlot             // slot, type, level, affinity_bonus
InstallModuleRequest   // module_type, level (1-5)
ModuleInstallResponse  // current_stats, cap_reached
```

## Forge

```ts
ForgeStartRequest      // ship_a_id, ship_b_id
ForgeStatusResponse    // forge_id, completed_at, progress_pct, eta_seconds, result_ship_id?
ForgeHistoryItem       // forge_id, ship_a_id, ship_b_id, result_ship_id?, started_at, completed_at, is_completed
```

## Planets

```ts
PlanetSummary          // id, name, galaxy, system, position, is_homeworld, metal, crystal, deuterium
ProductionRates        // metal_per_hour, crystal_per_hour, deuterium_per_hour, energy_produced, energy_factor
PlanetDetail           // PlanetSummary + capacities, buildings, production_rates, resources_last_updated_at
```

## Fleets / Ranking

```ts
FleetResponse          // fleet_id, mission, origin_planet_id, target_*, departed_at, arrives_at, ship_count
RankingEntry           // rank, player_id, username, score, alliance_tag
```

## WebSocket events

```ts
WsEvent<T>             // { type: string, data: T }
ForgeCompleteData      // forge_id, new_ship_id, rarity, base_stats, combat_xp, slots_total, slots_premium, trait, name, is_drift
ForgeCompleteEvent     // { type: 'forge.complete', data: ForgeCompleteData }
CombatResultData       // combat_id, winner, total_rounds, attacker/defender_power, ships_lost, xp_diff, loot, grade_ups, scars, synergies
GradeUpData            // ship_id, owner_id, old_grade, new_grade, combat_xp
ScarEarnedData         // ship_id, owner_id, tag
FleetArrivedData       // fleet_id, mission, target_planet_id
```

## Constantes UI

```ts
RARITY_CONFIG[rarity]      // { color, label, tw }
GRADE_CONFIG[grade]        // { name, xp }
SHIP_TYPE_CONFIG[type]     // { icon, class }
MODULE_CONFIG[module]      // { stat, icon }
FORGE_COSTS[type]          // { metal, crystal, deuterium }

xpForNextGrade(grade)      // returns next grade XP threshold or null
```

## Helpers `@/lib/utils`

```ts
cn(...inputs)              // twMerge(clsx(...))
fmt(n, decimals=0)         // toLocaleString fr-FR
fmtShort(n)                // 1.5M / 1.2k / 123
fmtCountdown(seconds)      // HH:MM:SS
rarityColor(r)             // hex
rarityTw(r)                // Tailwind classes
rarityGlow(r)              // box-shadow string
timeAgo(dateStr)           // "il y a 2 heures"
fmtDate(dateStr)           // "01/05/2026 14:30"
xpProgress(currentXp, currentGrade)  // 0-100
clamp(val, min, max)
```

## Stores

```ts
// useAuthStore
{
  accessToken: string | null,
  refreshToken: string | null,
  playerId: string | null,
  username: string | null,
  setTokens(access, refresh): void,
  setPlayerId(id, username?): void,
  logout(): void,
  isAuthenticated(): boolean,
}

// useGameStore
{
  wsConnected: boolean,
  activeResources: { metal, crystal, deuterium, planetId, updatedAt },
  pendingCombatResult: PendingCombatResult | null,
  spectreData: SpectreAwakeningData | null,
  pendingForgeResult: PendingForgeResult | null,
  notifications: Notification[],
  setActiveResources(r): void,
  setPendingCombatResult(r): void,
  setWsConnected(b): void,
  setSpectreData(d): void,
  setPendingForgeResult(r): void,
  addNotification(n): void,
  markAllRead(): void,
  clearNotifications(): void,
}
```

## Hooks

```ts
useGameSocket()            // (instancié dans AppLayout — ne pas réinstancier)
useCountdown(eta_seconds, onComplete?)  // → { remaining, pct, done }
```

## Types à créer en Phase 2

Pour les nouvelles pages :

```ts
// Espionnage
type ProbeRequest = { target_planet_id: string; ship_ids: string[] }
type ProbeStatus = { probe_id: string; arrives_at: string; eta_seconds: number }
type EspionageReport = {
  report_id: string;
  target_username: string;
  target_planet: { galaxy, system, position, name };
  resources: { metal, crystal, deuterium };
  fleet?: ShipSummary[];
  buildings?: Record<string, number>;
  detected: boolean;
}

// Marché galactique
type MarketOffer = {
  offer_id: string;
  seller_id: string;
  seller_username: string;
  give: { metal?, crystal?, deuterium? };
  want: { metal?, crystal?, deuterium? };
  expires_at: string;
}

// Profil
type PlayerProfile = {
  id: string;
  username: string;
  rank: number;
  score: number;
  ships_total: number;
  ships_legendary: number;
  combats_won: number;
  combats_lost: number;
  alliance?: { id, tag, name };
  most_glorious_ships: ShipSummary[];
}
```
