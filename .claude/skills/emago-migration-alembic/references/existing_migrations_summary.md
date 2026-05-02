# Migrations existantes Emago — résumé

Source : `alembic/versions/` + `docs/07_base_de_donnees.md` section 5.

## 0001 — initial_schema

Création initiale complète. Inclut :

### Extensions
- `pgcrypto` (gen_random_uuid)
- `pg_trgm` (recherche similaire futures)

### Enums créés (5)
- `ship_class` : ATTACK, DEFENSE, SUPPORT, EXPLORATION
- `ship_rarity` : COMMON, UNCOMMON, RARE, EPIC, LEGENDARY
- `ship_status` : DOCKED, IN_FLEET, IN_FORGE
- `module_family` : PROPELLER, ARMOR, CANNON, EMITTER, SHIELD, CARGO
- `fleet_mission` : ATTACK, TRANSPORT, ESPIONAGE, COLONIZE, RECALL

### Tables créées (11 + association)
1. `alliances` — id, name UQ, tag UQ, leader_id (FK use_alter), description, score BigInt, created_at
2. `players` — id, username UQ, email UQ, password_hash, score BigInt, alliance_id (FK use_alter SET NULL), last_login_at, refresh_token, refresh_token_expires_at, created_at
3. `scar_tags` — id Integer auto, tag_code UQ, narrative Text
4. `planets` — id, owner_id (FK SET NULL), galaxy/system/position (CHECK 1-9 / 1-499 / 1-15), name, is_homeworld, metal/crystal/deuterium NUMERIC(16,2), capacities INT, resources_last_updated_at, buildings JSONB, created_at + UNIQUE coordinates
5. `build_queue` — id, planet_id (CASCADE), player_id (CASCADE), item_type CHECK IN, item_name, target_level, costs INT, started_at, completes_at, completed BOOL, completed_at
6. `technologies` — id, player_id UQ FK CASCADE, tech_levels JSONB, updated_at
7. `ships` — id, owner_id (CASCADE), planet_id (SET NULL), ship_type, class, rarity, status default DOCKED, grade CHECK 0-5, combat_xp CHECK ≥0, **base_stats JSONB IMMUABLE**, parent_ship_id (SET NULL), pedigree_bonus, grade4_immunity_active, grade4_immunity_reset_at, created_at, updated_at
8. `ship_modules` — id, ship_id (CASCADE), slot_index CHECK 0-5, module_type, level CHECK 1-5, affinity_bonus, installed_at + UNIQUE(ship_id, slot_index)
9. `forge_queue` — id, player_id (CASCADE), ship_a_id, ship_b_id (FK ships), costs INT, started_at, completed_at default `now() + INTERVAL '8 hours'`, result_ship_id (SET NULL), is_completed + CHECK ship_a_id != ship_b_id
10. `ship_scars` — id, ship_id (CASCADE), tag_id (FK scar_tags), earned_at + UNIQUE(ship_id, tag_id)
11. `ship_missions` — id, ship_id (CASCADE), mission_type, condition JSONB, progress JSONB, reward JSONB, expires_at, completed, completed_at, reward_claimed
12. `fleets` — id, owner_id (CASCADE), origin_planet_id, target_planet_id, target_galaxy/system/position, mission, cargo_*, departed_at, arrives_at, return_arrives_at, is_returning, is_recalled
13. `fleet_ships` — `(fleet_id, ship_id)` PK composite (CASCADE des deux côtés) — table d'association
14. `combat_logs` — id, fleet_attacker_id, fleet_defender_id, defender_planet_id, outcome CHECK IN, pillaged_*, rounds_log JSONB, snapshots JSONB, attacker_power/defender_power NUMERIC(12,2), fought_at

### Triggers (2)
- `prevent_base_stats_update` BEFORE UPDATE on ships — lève exception si `NEW.base_stats != OLD.base_stats` ET pas de bypass session var.
- `set_updated_at` BEFORE UPDATE on ships — `NEW.updated_at = now()`.

### Indexes partiels critiques
- `idx_build_queue_planet_pending` ON build_queue (planet_id, completes_at) WHERE completed=FALSE
- `idx_forge_queue_completed_at` ON forge_queue (completed_at) WHERE is_completed=FALSE — **utilisé scheduler 60s**
- `idx_forge_queue_player` ON forge_queue (player_id) WHERE is_completed=FALSE
- `idx_fleets_arrives_at` ON fleets (arrives_at) WHERE is_recalled=FALSE — **utilisé scheduler 5s**
- `idx_ship_missions_ship_expires` ON ship_missions (ship_id, expires_at) WHERE completed=FALSE

### Indexes simples
- `idx_alliances_score` (score DESC)
- `idx_players_score` (score DESC)
- `idx_planets_owner` (owner_id)
- `idx_ships_owner_status` (owner_id, status)
- `idx_ships_owner_planet` (owner_id, planet_id)
- `idx_ships_rarity` (rarity)
- `idx_ship_modules_ship_id` — **CRITIQUE** pour calcul current_stats
- `idx_ship_scars_ship` (ship_id)
- `idx_fleets_owner` (owner_id)
- `idx_combat_logs_attacker` (fleet_attacker_id, fought_at DESC)

### Pattern à reproduire
- FK circulaires alliance ↔ player via `use_alter=True`.
- Trigger immuabilité avec session var bypass.
- Indexes partiels pour minimiser scans scheduler.

---

## 0002 — seed_scar_tags

Bulk insert de ~30 tags narratifs (pool ~500 cible). Catégories :
- Batailles célèbres (10)
- Exploits individuels (10)
- Conditions extrêmes (5)
- Alliances et trahisons (5)

Exemples : `nebula_kha_survivor`, `hull_at_one_percent`, `titan_killer`, `betrayed_by_ally`, `ion_storm_transit`.

### Pattern à reproduire
- `op.bulk_insert` avec table définie via `sa.table(...) + sa.column(...)`.
- Downgrade : DELETE WHERE tag_code IN (...) — note : ne pas rollback en prod si `ship_scars` référence.

---

## 0003 — add_player_daily_data

ALTER TABLE players ADD COLUMN `daily_data JSONB NOT NULL DEFAULT '{}'`.

### Structure JSON (informelle)
```json
{
  "last_login_date": "YYYY-MM-DD",
  "streak": 1,
  "missions_claimed": ["build_ship", ...],
  "missions_progress": { "collect_metal": 1500, ... }
}
```

### Pattern à reproduire
- Ajout JSONB avec `server_default='{}'` pour remplir les rows existantes automatiquement.

---

## 0004 — alliances

Sprint 4 : tables d'extension alliance.

### Nouveaux enums (2)
- `alliance_role` : LEADER, OFFICER, MEMBER
- `war_status` : ACTIVE, PEACE

### Nouvelles tables (2)
- `alliance_members` — id, alliance_id (CASCADE), player_id (CASCADE, UQ), role default 'MEMBER' CHECK, joined_at + UNIQUE(player_id) [un joueur = une alliance]
- `alliance_wars` — id, attacker_id, defender_id (CASCADE), status default 'ACTIVE' CHECK, declared_at, peace_at, xp_bonus NUMERIC(4,2) default 1.5 + CHECK distinct + index partiel ACTIVE

### ALTER players
ADD COLUMN `alliance_last_candidacy_at TIMESTAMPTZ NULL` — pour cooldown re-candidature 24h.

### Pattern à reproduire
- Index partiel `WHERE status = 'ACTIVE'` pour query alliances en guerre.
- UNIQUE(player_id) sur alliance_members force le 1-to-1.

---

## 0005 — expedition_logs_table

Création table `expedition_logs` (préparée pour migration future Redis → BDD).

Colonnes :
- id UUID PK
- player_id (CASCADE)
- planet_id (SET NULL)
- ship_ids JSONB default '[]' (snapshot UUIDs)
- duration_hours SMALLINT CHECK IN (2, 6, 12)
- cost_deuterium NUMERIC(12,2) default 0
- event_type VARCHAR(32) CHECK IN ('RESOURCES','SHIPS_LOST','ANOMALY','EMPTY','DISCOVERY')
- result JSONB
- launched_at, completes_at, completed_at TIMESTAMPTZ

Indexes partiels :
- `idx_expedition_completes_at` ON (completes_at) WHERE completed_at IS NULL
- `idx_expedition_player_active` ON (player_id, completes_at) WHERE completed_at IS NULL

> **Note** : actuellement, le code utilise Redis (TTL 48h). La table est prête mais non utilisée. Décision Phase 2 : migrer ou pas.

---

## 0006 — ship_rpg_fields

Sprint 1.1 RPG. ALTER TABLE ships pour ajouter :
- `name VARCHAR(64) NULL` — nom procédural pour RARE+ (ex. "Astraeus Noir")
- `trait JSONB NULL` — `{key, name, description}`
- `is_drift BOOLEAN NOT NULL DEFAULT FALSE` — vaisseau Forge Dérive 5%

Index partiel : `idx_ships_is_drift` ON (is_drift) WHERE `is_drift = true`.

Seed scar_tag idempotent :
```sql
INSERT INTO scar_tags (tag_code, narrative)
VALUES ('born_in_drift', 'Né dans la Dérive')
ON CONFLICT (tag_code) DO NOTHING
```

### Pattern à reproduire
- Colonnes nullable pour features optionnelles (name = NULL pour COMMON/UNCOMMON).
- Bool default FALSE + index partiel WHERE = true (économique).
- Seed idempotent avec ON CONFLICT.

---

## Migrations futures probables

### 0007 — research_queue (ou similaire)
**Pourquoi** : `_active_research` actuellement en mémoire dans `routers/tech.py` (TODO ligne 212). Doit migrer en BDD.
**Structure proposée** : id UUID, player_id (CASCADE, UQ), tech_id String, target_level SMALLINT, completes_at TIMESTAMPTZ, costs INT.

### 0008 — espionage_reports (Phase 2B)
**Pourquoi** : nouvelle mécanique d'espionnage.

### 0009 — market_offers (Phase 2B)
**Pourquoi** : marché galactique entre joueurs.

### 0010 — player_module_inventory (Phase 2B)
**Pourquoi** : persister les drops de modules d'expédition.

### 0011 — alliance_chat (Phase 3)
**Pourquoi** : chat alliance (mécaniques avancées).

### 0012 — espionage_alerts (Phase 2B)
**Pourquoi** : notifications quand un joueur détecte une sonde adverse.
