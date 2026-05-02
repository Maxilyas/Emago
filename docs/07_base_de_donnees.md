# Agent 7 — Dev Base de données

> Schéma PostgreSQL complet, 6 migrations Alembic, modèles SQLAlchemy 2.0 async, triggers d'intégrité, stratégie Redis, indexes critiques.

---

## 1. Vue d'ensemble du schéma

13 tables principales, 7 enums PostgreSQL, 2 triggers, 18+ indexes (dont indexes partiels critiques pour le scheduler). Tous les ID primaires sont `UUID` (sauf `scar_tags.id` en INTEGER autoincrement).

```
┌─────────────────────────────────────────────────────────────┐
│                                                              │
│  alliances ◄── alliance_members ──► players                  │
│  ▲              alliance_wars                                │
│  └─── (leader_id) ┐                                          │
│                   ▼                                          │
│  players ──► planets ──► build_queue                         │
│       │       │                                              │
│       ├──► ships ──► ship_modules                            │
│       │       │   ├──► ship_scars ──► scar_tags              │
│       │       │   └──► ship_missions                         │
│       │       │                                              │
│       │       └──◄ fleets ↔ fleet_ships                      │
│       │           │                                          │
│       │           └──► combat_logs (snapshots JSONB)         │
│       │                                                      │
│       ├──► technologies (1:1)                                │
│       └──► expedition_logs                                   │
│                                                              │
│  forge_queue (ship_a, ship_b → ships, result_ship)           │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Enums PostgreSQL

| Enum | Valeurs |
|---|---|
| `ship_class` | ATTACK, DEFENSE, SUPPORT, EXPLORATION |
| `ship_rarity` | COMMON, UNCOMMON, RARE, EPIC, LEGENDARY |
| `ship_status` | DOCKED, IN_FLEET, IN_FORGE |
| `module_family` | PROPELLER, ARMOR, CANNON, EMITTER, SHIELD, CARGO |
| `fleet_mission` | ATTACK, TRANSPORT, ESPIONAGE, COLONIZE, RECALL |
| `alliance_role` | LEADER, OFFICER, MEMBER |
| `war_status` | ACTIVE, PEACE |

---

## 3. Tables — schéma détaillé

### `players`
| Colonne | Type | Contraintes |
|---|---|---|
| id | UUID PK | DEFAULT `gen_random_uuid()` |
| username | VARCHAR(32) | UNIQUE, NOT NULL |
| email | VARCHAR(255) | UNIQUE, NOT NULL |
| password_hash | TEXT | bcrypt |
| score | BIGINT | DEFAULT 0 |
| alliance_id | UUID | FK alliances (SET NULL) |
| last_login_at | TIMESTAMPTZ | |
| refresh_token | TEXT | |
| refresh_token_expires_at | TIMESTAMPTZ | |
| daily_data | JSONB | DEFAULT `{}` (migration 0003) |
| alliance_last_candidacy_at | TIMESTAMPTZ | (migration 0004) |
| created_at | TIMESTAMPTZ | DEFAULT `now()` |

Index : `idx_players_score` (score DESC).

### `alliances`
| Colonne | Type | Contraintes |
|---|---|---|
| id | UUID PK | |
| name | VARCHAR(64) | UNIQUE |
| tag | VARCHAR(8) | UNIQUE |
| leader_id | UUID | FK players (RESTRICT, use_alter=True) |
| description | TEXT | |
| score | BIGINT | DEFAULT 0 |
| created_at | TIMESTAMPTZ | |

FK circulaires `alliances.leader_id ↔ players.alliance_id` gérées via `use_alter=True` puis `op.create_foreign_key(...)` après création des deux tables.

Index : `idx_alliances_score` (score DESC).

### `planets`
| Colonne | Type | Contraintes |
|---|---|---|
| id | UUID PK | |
| owner_id | UUID | FK players (SET NULL) |
| galaxy | SMALLINT | CHECK 1-9 |
| system | SMALLINT | CHECK 1-499 |
| position | SMALLINT | CHECK 1-15 |
| name | VARCHAR(64) | DEFAULT 'Planète sans nom' |
| is_homeworld | BOOLEAN | DEFAULT FALSE |
| metal | NUMERIC(16,2) | DEFAULT 500 |
| crystal | NUMERIC(16,2) | DEFAULT 300 |
| deuterium | NUMERIC(16,2) | DEFAULT 100 |
| metal_capacity | INTEGER | DEFAULT 10000 |
| crystal_capacity | INTEGER | DEFAULT 10000 |
| deut_capacity | INTEGER | DEFAULT 5000 |
| resources_last_updated_at | TIMESTAMPTZ | |
| buildings | JSONB | DEFAULT `{}` |
| created_at | TIMESTAMPTZ | |

Contraintes : UNIQUE `(galaxy, system, position)` (`uq_planet_coordinates`).
Index : `idx_planets_owner`.

### `build_queue`
| Colonne | Type | Contraintes |
|---|---|---|
| id | UUID PK | |
| planet_id | UUID | FK planets (CASCADE) |
| player_id | UUID | FK players (CASCADE) |
| item_type | VARCHAR(16) | CHECK IN ('BUILDING','RESEARCH','SHIP') |
| item_name | VARCHAR(64) | |
| target_level | SMALLINT | nullable |
| cost_metal/crystal/deuterium | INTEGER | DEFAULT 0 |
| started_at | TIMESTAMPTZ | DEFAULT `now()` |
| completes_at | TIMESTAMPTZ | NOT NULL |
| completed | BOOLEAN | DEFAULT FALSE |
| completed_at | TIMESTAMPTZ | nullable |

**Index partiel critique** : `idx_build_queue_planet_pending` ON (planet_id, completes_at) WHERE `completed = FALSE` — permet au scheduler `build_tick` de scanner uniquement les items en attente.

### `technologies`
| Colonne | Type | Contraintes |
|---|---|---|
| id | UUID PK | |
| player_id | UUID | UNIQUE FK players (CASCADE) |
| tech_levels | JSONB | DEFAULT `{}` |
| updated_at | TIMESTAMPTZ | |

### `scar_tags`
| Colonne | Type |
|---|---|
| id | INTEGER PK autoincrement |
| tag_code | VARCHAR(64) UNIQUE |
| narrative | TEXT |

Pool de ~500 tags narratifs (seedés par migration 0002 — actuellement ~30 entrées dans le seed, à compléter). Tag spécial `'born_in_drift'` ajouté par migration 0006.

### `ships` ⭐ (table centrale)
| Colonne | Type | Contraintes |
|---|---|---|
| id | UUID PK | |
| owner_id | UUID | FK players (CASCADE) |
| planet_id | UUID | FK planets (SET NULL) |
| ship_type | VARCHAR(64) | |
| class | ship_class enum | NOT NULL |
| rarity | ship_rarity enum | NOT NULL |
| status | ship_status enum | DEFAULT DOCKED |
| grade | SMALLINT | CHECK 0-5, DEFAULT 0 |
| combat_xp | INTEGER | CHECK ≥ 0, DEFAULT 0 |
| **base_stats** | JSONB | **NOT NULL, IMMUABLE via trigger** |
| parent_ship_id | UUID | FK ships (SET NULL) — Pedigree |
| pedigree_bonus | JSONB | nullable |
| grade4_immunity_active | BOOLEAN | DEFAULT FALSE |
| grade4_immunity_reset_at | TIMESTAMPTZ | nullable |
| **name** | VARCHAR(64) | nullable (RARE+ uniquement) — migration 0006 |
| **trait** | JSONB | nullable `{key, name, description}` — migration 0006 |
| **is_drift** | BOOLEAN | DEFAULT FALSE — migration 0006 |
| created_at | TIMESTAMPTZ | |
| updated_at | TIMESTAMPTZ | DEFAULT `now()`, mise à jour par trigger |

Indexes :
- `idx_ships_owner_status` (owner_id, status) — requête la plus fréquente (hangar actif).
- `idx_ships_owner_planet` (owner_id, planet_id).
- `idx_ships_rarity` (rarity).
- `idx_ships_is_drift` partiel WHERE `is_drift = true` (migration 0006).

### `ship_modules`
| Colonne | Type | Contraintes |
|---|---|---|
| id | UUID PK | |
| ship_id | UUID | FK ships (CASCADE) |
| slot_index | SMALLINT | CHECK 0-5 |
| module_type | module_family enum | |
| level | SMALLINT | CHECK 1-5 |
| affinity_bonus | BOOLEAN | |
| installed_at | TIMESTAMPTZ | |

Contraintes : UNIQUE `(ship_id, slot_index)`.
Index `idx_ship_modules_ship_id` — **critique** (chaque calcul `current_stats` le requête).

### `forge_queue`
| Colonne | Type | Contraintes |
|---|---|---|
| id | UUID PK | |
| player_id | UUID | FK players (CASCADE) |
| ship_a_id | UUID | FK ships |
| ship_b_id | UUID | FK ships |
| cost_metal/crystal/deuterium | INTEGER | |
| started_at | TIMESTAMPTZ | |
| completed_at | TIMESTAMPTZ | DEFAULT `now() + INTERVAL '8 hours'` |
| result_ship_id | UUID | FK ships (SET NULL) |
| is_completed | BOOLEAN | DEFAULT FALSE |

CHECK `ck_forge_ships_distinct` : `ship_a_id != ship_b_id`.
Index partiel critique : `idx_forge_queue_completed_at` ON (completed_at) WHERE `is_completed = FALSE` — utilisé par scheduler `forge_tick` toutes les 60 s.
Index `idx_forge_queue_player` partiel WHERE `is_completed = FALSE`.

### `ship_scars`
| Colonne | Type | Contraintes |
|---|---|---|
| id | UUID PK | |
| ship_id | UUID | FK ships (CASCADE) |
| tag_id | INTEGER | FK scar_tags |
| earned_at | TIMESTAMPTZ | |

Contrainte UNIQUE `(ship_id, tag_id)` — un même tag ne peut pas être appliqué deux fois.
Index `idx_ship_scars_ship`.

### `ship_missions`
| Colonne | Type | Contraintes |
|---|---|---|
| id | UUID PK | |
| ship_id | UUID | FK ships (CASCADE) |
| mission_type | VARCHAR(64) | |
| condition | JSONB | NOT NULL |
| progress | JSONB | DEFAULT `{}` |
| reward | JSONB | NOT NULL |
| expires_at | TIMESTAMPTZ | NOT NULL |
| completed | BOOLEAN | DEFAULT FALSE |
| completed_at | TIMESTAMPTZ | nullable |
| reward_claimed | BOOLEAN | DEFAULT FALSE |

Index partiel : `idx_ship_missions_ship_expires` ON (ship_id, expires_at) WHERE `completed = FALSE`.

### `fleets`
| Colonne | Type | Contraintes |
|---|---|---|
| id | UUID PK | |
| owner_id | UUID | FK players (CASCADE) |
| origin_planet_id | UUID | FK planets |
| target_planet_id | UUID | FK planets, nullable |
| target_galaxy/system/position | SMALLINT | nullable |
| mission | fleet_mission enum | |
| cargo_metal/crystal/deuterium | NUMERIC(16,2) | DEFAULT 0 |
| departed_at | TIMESTAMPTZ | |
| arrives_at | TIMESTAMPTZ | NOT NULL |
| return_arrives_at | TIMESTAMPTZ | nullable |
| is_returning | BOOLEAN | DEFAULT FALSE |
| is_recalled | BOOLEAN | DEFAULT FALSE |

Index partiel critique : `idx_fleets_arrives_at` ON (arrives_at) WHERE `is_recalled = FALSE` — utilisé par scheduler `fleet_arrival` toutes les 5 s.
Index `idx_fleets_owner`.

### `fleet_ships` (table d'association)
| Colonne | Type |
|---|---|
| fleet_id | UUID PK FK fleets (CASCADE) |
| ship_id | UUID PK FK ships (CASCADE) |

PK composite. Aucun autre champ.

### `combat_logs`
| Colonne | Type | Contraintes |
|---|---|---|
| id | UUID PK | |
| fleet_attacker_id | UUID | FK fleets |
| fleet_defender_id | UUID | FK fleets, nullable |
| defender_planet_id | UUID | FK planets, nullable |
| outcome | VARCHAR(16) | CHECK IN ('ATTACKER_WIN','DEFENDER_WIN','DRAW') |
| pillaged_metal/crystal/deuterium | NUMERIC(16,2) | DEFAULT 0 |
| rounds_log | JSONB | DEFAULT `[]` |
| attacker_ships_snapshot | JSONB | DEFAULT `[]` |
| defender_ships_snapshot | JSONB | DEFAULT `[]` |
| attacker_power | NUMERIC(12,2) | NOT NULL |
| defender_power | NUMERIC(12,2) | NOT NULL |
| fought_at | TIMESTAMPTZ | DEFAULT `now()` |

Index : `idx_combat_logs_attacker` (fleet_attacker_id, fought_at DESC).

### `alliance_members` (migration 0004)
| Colonne | Type | Contraintes |
|---|---|---|
| id | UUID PK | |
| alliance_id | UUID | FK alliances (CASCADE) |
| player_id | UUID | UNIQUE FK players (CASCADE) — un joueur = une alliance |
| role | alliance_role enum | DEFAULT MEMBER |
| joined_at | TIMESTAMPTZ | |

CHECK `ck_alliance_member_role` IN ('LEADER','OFFICER','MEMBER').
Indexes : `idx_alliance_members_alliance`, `idx_alliance_members_player`.

### `alliance_wars` (migration 0004)
| Colonne | Type | Contraintes |
|---|---|---|
| id | UUID PK | |
| attacker_id | UUID | FK alliances (CASCADE) |
| defender_id | UUID | FK alliances (CASCADE) |
| status | war_status enum | DEFAULT ACTIVE |
| declared_at | TIMESTAMPTZ | |
| peace_at | TIMESTAMPTZ | nullable |
| xp_bonus | NUMERIC(4,2) | DEFAULT 1.5 |

CHECK `ck_war_different_alliances` : `attacker_id != defender_id`.
Indexes : `idx_alliance_wars_attacker`, `idx_alliance_wars_defender`, partiel `idx_alliance_wars_active` WHERE `status = 'ACTIVE'`.

### `expedition_logs` (migration 0005)
| Colonne | Type | Contraintes |
|---|---|---|
| id | UUID PK | |
| player_id | UUID | FK players (CASCADE) |
| planet_id | UUID | FK planets (SET NULL), nullable |
| ship_ids | JSONB | DEFAULT `[]` (snapshot UUIDs) |
| duration_hours | SMALLINT | CHECK IN (2,6,12) |
| cost_deuterium | NUMERIC(12,2) | DEFAULT 0 |
| event_type | VARCHAR(32) | nullable, CHECK IN ('RESOURCES','SHIPS_LOST','ANOMALY','EMPTY','DISCOVERY') |
| result | JSONB | nullable |
| launched_at | TIMESTAMPTZ | |
| completes_at | TIMESTAMPTZ | |
| completed_at | TIMESTAMPTZ | nullable |

Index partiel `idx_expedition_completes_at` ON (completes_at) WHERE `completed_at IS NULL`.
Index partiel `idx_expedition_player_active` ON (player_id, completes_at) WHERE `completed_at IS NULL`.

> **Note** : actuellement, le code utilise Redis (TTL 48h) pour stocker les expéditions actives. La table `expedition_logs` est prête pour la migration future si besoin de persistance.

---

## 4. Triggers PostgreSQL

### `prevent_base_stats_update` (migration 0001)

**Garantie d'immuabilité des stats de base.**

```sql
CREATE OR REPLACE FUNCTION prevent_base_stats_update_fn()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.base_stats IS DISTINCT FROM OLD.base_stats
     AND COALESCE(current_setting('emago.bypass_stats_trigger', true), '') != 'true'
  THEN
    RAISE EXCEPTION 'base_stats is immutable after creation'
      USING ERRCODE = 'integrity_constraint_violation';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER prevent_base_stats_update
  BEFORE UPDATE ON ships
  FOR EACH ROW
  EXECUTE FUNCTION prevent_base_stats_update_fn();
```

**Bypass contrôlé** : `SET LOCAL emago.bypass_stats_trigger = 'true'` dans une migration Alembic permet de modifier `base_stats` (réservé à l'évolution du schéma — pas de triche possible via API).

### `set_updated_at` (migration 0001)

```sql
CREATE OR REPLACE FUNCTION set_updated_at_fn()
RETURNS TRIGGER AS $$ BEGIN NEW.updated_at = now(); RETURN NEW; END; $$ LANGUAGE plpgsql;

CREATE TRIGGER set_updated_at
  BEFORE UPDATE ON ships
  FOR EACH ROW EXECUTE FUNCTION set_updated_at_fn();
```

---

## 5. Migrations Alembic — historique

### `0001_initial_schema.py`

Création initiale : 5 enums, 11 tables (alliances, players, scar_tags, planets, build_queue, technologies, ships, ship_modules, forge_queue, ship_scars, ship_missions, fleets, fleet_ships, combat_logs), 2 triggers PL/pgSQL, 18+ indexes (dont partiels). Extensions activées : `pgcrypto`, `pg_trgm`. FK circulaires alliance↔player gérées via `use_alter=True`.

### `0002_seed_scar_tags.py`

Bulk insert d'environ 30 tags narratifs (à compléter jusqu'à ~500). Catégories : Batailles célèbres, Exploits individuels, Conditions extrêmes, Alliances et trahisons. Exemples : `nebula_kha_survivor`, `hull_at_one_percent`, `titan_killer`, `betrayed_by_ally`, `ion_storm_transit`.

### `0003_add_player_daily_data.py`

ALTER TABLE players ADD COLUMN `daily_data JSONB NOT NULL DEFAULT '{}'`. Structure JSON : `{ last_login_date, streak, missions_claimed, missions_progress }`.

### `0004_alliances.py`

- 2 nouveaux enums : `alliance_role`, `war_status`.
- CREATE TABLE `alliance_members` (avec UNIQUE player_id : un joueur ne peut être que dans 1 alliance).
- CREATE TABLE `alliance_wars` (avec CHECK distinct + index partiel ACTIVE).
- ALTER TABLE players ADD COLUMN `alliance_last_candidacy_at TIMESTAMPTZ` (re-candidature 24h).

### `0005_expedition_logs_table.py`

CREATE TABLE `expedition_logs` (prête pour migration future Redis→DB). 2 indexes partiels.

### `0006_ship_rpg_fields.py`

- ALTER TABLE ships ADD COLUMN `name VARCHAR(64) NULL` (RARE+).
- ALTER TABLE ships ADD COLUMN `trait JSONB NULL`.
- ALTER TABLE ships ADD COLUMN `is_drift BOOLEAN NOT NULL DEFAULT FALSE`.
- Index partiel `idx_ships_is_drift` WHERE `is_drift = true`.
- INSERT INTO scar_tags `('born_in_drift', 'Né dans la Dérive')` ON CONFLICT DO NOTHING.

---

## 6. Stratégie Redis — détail

| Clé | Contenu | TTL | Invalidation |
|---|---|---:|---|
| `ship:{ship_id}:stats` | `current_stats` JSON complet (base + grade + modules + cap_reached) | 300 s | `PUT/DELETE /modules`, `grade_up`, fin de forge, démolition (`invalidate_ship_cache`) |
| `player:{player_id}:hangar` | Liste `[{id, rarity, class, grade, status}]` | 120 s | build, demolish, forge complete (`invalidate_hangar_cache`) |
| `forge:{forge_id}:status` | `{forge_id, completed_at(iso), progress_pct, eta_seconds, result_ship_id?}` | 8h+10min (29 400 s) | Forge finalisée |
| `combat:{combat_id}:result` | Rapport sérialisé (snapshots, rounds, XP, scars) | 600 s | Jamais (lecture seule) |
| `expedition:{exp_id}` | JSON expédition complète | 48 h | Résolution finale |
| `player_expeditions:{pid}` | SET d'expedition_ids actifs | 48 h | SREM à résolution |
| `ratelimit:{pid}:{tag}` | Sorted set sliding-window | 61 s | Auto |
| `emago:events:player:{id}` | Pub/sub channel | (transient) | — |

---

## 7. Indexes critiques pour scheduler & performance

| Index | Table | Usage |
|---|---|---|
| `idx_build_queue_planet_pending` partiel | build_queue | scheduler `build_tick` (10 s) |
| `idx_forge_queue_completed_at` partiel | forge_queue | scheduler `forge_tick` (60 s) |
| `idx_fleets_arrives_at` partiel | fleets | scheduler `fleet_arrival` (5 s) |
| `idx_ship_missions_ship_expires` partiel | ship_missions | requête missions actives |
| `idx_expedition_completes_at` partiel | expedition_logs | scheduler futur expédition |
| `idx_ships_owner_status` | ships | requête hangar (la plus fréquente) |
| `idx_ship_modules_ship_id` | ship_modules | calcul `current_stats` |
| `idx_players_score` (DESC) | players | classement |
| `idx_alliances_score` (DESC) | alliances | classement alliances |
| `idx_combat_logs_attacker` (timestamp DESC) | combat_logs | history 50 dernières |

---

## 8. Modèles SQLAlchemy 2.0 (annotations clés)

### Base type-mapping

```python
class Base(DeclarativeBase):
    type_annotation_map = {
        dict: JSONB,
        list: JSONB,
    }
```

Permet d'écrire `Mapped[dict]` au lieu de `Mapped[dict] = mapped_column(JSONB, ...)`.

### Convention enums

Chaque enum PostgreSQL a son miroir Python `str.Enum` dans `models.py` :

```python
class ShipClass(str, enum.Enum):
    ATTACK = "ATTACK"; DEFENSE = "DEFENSE"; SUPPORT = "SUPPORT"; EXPLORATION = "EXPLORATION"
```

Stocké en colonne `String` (pas `Enum`) pour faciliter les migrations futures sans `ALTER TYPE`.

### Relations notables

```python
# Ship
modules: Mapped[list["ShipModule"]] = relationship(back_populates="ship", cascade="all, delete-orphan")
scars: Mapped[list["ShipScar"]] = relationship(back_populates="ship", cascade="all, delete-orphan")
missions: Mapped[list["ShipMission"]] = relationship(back_populates="ship", cascade="all, delete-orphan")
parent: Mapped["Ship | None"] = relationship(remote_side="Ship.id", foreign_keys=[parent_ship_id])

# Fleet
ships: Mapped[list["Ship"]] = relationship(secondary="fleet_ships", viewonly=True)

# Alliance ↔ Player (FK circulaires)
members: Mapped[list["Player"]] = relationship("Player", back_populates="alliance", foreign_keys="Player.alliance_id")
leader: Mapped["Player"] = relationship("Player", foreign_keys=[leader_id], post_update=True)
```

---

## 9. Pool de connexions

```python
# database.py
engine = create_async_engine(DATABASE_URL,
    echo=DEBUG,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,    # détecte les connexions mortes
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,    # objets restent utilisables après commit
    autoflush=False,
    autocommit=False,
)
```

Pour `>500` joueurs simultanés : envisager pgBouncer (transaction pooling).

---

## 10. Améliorations BDD à prévoir

| Tâche | Priorité | Détail |
|---|---|---|
| Compléter `scar_tags` jusqu'à ~500 entrées | Moyenne | Migration 0002 actuellement 30 |
| Index JSONB sur `combat_logs.attacker_ships_snapshot` | Moyenne | Pour participation combat (TODO `combat.py:107`) |
| EXPLAIN ANALYZE sur `fleet_arrival`, `resource_tick`, hangar | Moyenne | Audit perf |
| Procédure de purge `combat_logs > 30 jours` | Basse | Archivage S3 ou DELETE |
| Partitionnement `combat_logs` par mois | Basse | Si volume > 1M lignes |
| Migration future `_active_research` (mémoire `tech.py`) → table `research_queue` | Haute | |
| Migration future expéditions Redis → table `expedition_logs` (déjà créée) | Basse | |
| Vérification `BYPASS_STATS_TRIGGER` en context Alembic | Haute | Tester en CI |
| Strat sharding pour > 10 000 joueurs | Basse | |
| Audit FK orphelines (planets owner_id NULL → player supprimé) | Basse | |

---

*Document Agent 7 — Mai 2026*
