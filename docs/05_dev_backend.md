# Agent 5 — Dev Backend

> Détail exhaustif des services métier, des 14 routers FastAPI, des 6 jobs APScheduler, du WebSocket, et des tests pytest.

---

## 1. Structure du projet backend

```
backend/
├── alembic/
│   ├── env.py
│   └── versions/
│       ├── 0001_initial_schema.py
│       ├── 0002_seed_scar_tags.py
│       ├── 0003_add_player_daily_data.py
│       ├── 0004_alliances.py
│       ├── 0005_expedition_logs_table.py
│       ├── 0006_ship_rpg_fields.py
│       ├── 0007_combat_logs_gin_index.py
│       └── 0008_ship_status_scrapped.py
├── app/
│   ├── main.py                    # FastAPI app + lifespan + CORS + routers + scheduler
│   ├── core/
│   │   ├── config.py              # Settings (pydantic-settings)
│   │   ├── database.py            # AsyncEngine + AsyncSessionLocal + get_db_dep
│   │   ├── deps.py                # CurrentPlayer, DbDep
│   │   ├── redis_client.py        # init_redis, publish_event
│   │   └── security.py            # bcrypt + JWT HS256
│   ├── middleware/
│   │   └── rate_limit.py          # Redis sliding-window
│   ├── models/
│   │   ├── models.py              # 13 tables principales
│   │   └── alliance_models.py     # AllianceMember, AllianceWar, enums
│   ├── routers/                   # 14 routers
│   ├── schemas/                   # auth, ship, forge (Pydantic)
│   ├── services/                  # logique métier
│   ├── tasks/                     # 6 jobs APScheduler
│   └── websocket/
│       ├── connection_manager.py  # Singleton mémoire
│       ├── handler.py             # /ws endpoint
│       └── subscribers.py         # Redis pub/sub bridge
├── tests/
│   ├── conftest.py
│   ├── services/test_ship_services.py
│   └── routers/{test_auth,test_ships,test_forge}.py
├── docker-compose.yml             # dev
├── docker-compose.prod.yml
├── Dockerfile                     # multi-stage
├── nginx/{nginx.conf, conf.d/emago.conf}
├── github/workflows/{ci.yml, cd.yml}
├── scripts/{install_vps.sh, backup_postgres.sh}
├── requirements.txt
└── .env / .env.example
```

---

## 2. Bootstrap (`app/main.py`)

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_redis()                      # connecte le pool Redis
    _register_jobs()                        # 6 jobs APScheduler
    scheduler.start()                       # AsyncIOScheduler(timezone="UTC")
    yield
    scheduler.shutdown(wait=False)
    await close_redis()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware,
    allow_origins=["http://localhost:5173"] if settings.DEBUG else settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"])
```

14 routers inclus avec préfixe `/api/v1`. Endpoint `/health` retourne 200/503 selon état DB+Redis (pour Uptime Kuma).

**Variable d'env CORS_ORIGINS** (production) : liste JSON ou séparée par virgules des origines autorisées. Ex : `CORS_ORIGINS=["https://emago.example.com"]`.

---

## 3. Services métier (résumé)

> **Note** : `ship_build_service_patch.py` a été supprimé — les champs `trait`, `name`, `is_drift` sont intégrés dans `ship_build_service.py` et le modèle SQLAlchemy.

### `ship_build_service.py` (447 lignes)

**Rôle** : fabrication d'un vaisseau. Tirage RNG rareté, génération `base_stats`, application optionnelle Pedigree, INSERT atomique avec lock planète.

Constantes clés :
- `_RARITY_THRESHOLDS` : `[0.55, 0.82, 0.94, 0.99, 1.00]` (cumulés).
- `_RARITY_MULT` : `1.00, 1.25, 1.55, 1.90, 2.40`.
- `_RARITY_SLOTS` : `(2,0), (3,0), (4,1), (5,2), (6,3)`.
- `_BASE_STATS_BY_CLASS` : tableau classe × stats (cf. doc Game Designer).
- `SHIP_TYPE_BUILD_COST` : 6 types × 3 ressources.
- `SHIP_SHIPYARD_REQUIREMENTS` : niveau chantier requis (1 à 4 selon type).
- `_srng = secrets.SystemRandom()` singleton.

Fonctions clés :
- `roll_rarity() -> str` : `r = _srng.random()`, comparaison avec thresholds.
- `generate_base_stats(class, rarity) -> dict` : `stat = base × mult + uniform(-0.10,+0.10) × (base × mult)`.
- `apply_pedigree_bonus(base_stats, parent_best_stat)` : `× 1.05` sur la meilleure stat.
- `build_ship(db, player_id, ship_type, planet_id, parent_ship_id?)` :
  - `SELECT FOR UPDATE` planète (HTTP 404 si pas owner).
  - `_check_and_deduct_resources` (HTTP 402 si insuffisant) — utilise `math.floor`.
  - Vérifie `shipyard_level >= SHIP_SHIPYARD_REQUIREMENTS[ship_type]` (HTTP 409).
  - `roll_rarity()` puis `generate_base_stats()`.
  - Si parent_ship_id : `_validate_pedigree_parent` (404/403/409) puis bonus.
  - INSERT Ship, `invalidate_hangar_cache(player_id)`.
  - Pas de commit (délégué au router).

### `ship_stats_service.py` (379 lignes)

**Rôle** : seul calculateur de `current_stats`. Cache Redis TTL 300 s.

Constantes :
- `_STAT_CAP_RATIO = 1.50` (cap absolu +150 %).
- `_GRADE_BONUS` : `0/0.05/0.10/0.15/0.22/0.30`.
- `GRADE_SHIELD_REGEN` : `0/0/0/0.02/0.02/0.02`.
- `GRADE_5_STEALTH_BONUS = 10.0`.
- `_MODULE_BOOST` : `{1:0.08, 2:0.14, 3:0.22, 4:0.32, 5:0.44}`.
- `_AFFINITY_MULT = 1.15`.
- `_PREMIUM_REQUIRED_LEVELS = {4, 5}`.
- `_STATS_TTL = 300`, `_HANGAR_TTL = 120`.

Fonctions :
- `get_current_stats(ship_id, db) -> dict` : Redis hit → loads ; miss → load ship + modules → compute → setex 300s.
- `_compute_current_stats(ship, modules)` :
  1. `after_grade[stat] = base × (1 + grade_mult)`.
  2. Bonus Grade 5 stealth absolu : `after_grade["stealth"] += 10` (cap 100).
  3. `module_boost_ratio[stat] += _MODULE_BOOST[level] × (_AFFINITY_MULT si match)`.
  4. `target = after_grade + base × boost_ratio` ; cap `base × 2.5`. Si dépassement → `cap_reached.append(stat)`.
- `validate_module_slot(ship, slot_index, level) -> (bool, str)` : check `total_slots`, `premium_slots = total - premium`. Niveaux 4/5 doivent avoir `slot_index >= premium_start`.
- `invalidate_ship_cache(ship_id)` / `invalidate_hangar_cache(player_id)` : `DEL` Redis.

### `combat_engine.py` (832 lignes — le plus volumineux)

**Rôle** : résolution complète d'un combat PvP (load, power, synergies, rounds, XP, scars, log, broadcast WS).

Constantes :
- `MAX_ROUNDS = 50`.
- `_BASE_XP` : `ATTACK_WIN=100, ATTACK_WIN_LOOT=80, DEFENSE_WIN=150, ALLIANCE=60, LOSS_SURVIVOR=40`.
- `_GRADE_THRESHOLDS` : `[(5, 40000), (4, 15000), (3, 6000), (2, 2000), (1, 500)]`.
- `GRADE_4_IMMUNITY_HP = 1`.
- `SCAR_HULL_LOSS_THRESHOLD = 0.75`, `SCAR_POWER_RATIO_THRESHOLD = 2.0`.
- `_SCAR_TAGS` : 10 tags en dur (en complément de la table BDD ~500 tags).

Dataclasses :
- `CombatShip` : ship_id, owner_id, ship_class, rarity, grade, base_hull, hull, hull_max, shield, shield_max, dps, shield_regen, support_aura, immunity_used, xp_earned, hull_start, alive.
  - `take_damage(raw)` : shield absorb d'abord, puis hull. Si destroyed et grade ≥ 4 sans immunity_used → hull = 1, immunity_used = True.
  - `regenerate_shield()` : `+ int(shield_max × shield_regen)`.
- `RoundResult` : round_number, attackers_before/after, defenders_before/after, synergies_applied, hits.

Fonctions clés :
- `_fleet_power(ships) -> float` : `Σ (dps × hull_max × (1 + shield/hull))`, plancher 1.0.
- `_compute_synergy_bonuses(ships, label)` : ATTACK+SUPPORT (DPS ×1.20), DEFENSE+SUPPORT (hull regen 5%/round), DEFENSE×3+ (shield_max ×1.15), ATTACK+EXPLO (logué).
- `_resolve_round(round_num, attackers, defenders, rng, att_support_bonus, def_support_bonus)` : tirs simultanés, cible aléatoire, `int(dps × uniform(0.90,1.10) × (1 + support_aura))`. Régen shield + hull repair.
- `_compute_differential_xp(base_xp, own_power, enemy_power) -> (xp, audit)` : formule `base × (1 + max(0, ratio - 1) × 2.5)`.
- `resolve_combat(db, attacker_fleet_id, defender_planet_id, attacker_ship_ids, defender_ship_ids, loot)` :
  1. `_load_ships`, `_build_combatants` (récup current_stats).
  2. Calcul powers.
  3. Synergies + auras.
  4. Seed combat → `random.Random(seed)`.
  5. Loop max 50 rounds, break si une face exterminée.
  6. Vainqueur calculé. XP par côté.
  7. Pour chaque ship : si détruit → `db.delete()` ; si survivant → update xp/grade/status DOCKED.
  8. Cicatrices : précharge `all_scar_tags` depuis BDD (SELECT ScarTag), `_should_earn_scar` → `ShipScar(tag_id=scar_tag.id)`.
  9. INSERT `CombatLog` (snapshots JSONB, rounds_log).
  10. `_broadcast_combat_events` HORS transaction : WS `combat.result` aux 2 owners, `ship.grade_up`, `ship.scar_earned`.

### `forge_service.py` (537 lignes)

**Rôle** : la Forge. Fusion 2 ships → rareté supérieure. Durée 8h. Coût ×3 build. Drift 5%.

Constantes :
- `_DRIFT_PROBABILITY = 0.05`, `_DRIFT_ELIGIBLE_STATS = ["hull", "shield", "dps", "speed"]`.
- `DRIFT_SCAR_TAG_CODE = "born_in_drift"`.
- `_RARITY_UPGRADE` : COMMON→UNCOMMON…→LEGENDARY (LEGENDARY absent).
- `_XP_TRANSFER_RATIO = 0.30`.
- `_FORGE_STATUS_TTL = 8*3600 + 600` (29 400 s).

Fonctions :
- `start_forge(db, player_id, ship_a_id, ship_b_id)` :
  - 400 si même ship.
  - SELECT FOR UPDATE 2 ships ORDER BY id (anti-deadlock).
  - 404 si manquants, 403 si owner ≠, 422 si type/rareté différents ou LEGENDARY, 409 si statut ≠ DOCKED ou pas planet_id.
  - SELECT FOR UPDATE planète, déduit ressources × 3.
  - Statut 2 parents → IN_FORGE, INSERT ForgeQueue (completed_at = now + 8h, **cost_metal/crystal/deuterium** valorisés depuis `forge_cost`).
  - `_store_forge_status(0%, player_id=player_id)` Redis (inclut le player_id dans le payload), invalidate_hangar_cache.
- `finalize_forge(db, forge_entry)` :
  - SELECT FOR UPDATE parents.
  - `new_rarity = _RARITY_UPGRADE[rarity]`.
  - `new_base_stats = _merge_best_stats(stats_a, stats_b)`.
  - 5 % drift : `apply_drift(stats)` → stat × 0.80, `is_drift = True`.
  - `new_name = generate_ship_name(class, rarity)` ; `new_trait = roll_trait()`.
  - `transferred_xp = int(max(xp_a, xp_b) × 0.30)`.
  - INSERT new Ship (status DOCKED, trait, name, is_drift).
  - Si drift : INSERT ShipScar tag `"born_in_drift"`.
  - Parents → status `ShipStatus.SCRAPPED`.
  - Invalidate cache parents (sinon stale stats).
  - WS `forge.complete` channel `player:{pid}` avec base_stats + slots + trait + name + is_drift.
- `run_forge_tick(db)` (job APScheduler 60 s) : SELECT ForgeQueue WHERE completed_at <= now AND result_ship_id IS NULL → `finalize_forge` puis commit.

Notes v1.1 : 7 corrections de bugs documentées dans le docstring (cf. doc services).

### `expedition_service.py` (324 lignes)

**Rôle** : missions autonomes 2h/6h/12h, RNG déterministe SHA-256.

Constantes :
- `DURATION_HOURS = {SHORT:2, MEDIUM:6, LONG:12}`.
- `DURATION_COST` : deutérium 500/1500/4000.
- `EXPEDITION_EVENTS` : 12 events pondérés (poids total 100). Détails dans Game Designer doc.

Fonctions :
- `_roll_event(seed)` : `int(sha256(seed)) % 100` → cumulatif sur events.
- `_roll_range(seed, key, rng)` : déterministe par seed+key.
- `resolve_expedition(exp_id, ship_ids, duration, db)` :
  - `lead_ship = max(ships, key=(grade, combat_xp))`.
  - Ressources × multiplier durée (0.6/1.0/1.8) ; ajout au homeworld avec cap capacity.
  - XP × multiplier durée (0.7/1.0/1.5) sur lead_ship.
  - Module drop logué (PAS persisté — TODO `player_module_inventory`).
  - Cicatrice avec `tag_id = 1` (TODO : lookup réel `EXPEDITION_SCAR_TAGS`).

### `naming_service.py` (112 lignes)

**Rôle** : génération `[Racine] [Qualificatif]` pour ships RARE+.

- 80 racines (Astraeus, Corvus, Vael, Eryndor, Kha, Fenrath, Obsidia…).
- 15 qualificatifs par classe (cf. Game Designer doc).
- 10 qualificatifs génériques (Ancien, Dernier, Premier, Ultime, Oublié…).
- Probabilité de doublon : `1 / (80 × 15) = 1/1200` par classe.

### `ship_trait_service.py` (562 lignes)

**Rôle** : pool de ~200 traits narratifs en 8 familles. Tirage à la fabrication, immuable.

Dataclasses :
- `TraitEffect(condition, stat?, bonus_pct, target, condition_class?)`.
- `ShipTrait(key, name, description, effect)`.

Fonctions :
- `roll_trait()` : `_srng.choice(_TRAITS)` → `{key, name, description}` (effet PAS sérialisé, ré-résolu via `TRAIT_INDEX`).
- `apply_trait_bonus(stats, trait_key, ship_class, fleet_size)` :
  - ALWAYS, SOLO (`fleet_size == 1`), FLEET_3PLUS (`>= 3`), CLASS_MATCH (`ship_class == cond_class`).
  - Si activé et stat dans dict : `result[stat] *= (1 + bonus_pct)`.

Détails des 8 familles dans la doc Game Designer.

~~`ship_build_service_patch.py`~~ — **Supprimé**. Était un fichier d'instructions temporaire. Le patch (champs `trait`, `name`, `is_drift`) est appliqué dans `ship_build_service.py` et la migration 0006.

---

## 4. Routers FastAPI (14 fichiers)

Tous montés avec préfixe `/api/v1`. Détails complets de chaque endpoint (validation, codes HTTP, transactions, cache) dans la doc Architecte. Voici les particularités :

### `auth.py`

3 endpoints :
- `POST /auth/register` : rate limit 5/min par IP, stocke `hash_refresh_token()` en `players.refresh_token`.
- `POST /auth/login` : rate limit 10/min par IP, 401 anti-énumération, met à jour le hash du refresh token.
- `POST /auth/refresh` : rate limit 30/min par IP ; vérifie que `sha256(incoming_token) == players.refresh_token` avant rotation. Token volé révoqué dès la prochaine rotation légitime.

Les trois endpoints utilisent `db: DbDep` (injection FastAPI) — pas d'`AsyncSessionLocal` direct. Commit/rollback délégués à `get_db_dep`.

`security.py` expose `hash_refresh_token(token: str) -> str` (SHA-256 hex).

### `ships.py` + `modules.py`

- `GET /ships` (liste hangar)
- `GET /ships/{id}` (détail + current_stats via service)
- `POST /ships/build` — **rate limit 10/min** par player_id via `check_rate_limit`
- `DELETE /ships/{id}` (404 owner masqué, 409 si pas DOCKED, FOR UPDATE)
- `GET/PUT/DELETE /ships/{id}/modules/{slot}` (404, 409 si IN_FORGE, 422 validation slot) — `PUT` **rate limit 30/min**

### `forge.py` (105 lignes)

- `POST /forge` (délègue à service) — **rate limit 5/min** par player_id
- `GET /forge/history` (50 dernières, ordre `started_at DESC`) — **AVANT** `/forge/{id}`
- `GET /forge/{id}` : cache Redis avec **vérification ownership** (`cached["player_id"] == str(player.id)`) — si absent du cache (entrées anciennes) → fallback BDD ; si player_id présent et différent → 404.

### `planets.py` (487 lignes)

Le plus gros router. Contient :
- `BUILDING_CONFIG` (6 bâtiments avec label, base_cost, build_time_base, icon, category, description, per_level, synergies, unlocks, tip).
- `_compute_rates`, `_apply_lazy_production`, `_create_homeworld`, `_planet_to_detail`.
- 4 endpoints : list (crée homeworld si absent), detail, build (FOR UPDATE planète, `math.floor` ressources), queue.
- **Commentaire critique** : « FIX : math.floor() pour éviter le bug d'arrondi. planet.metal peut valoir 1999.87, affiché 2000 → mais 1999.87 < 2000 → refus injuste. »

### `fleets.py` (382 lignes)

- `GET /fleets` (actives non rappelées) + `GET /fleets/incoming` (ennemis en approche) — **AVANT** `/{id}`
- `POST /fleets` — **rate limit 20/min** par player_id, FOR UPDATE ships, validation cargo, `text("INSERT INTO fleet_ships ...")`
- `DELETE /fleets/{id}` (rappel, ships → DOCKED, WS `fleet.recalled`)
- Helpers : `_compute_distance` (UA — galaxy diff ×20000, system diff ×5+1000, position diff ×5+100), `_fleet_speed` (min speeds × `FLEET_SPEED_BASE`).

### `combat.py` (189 lignes)

- `GET /combat/history` : filtre PostgreSQL JSONB `@>` sur `attacker_ships_snapshot` et `defender_ships_snapshot` — requête DB uniquement, plus de chargement Python.
- `GET /combat/{id}` : Redis cache `combat:{id}:result` TTL 600 s. Vérifie participation via helper `_is_participant`. 403 si pas participant, 404 si introuvable.

### `ranking.py` (74 lignes)

- `GET /ranking` (public, top N capé 500) — TODO ligne 53 : charger `alliance_tag` depuis relation.
- `GET /ranking/me` (rang via COUNT score >).

### `scars.py` (178 lignes)

- `GET /ships/{id}/scars` : visibles publiquement (tous joueurs).
- `GET /ships/{id}/missions` : owner only, 403 si Grade < 2.
- `POST /ships/{id}/missions/{mid}/claim` : owner, 409 si pas complétée ou déjà claim.

### `galaxy.py` (83 lignes)

- `GET /galaxy?galaxy=&system=` : 15 slots orbitaux, batch SELECT planets + usernames.

### `expeditions.py` (323 lignes)

- Stockage Redis (TTL 48h) — fix v2 critique (avant : dict Python en mémoire vidé au redémarrage Uvicorn).
- 5 endpoints : `/active`, `/history`, `/events` (public), `/launch`, `/{id}/result`.
- POST launch : 1-5 ships max, FOR UPDATE absent (TODO race condition), `math.floor` deutérium.

### `tech.py` (367 lignes)

- `TECH_TREE` : 14 techs en 4 classes, prérequis, coûts par niveau, bonus.
- **`_active_research: dict[str, dict]` en MÉMOIRE** — TODO ligne 212 : à migrer en BDD (perdu au redémarrage).
- 3 endpoints : `/tech/tree`, `/tech/research`, `/tech/research/complete`.

### `daily.py` (317 lignes)

- `STREAK_REWARDS` (jours 1-7), `MAX_STREAK_DAY = 7`.
- `MISSION_POOL` 8 missions, sélection déterministe `sha256(player + date) % 8 × 3` sans répétition.
- 4 endpoints : `/daily/status`, `/daily/login` (idempotent), `/daily/missions/{id}/claim`, `/daily/missions/{id}/progress`.

### `alliances.py` (470 lignes)

- Constantes : MAX_MEMBERS=20, MIN_SCORE=500, COST 10k métal + 5k cristal, WAR_MIN_DURATION=48h.
- Helpers : `_get_member`, `_require_role(min_role)`.
- 7 endpoints : list (public top 50), detail (public), create, join (admission directe v1), leave/kick, declare_war (LEADER + WS `alliance.war_declared`), declare_peace (≥48h, TODO v2 dual-leader).

---

## 5. Tâches asynchrones (APScheduler)

| Job | Fichier | Fréquence | Description |
|---|---|---|---|
| resource_tick | tasks/resource_tick.py | 60 s | Production métal/cristal/deut par planète. Formule `base × level × 1.1^level`, facteur énergie `min(1, prod/need)`. Skip si elapsed < 3.6 s. |
| build_tick | tasks/build_tick.py | 10 s | Finalise items `BuildQueue` dont `completes_at <= now`. SELECT FOR UPDATE planet. RESEARCH/SHIP non gérés. |
| fleet_arrival | tasks/fleet_arrival.py | 5 s | Dispatch par mission : ATTACK → `combat_engine.resolve_combat` ; TRANSPORT → ajoute cargo planète target ; ESPIONAGE/COLONIZE → stub. WS `fleet.arrived`. |
| forge_tick | tasks/forge_tick.py | 60 s | Wrapper minimal vers `forge_service.run_forge_tick(db)`. |
| ranking | tasks/ranking.py | 10 min | Recalcul score : `Σ(niveaux bâtiments) × 1000 + Σ(grades) × 500 + Σ(combat_xp × 0.1)`. N+1 queries (TODO optim). |
| immunity_reset | tasks/immunity_reset.py | 5 min | Réactive Grade 4 immunity 48h après reset_at. Invalide cache ship. |

---

## 6. WebSocket (3 fichiers)

### `connection_manager.py`

```python
class ConnectionManager:
    _connections: dict[UUID, list[WebSocket]] = defaultdict(list)
    
    async connect(ws, player_id)  → ws.accept() + register (usage interne uniquement)
    def   register(ws, player_id) → append sans accept (utilisé par handler.py)
    disconnect(ws, player_id)
    async send_to_player(player_id, message)  # nettoyage zombies
    async broadcast(message)
```

Singleton `manager`. Pour scale horizontal : à remplacer par broadcaster Redis pub/sub strict (déjà préparé via subscriber).

### `handler.py`

Flux de connexion sécurisé (token en premier message, pas dans l'URL) :

```python
@router.websocket("/ws")
async def websocket_endpoint(websocket):
    await websocket.accept()
    # Attendre {"type": "auth", "token": "..."} dans les 10s (4001 si timeout)
    msg = await asyncio.wait_for(ws.receive_text(), timeout=10)
    if msg["type"] != "auth" → close 4001
    decode_token(msg["token"])  # close 4001 si invalide
    player = SELECT Player      # close 4004 si absent
    manager.register(ws, player_id)  # register sans double accept
    sub_task = asyncio.create_task(subscribe_player_events(player_id))
    await ws.send_json({"type": "connected", ...})
    
    try:
        while True:
            msg = await ws.receive_text()
            await _handle_client_message(ws, json.loads(msg))
    finally:
        sub_task.cancel()
        manager.disconnect(ws, player_id)
```

**Sécurité** : le token n'est jamais dans l'URL `/ws` — il n'apparaît pas dans les logs nginx ni l'historique navigateur. Le frontend envoie `{"type": "auth", "token": "<jwt>"}` dans `onopen`.

Messages client supportés : `ping` → `pong`, `forge.poll` → `forge.status` (fallback si WS coupé pendant forge active).

### `subscribers.py` (54 lignes)

```python
async def subscribe_player_events(player_id):
    channel = f"emago:events:player:{player_id}"
    async with r.pubsub() as ps:
        await ps.subscribe(channel)
        async for message in ps.listen():
            if message["type"] == "message":
                event = json.loads(message["data"])
                await manager.send_to_player(player_id, event)
```

---

## 7. Schemas Pydantic

### `auth.py`
- `RegisterRequest` (username 3-32 alphanum + `_`, email, password ≥ 8).
- `LoginRequest`, `RefreshRequest`, `TokenResponse`.

### `ship.py`
- `BuildShipRequest` (ship_type, planet_id, parent_ship_id?).
- `InstallModuleRequest` (module_type, level 1-5).
- `BaseStatsOut`, `ModuleDetailOut`, `CurrentStatsOut`, `ShipSummaryOut`, `ShipDetailOut`, `BuildShipResponse`, `ModuleInstallResponse`.

### `forge.py`
- `ForgeStartRequest`, `ForgeStatusResponse`, `ForgeHistoryItem`.

---

## 8. Core (database, deps, redis, security)

### `database.py`
```python
engine = create_async_engine(DATABASE_URL,
    echo=DEBUG, pool_size=20, max_overflow=10, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(bind=engine,
    expire_on_commit=False, autoflush=False, autocommit=False)

async def get_db_dep():  # FastAPI Depends
    # commit auto, rollback exception, close finally
```

### `deps.py`
```python
DbDep = Annotated[AsyncSession, Depends(get_db_dep)]

async def get_current_player(credentials, db):
    payload = decode_token(token, expected_kind="access")  # 401 si invalide
    player = SELECT Player WHERE id = uuid(payload.sub)    # 401 si absent
    return player

CurrentPlayer = Annotated[Player, Depends(get_current_player)]
```

### `redis_client.py`
```python
async def init_redis():
    aioredis.from_url(REDIS_URL, encoding="utf-8",
        decode_responses=True, max_connections=50)
    await ping()

async def publish_event(channel, event):
    r.publish(f"emago:events:{channel}", json.dumps(event))
```

### `security.py`
```python
hash_password(plain) → bcrypt
verify_password(plain, hashed) → bool
create_token(subject, kind="access") → JWT HS256 ({sub, kind, iat, exp})
decode_token(token, expected_kind) → payload (raise ValueError → 401)
```

### `middleware/rate_limit.py`
Sliding window via Redis sorted set, pipeline atomique `ZREMRANGEBYSCORE → ZADD → ZCARD → EXPIRE`. Limites 60s :

| Tag | Limit |
|---|---:|
| ships:build | 10 |
| forge:start | 5 |
| fleets:send | 20 |
| auth:register | 5 |
| auth:login | 10 |
| modules:install | 30 |
| default | 120 |

429 + header `Retry-After: 60` si dépassement.

---

## 9. Tests pytest

### `conftest.py` (fixtures)

- `test_engine` (session) : drop_all + create_all sur `emago_test`.
- `db_session` : transaction par test, rollback.
- `client` : AsyncClient ASGI sans auth, override `get_db_dep`, mock Redis.
- `auth_client` : client + Bearer token créé.
- `registered_player` : Player aléatoire (`password123`).
- `planet_id` : Homeworld 50k/20k/10k.
- `built_ship` : POST /ships/build frigate_attack.
- `other_player_ship_id` : ship d'un autre joueur (test ownership).
- `ship_in_fleet` : ship status IN_FLEET.
- `two_ships_different_rarity` : COMMON + RARE.

### Tests services (`test_ship_services.py` — 47 tests)

Couvre : RNG rarity (300 tirages valid, distribution COMMON 0.45-0.65), generate_base_stats (fourchettes, ±10%, no negative, speed décimale, errors), Pedigree (boost correct, no mutation), find_best_stat (exclut stealth/aura), compute_current_stats (no modules, grade 1 +5%, grade 3 regen, cannon dps, affinity > non, cap 150% enforced, grade 5 stealth), validate_module_slot (valid/out_of_range/level4_premium), CombatShip.take_damage (shield_first, overflow, destroyed, immunity grade 4), differential XP (equal/stronger/weaker/audit), compute_grade (0-5), fleet_power, should_earn_scar, merge_best_stats, rarity_upgrade (full chain + LEGENDARY), XP transfer 30%.

### Tests routers

- `test_auth.py` : register success/dup_username/dup_email/invalid_email/short_username, login success/wrong_pwd/unknown_email/missing, refresh success/access_token_fails/invalid.
- `test_ships.py` : build success/insufficient/unknown_type/wrong_planet, list, get_detail, get_other_player (404 ownership masqué), modules install/invalid_slot/premium_in_standard/other_player_ship/remove.
- `test_forge.py` : different_rarities (422), same_ship (400), in_fleet (409), history, status_not_found.

---

## 10. Améliorations Backend à prévoir

| Tâche | Priorité | Localisation |
|---|---|---|
| Migrer `_active_research` en BDD | Haute | `tech.py` ligne 212 |
| Tests d'intégration combat (fleet→combat→XP→cicatrice) | Haute | `tests/routers/` |
| Tests d'intégration alliances | Haute | `tests/routers/` |
| Tests d'intégration WebSocket | Haute | `tests/` |
| ~~Index JSONB pour `combat_logs.attacker_ships_snapshot` participation~~ | ~~Moyenne~~ | ✅ FAIT — migration 0007, GIN jsonb_path_ops sur attacker et defender snapshot |
| ~~ShipStatus.SCRAPPED manquant + ForgeQueue sans cost_metal/crystal/deuterium~~ | ~~Haute~~ | ✅ FAIT — migration 0008 (index partiel ships actifs), enum complété, ForgeQueue valorisé |
| Charger `alliance_tag` dans ranking | Basse | `ranking.py` ligne 53 |
| Implémenter pool `EXPEDITION_SCAR_TAGS` (au lieu de `tag_id=1`) | Basse | `expedition_service.py` |
| Implémenter `module_drop` persistance (table inventory) | Haute | `expedition_service.py` |
| Implémenter `hull_damage` / `module_damage` flags expédition | Moyenne | `expedition_service.py` |
| Optim ranking job N+1 queries | Moyenne | `tasks/ranking.py` |
| Implémenter ESPIONAGE / COLONIZE missions | Haute | `tasks/fleet_arrival.py` |
| Spec phase 2 alliances dual-leader paix | Basse | `routers/alliances.py` |
| `with_for_update` sur `expeditions.launch`, `tech.start_research`, `alliances.create_alliance`, `daily.claim_daily_login` | Moyenne | divers routers |
| Heartbeat WS server-side | Moyenne | `websocket/handler.py` |
| Audit OWASP Top 10 + headers HTTP | Haute | global |

---

*Document Agent 5 — Mai 2026*
