# Emago — Schéma BDD complet
*Agent 7 — Développeur Base de données | Version 1.0 | 2025-01-29*
*Stack : PostgreSQL 16 · SQLAlchemy 2.0 async · asyncpg · Redis 7 · Alembic*

---

## Vue d'ensemble

```
┌─────────────┐     ┌─────────────┐
│   players   │────►│  alliances  │
└──────┬──────┘     └─────────────┘
       │
       ├──────────────────────────────────────────────┐
       │                                              │
       ▼                                              ▼
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│   planets   │────►│ build_queue  │     │ technologies  │
└──────┬──────┘     └──────────────┘     └───────────────┘
       │
       ▼
┌─────────────┐◄────────────────────────────────────────┐
│    ships    │  (table centrale — toutes les relations) │
└──────┬──────┘                                         │
       │                                                │
       ├──► ship_modules                                │
       ├──► ship_scars ──► scar_tags                   │
       ├──► ship_missions                               │
       └──► forge_queue ──────────────────────────────►┘
                │
                ▼
         (ships résultats)

┌─────────────┐     ┌─────────────┐     ┌──────────────┐
│   fleets    │────►│ fleet_ships │────►│    ships     │
└──────┬──────┘     └─────────────┘     └──────────────┘
       │
       ▼
┌──────────────┐
│ combat_logs  │
└──────────────┘
```

---

## Enums PostgreSQL

| Type | Valeurs |
|---|---|
| `ship_class` | `ATTACK` · `DEFENSE` · `SUPPORT` · `EXPLORATION` |
| `ship_rarity` | `COMMON` · `UNCOMMON` · `RARE` · `EPIC` · `LEGENDARY` |
| `ship_status` | `DOCKED` · `IN_FLEET` · `IN_FORGE` |
| `module_family` | `PROPELLER` · `ARMOR` · `CANNON` · `EMITTER` · `SHIELD` · `CARGO` |
| `fleet_mission` | `ATTACK` · `TRANSPORT` · `ESPIONAGE` · `COLONIZE` · `RECALL` |

---

## Tables

---

### `players`
Comptes joueurs. Un joueur peut appartenir à une alliance.

| Colonne | Type | Contraintes | Notes |
|---|---|---|---|
| `id` | UUID | PK, `gen_random_uuid()` | |
| `username` | VARCHAR(32) | NOT NULL, UNIQUE | |
| `email` | VARCHAR(255) | NOT NULL, UNIQUE | |
| `password_hash` | TEXT | NOT NULL | bcrypt |
| `score` | BIGINT | NOT NULL, DEFAULT 0 | Recalculé par scheduler |
| `alliance_id` | UUID | FK → alliances(id), SET NULL | Nullable |
| `last_login_at` | TIMESTAMPTZ | | |
| `refresh_token` | TEXT | | JWT refresh (1 actif max) |
| `refresh_token_expires_at` | TIMESTAMPTZ | | |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |

**Index :** `idx_players_score` sur `score DESC` (classements)

---

### `alliances`
Guildes de joueurs. FK circulaire avec `players`.

| Colonne | Type | Contraintes | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `name` | VARCHAR(64) | NOT NULL, UNIQUE | |
| `tag` | VARCHAR(8) | NOT NULL, UNIQUE | Ex: `[NOVA]` |
| `leader_id` | UUID | NOT NULL, FK → players(id), RESTRICT | |
| `description` | TEXT | | |
| `score` | BIGINT | NOT NULL, DEFAULT 0 | Somme scores membres |
| `created_at` | TIMESTAMPTZ | NOT NULL | |

**FK circulaire :** `players.alliance_id ↔ alliances.leader_id` — résolue via `use_alter=True` en migration.
**Index :** `idx_alliances_score` sur `score DESC`

---

### `planets`
Planètes colonisées. Coordonnées uniques en galaxie:système:position.

| Colonne | Type | Contraintes | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `owner_id` | UUID | FK → players(id), SET NULL | Nullable (planète neutre) |
| `galaxy` | SMALLINT | NOT NULL, CHECK 1–9 | |
| `system` | SMALLINT | NOT NULL, CHECK 1–499 | |
| `position` | SMALLINT | NOT NULL, CHECK 1–15 | |
| `name` | VARCHAR(64) | NOT NULL, DEFAULT 'Planète sans nom' | |
| `is_homeworld` | BOOLEAN | NOT NULL, DEFAULT FALSE | |
| `metal` | NUMERIC(16,2) | NOT NULL, DEFAULT 500 | Production lazy |
| `crystal` | NUMERIC(16,2) | NOT NULL, DEFAULT 300 | |
| `deuterium` | NUMERIC(16,2) | NOT NULL, DEFAULT 100 | |
| `metal_capacity` | INTEGER | NOT NULL, DEFAULT 10000 | Augmente avec silos |
| `crystal_capacity` | INTEGER | NOT NULL, DEFAULT 10000 | |
| `deut_capacity` | INTEGER | NOT NULL, DEFAULT 5000 | |
| `resources_last_updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Clé de la prod lazy |
| `buildings` | JSONB | NOT NULL, DEFAULT `{}` | Ex: `{"metal_mine": 5}` |
| `created_at` | TIMESTAMPTZ | NOT NULL | |

**Contrainte :** `UNIQUE(galaxy, system, position)`
**Index :** `idx_planets_owner` sur `owner_id`
**Note design :** `buildings` en JSONB évite 15 JOINs par dashboard. Nouveaux bâtiments sans migration.

---

### `build_queue`
File de construction par planète (bâtiments, recherches, vaisseaux).

| Colonne | Type | Contraintes | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `planet_id` | UUID | NOT NULL, FK → planets(id), CASCADE | |
| `player_id` | UUID | NOT NULL, FK → players(id), CASCADE | |
| `item_type` | VARCHAR(16) | NOT NULL, CHECK IN ('BUILDING','RESEARCH','SHIP') | |
| `item_name` | VARCHAR(64) | NOT NULL | Ex: `"metal_mine"` |
| `target_level` | SMALLINT | Nullable | NULL pour SHIP |
| `cost_metal` | INTEGER | NOT NULL, DEFAULT 0 | Snapshot au lancement |
| `cost_crystal` | INTEGER | NOT NULL, DEFAULT 0 | |
| `cost_deuterium` | INTEGER | NOT NULL, DEFAULT 0 | |
| `started_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| `completes_at` | TIMESTAMPTZ | NOT NULL | Vérifié par scheduler |
| `completed` | BOOLEAN | NOT NULL, DEFAULT FALSE | |
| `completed_at` | TIMESTAMPTZ | Nullable | |

**Index partiel :** `idx_build_queue_planet_pending` sur `(planet_id, completes_at) WHERE completed = FALSE`

---

### `technologies`
Arbre technologique par joueur. Une seule ligne par joueur.

| Colonne | Type | Contraintes | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `player_id` | UUID | NOT NULL, FK → players(id), CASCADE, UNIQUE | 1 ligne/joueur |
| `tech_levels` | JSONB | NOT NULL, DEFAULT `{}` | Ex: `{"weapons_tech": 7}` |
| `updated_at` | TIMESTAMPTZ | NOT NULL | |

---

### `scar_tags`
Pool de ~500 tags narratifs pour les cicatrices. Peuplé par seed, jamais modifié en prod.

| Colonne | Type | Contraintes | Notes |
|---|---|---|---|
| `id` | SERIAL | PK | Integer auto-increment |
| `tag_code` | VARCHAR(64) | NOT NULL, UNIQUE | Ex: `"nebula_kha_survivor"` |
| `narrative` | TEXT | NOT NULL | Ex: `"Rescapé de la Nébuleuse Kha"` |

---

### ⭐ `ships` — Table centrale
Chaque vaisseau est une entité unique avec identité, stats immuables et histoire.

| Colonne | Type | Contraintes | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `owner_id` | UUID | NOT NULL, FK → players(id), CASCADE | |
| `planet_id` | UUID | FK → planets(id), SET NULL | Planète d'amarrage |
| `ship_type` | VARCHAR(64) | NOT NULL | Ex: `"frigate_attack"` |
| `class` | ship_class | NOT NULL | Enum PG |
| `rarity` | ship_rarity | NOT NULL | Enum PG |
| `status` | ship_status | NOT NULL, DEFAULT 'DOCKED' | Enum PG |
| `grade` | SMALLINT | NOT NULL, DEFAULT 0, CHECK 0–5 | 0=Recrue → 5=Spectre |
| `combat_xp` | INTEGER | NOT NULL, DEFAULT 0, CHECK ≥ 0 | |
| `base_stats` | JSONB | NOT NULL | **⚠ IMMUABLE** — trigger |
| `parent_ship_id` | UUID | FK → ships(id), SET NULL | Pedigree nullable |
| `pedigree_bonus` | JSONB | Nullable | Ex: `{"stat":"dps","bonus_pct":5}` |
| `grade4_immunity_active` | BOOLEAN | NOT NULL, DEFAULT FALSE | Immunité Grade 4 |
| `grade4_immunity_reset_at` | TIMESTAMPTZ | Nullable | Reset après 48h non-combat |
| `created_at` | TIMESTAMPTZ | NOT NULL | |
| `updated_at` | TIMESTAMPTZ | NOT NULL | Auto-mis à jour (trigger) |

**Format `base_stats` :**
```json
{
  "hull": 152,
  "shield": 31,
  "dps": 79,
  "speed": 44,
  "cargo": 198,
  "stealth": 0,
  "support_aura": 0
}
```

**`current_stats` : JAMAIS en base.** Calculé par `ship_stats_service`, stocké Redis `ship:{id}:stats` TTL 5min.

**Index :**
- `idx_ships_owner_status` sur `(owner_id, status)` — requête la plus fréquente (hangar)
- `idx_ships_owner_planet` sur `(owner_id, planet_id)`
- `idx_ships_rarity` sur `rarity`

---

### `ship_modules`
Modules installés dans les slots d'un vaisseau.

| Colonne | Type | Contraintes | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `ship_id` | UUID | NOT NULL, FK → ships(id), CASCADE | |
| `slot_index` | SMALLINT | NOT NULL, CHECK 0–5 | 0-based |
| `module_type` | module_family | NOT NULL | Enum PG |
| `level` | SMALLINT | NOT NULL, CHECK 1–5 | |
| `affinity_bonus` | BOOLEAN | NOT NULL, DEFAULT FALSE | +15% si classe native |
| `installed_at` | TIMESTAMPTZ | NOT NULL | |

**Contrainte :** `UNIQUE(ship_id, slot_index)` — un seul module par slot
**Index :** `idx_ship_modules_ship_id` sur `ship_id` — appelé à chaque calcul de `current_stats`

**Slots disponibles par rareté :**
| Rareté | Slots standard | Slots premium |
|---|---|---|
| COMMON | 0–1 | — |
| UNCOMMON | 0–2 | — |
| RARE | 0–2 | 3 |
| EPIC | 0–2 | 3–4 |
| LEGENDARY | 0–2 | 3–5 |

Slots premium (index ≥ 3) : acceptent modules niveaux IV–V.

---

### `forge_queue`
Fusions en cours entre deux vaisseaux de même type et rareté (durée : 8h).

| Colonne | Type | Contraintes | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `player_id` | UUID | NOT NULL, FK → players(id), CASCADE | |
| `ship_a_id` | UUID | NOT NULL, FK → ships(id) | |
| `ship_b_id` | UUID | NOT NULL, FK → ships(id) | |
| `cost_metal` | INTEGER | NOT NULL | Déduit au lancement |
| `cost_crystal` | INTEGER | NOT NULL | |
| `cost_deuterium` | INTEGER | NOT NULL | |
| `started_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | |
| `completed_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now()+8h | **⚠ Index critique scheduler** |
| `result_ship_id` | UUID | FK → ships(id), SET NULL | NULL jusqu'à finalisation |
| `is_completed` | BOOLEAN | NOT NULL, DEFAULT FALSE | |

**Contrainte :** `ship_a_id != ship_b_id`
**Index partiels :**
- `idx_forge_queue_completed_at` sur `completed_at WHERE is_completed = FALSE` — APScheduler toutes les 60s
- `idx_forge_queue_player` sur `player_id WHERE is_completed = FALSE`

---

### `ship_scars`
Cicatrices narratives gagnées en combat difficile. Aucun effet mécanique.

| Colonne | Type | Contraintes | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `ship_id` | UUID | NOT NULL, FK → ships(id), CASCADE | |
| `tag_id` | INTEGER | NOT NULL, FK → scar_tags(id) | |
| `earned_at` | TIMESTAMPTZ | NOT NULL | |

**Contrainte :** `UNIQUE(ship_id, tag_id)` — pas deux fois la même cicatrice
**Condition d'attribution :** perte >75% coque OU combat contre flotte ×2 plus puissante
**Index :** `idx_ship_scars_ship` sur `ship_id`

---

### `ship_missions`
Missions optionnelles pour les vaisseaux Grade 2+. Renouvellement toutes les 72h.

| Colonne | Type | Contraintes | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `ship_id` | UUID | NOT NULL, FK → ships(id), CASCADE | |
| `mission_type` | VARCHAR(64) | NOT NULL | Ex: `"siege_participant"` |
| `condition` | JSONB | NOT NULL | Ex: `{"kills": 10, "target_class": "ATTACK"}` |
| `progress` | JSONB | NOT NULL, DEFAULT `{}` | Ex: `{"kills": 4}` |
| `reward` | JSONB | NOT NULL | Ex: `{"skin": "nova_red"}` |
| `expires_at` | TIMESTAMPTZ | NOT NULL | +72h à la création |
| `completed` | BOOLEAN | NOT NULL, DEFAULT FALSE | |
| `completed_at` | TIMESTAMPTZ | Nullable | |
| `reward_claimed` | BOOLEAN | NOT NULL, DEFAULT FALSE | Via POST /claim |

**Index partiel :** `idx_ship_missions_ship_expires` sur `(ship_id, expires_at) WHERE completed = FALSE`

---

### `fleets`
Flottes en transit. Les vaisseaux membres ont `status = IN_FLEET` dans `ships`.

| Colonne | Type | Contraintes | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `owner_id` | UUID | NOT NULL, FK → players(id), CASCADE | |
| `origin_planet_id` | UUID | NOT NULL, FK → planets(id) | |
| `target_planet_id` | UUID | FK → planets(id) | Nullable si coords directes |
| `target_galaxy` | SMALLINT | | Coordonnées directes |
| `target_system` | SMALLINT | | |
| `target_position` | SMALLINT | | |
| `mission` | fleet_mission | NOT NULL | Enum PG |
| `cargo_metal` | NUMERIC(16,2) | NOT NULL, DEFAULT 0 | |
| `cargo_crystal` | NUMERIC(16,2) | NOT NULL, DEFAULT 0 | |
| `cargo_deuterium` | NUMERIC(16,2) | NOT NULL, DEFAULT 0 | |
| `departed_at` | TIMESTAMPTZ | NOT NULL | |
| `arrives_at` | TIMESTAMPTZ | NOT NULL | Calculé à l'envoi |
| `return_arrives_at` | TIMESTAMPTZ | Nullable | |
| `is_returning` | BOOLEAN | NOT NULL, DEFAULT FALSE | |
| `is_recalled` | BOOLEAN | NOT NULL, DEFAULT FALSE | |

**Index partiels :**
- `idx_fleets_arrives_at` sur `arrives_at WHERE is_recalled = FALSE` — scheduler d'arrivée
- `idx_fleets_owner` sur `owner_id`

---

### `fleet_ships`
Table d'association flottes ↔ vaisseaux (many-to-many).

| Colonne | Type | Contraintes |
|---|---|---|
| `fleet_id` | UUID | PK, FK → fleets(id), CASCADE |
| `ship_id` | UUID | PK, FK → ships(id), CASCADE |

---

### `combat_logs`
Logs complets de combat. Replay possible via `rounds_log`.

| Colonne | Type | Contraintes | Notes |
|---|---|---|---|
| `id` | UUID | PK | |
| `fleet_attacker_id` | UUID | NOT NULL, FK → fleets(id) | |
| `fleet_defender_id` | UUID | FK → fleets(id) | Nullable si défense planétaire |
| `defender_planet_id` | UUID | FK → planets(id) | Nullable |
| `outcome` | VARCHAR(16) | NOT NULL, CHECK IN ('ATTACKER_WIN','DEFENDER_WIN','DRAW') | |
| `pillaged_metal` | NUMERIC(16,2) | NOT NULL, DEFAULT 0 | |
| `pillaged_crystal` | NUMERIC(16,2) | NOT NULL, DEFAULT 0 | |
| `pillaged_deuterium` | NUMERIC(16,2) | NOT NULL, DEFAULT 0 | |
| `rounds_log` | JSONB | NOT NULL, DEFAULT `[]` | Replay round par round |
| `attacker_ships_snapshot` | JSONB | NOT NULL | Snapshot stats au combat |
| `defender_ships_snapshot` | JSONB | NOT NULL | |
| `attacker_power` | NUMERIC(12,2) | NOT NULL | Pour formule XP différentielle |
| `defender_power` | NUMERIC(12,2) | NOT NULL | |
| `fought_at` | TIMESTAMPTZ | NOT NULL | |

**Format `rounds_log` :**
```json
[
  {
    "round": 1,
    "attacker_damage": 450,
    "defender_damage": 120,
    "synergies_active": ["ATTACK+SUPPORT"],
    "ships_lost": [{"ship_id": "uuid", "side": "defender"}]
  }
]
```

**Index :** `idx_combat_logs_attacker` sur `(fleet_attacker_id, fought_at DESC)`

---

## Triggers

### `trg_ships_prevent_base_stats_update`
**Table :** `ships` | **Événement :** `BEFORE UPDATE FOR EACH ROW`

Lève une exception si `NEW.base_stats != OLD.base_stats`.
Garantit l'immuabilité des stats RNG générées à la création.

**Bypass pour migrations Alembic contrôlées :**
```sql
SET LOCAL emago.bypass_stats_trigger = 'true';
UPDATE ships SET base_stats = '...' WHERE id = '...';
-- Le SET LOCAL expire à la fin de la transaction
```

### `trg_ships_updated_at`
**Table :** `ships` | **Événement :** `BEFORE UPDATE FOR EACH ROW`

Met à jour `updated_at = now()` automatiquement.

---

## Stratégie Redis

| Clé | Contenu | TTL | Invalidation |
|---|---|---|---|
| `ship:{id}:stats` | `current_stats` JSON complet | 5 min | `PUT /modules`, `grade_up` |
| `player:{id}:hangar` | `[{id, rarity, class, grade, status}]` | 2 min | build, demolish, forge |
| `forge:{id}:status` | `{progress_pct, eta_seconds}` | Durée forge | Completion ou annulation |
| `combat:{id}:result` | Rapport complet sérialisé | 10 min | Jamais (lecture seule) |

**Règle absolue :** `current_stats` n'existe qu'en Redis. Jamais en base PostgreSQL.

---

## Index — récapitulatif

| Index | Table | Colonnes | Partiel ? | Usage |
|---|---|---|---|---|
| `idx_ships_owner_status` | ships | `owner_id, status` | Non | Hangar actif — requête la plus fréquente |
| `idx_ships_owner_planet` | ships | `owner_id, planet_id` | Non | Vue hangar par planète |
| `idx_ships_rarity` | ships | `rarity` | Non | Classements, stats |
| `idx_ship_modules_ship_id` | ship_modules | `ship_id` | Non | Calcul `current_stats` — systématique |
| `idx_forge_queue_completed_at` | forge_queue | `completed_at` | ✅ `is_completed=FALSE` | APScheduler 60s — **critique** |
| `idx_forge_queue_player` | forge_queue | `player_id` | ✅ `is_completed=FALSE` | Forges actives d'un joueur |
| `idx_build_queue_planet_pending` | build_queue | `planet_id, completes_at` | ✅ `completed=FALSE` | Scheduler construction |
| `idx_fleets_arrives_at` | fleets | `arrives_at` | ✅ `is_recalled=FALSE` | Scheduler arrivées de flotte |
| `idx_fleets_owner` | fleets | `owner_id` | Non | Flottes d'un joueur |
| `idx_ship_missions_ship_expires` | ship_missions | `ship_id, expires_at` | ✅ `completed=FALSE` | Missions actives |
| `idx_ship_scars_ship` | ship_scars | `ship_id` | Non | Cicatrices d'un vaisseau |
| `idx_combat_logs_attacker` | combat_logs | `fleet_attacker_id, fought_at` | Non | Historique de combats |
| `idx_planets_owner` | planets | `owner_id` | Non | Planètes d'un joueur |
| `idx_players_score` | players | `score DESC` | Non | Classement global |
| `idx_alliances_score` | alliances | `score DESC` | Non | Classement alliances |

---

## Fichiers produits

| Fichier | Rôle |
|---|---|
| `schema.sql` | Schéma SQL de référence commenté (documentation + déploiement direct) |
| `app/models/models.py` | Modèles SQLAlchemy 2.0 async — à importer dans les services |
| `alembic/env.py` | Configuration Alembic async avec asyncpg |
| `alembic/versions/0001_initial_schema.py` | Migration complète (enums, tables, triggers, index) |
| `alembic/versions/0002_seed_scar_tags.py` | Seed des 30 premiers tags narratifs (à compléter jusqu'à ~500) |

---

*Document généré pour le projet Emago — Version 1.0*
*Stack : Python/FastAPI · React/TypeScript · PostgreSQL · Redis · Docker*
