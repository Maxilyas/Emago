# Agent 3 — Architecte système

> Architecture complète, contrats API REST, événements WebSocket, stratégie Redis, décisions techniques justifiées.

---

## 1. Architecture globale

```
┌─────────────────────────────────────────────────────────────┐
│  Client React (Vite + TS + Zustand + TanStack Query)        │
│  ├── REST  (axios via lib/api.ts → /api/v1/*)               │
│  └── WS    (useGameSocket.ts → /ws?token=<jwt>)             │
└──────────────────────────┬──────────────────────────────────┘
                           │
                  Internet (HTTPS 443)
                           │
                  ┌────────▼─────────┐
                  │  Nginx           │
                  │  - SSL term.     │
                  │  - WS upgrade    │
                  │  - Static React  │
                  │  - gzip + HSTS   │
                  └────────┬─────────┘
                           │
                  ┌────────▼─────────────────────────────────┐
                  │  FastAPI (Uvicorn 4 workers)             │
                  │                                          │
                  │  Routers (14)         WebSocket          │
                  │  ├── auth             /ws?token          │
                  │  ├── ships            ConnectionManager  │
                  │  ├── modules          (singleton mémoire)│
                  │  ├── forge            Subscriber Redis   │
                  │  ├── planets          pub/sub            │
                  │  ├── fleets                              │
                  │  ├── combat                              │
                  │  ├── ranking          APScheduler        │
                  │  ├── scars            (6 jobs):          │
                  │  ├── galaxy           - resource_tick 60s│
                  │  ├── expeditions      - build_tick 10s   │
                  │  ├── tech             - fleet_arrival 5s │
                  │  ├── daily            - forge_tick 60s   │
                  │  └── alliances        - ranking 10min    │
                  │                       - immunity_reset 5m│
                  │                                          │
                  │  Services (logique métier)               │
                  │  ├── ship_build_service                  │
                  │  ├── ship_stats_service                  │
                  │  ├── combat_engine                       │
                  │  ├── forge_service                       │
                  │  ├── expedition_service                  │
                  │  ├── naming_service                      │
                  │  └── ship_trait_service                  │
                  └──────┬───────────────────────┬───────────┘
                         │                       │
                  ┌──────▼──────┐         ┌──────▼──────┐
                  │ PostgreSQL  │◄────────┤   Redis 7   │
                  │ 16          │         │  - Cache    │
                  │ - 13 tables │         │  - Pub/sub  │
                  │ - 7 enums   │         │  - Expé/    │
                  │ - 2 triggers│         │    forge    │
                  │ - 18+ index │         │  - Ratelimit│
                  └─────────────┘         └─────────────┘
```

---

## 2. Décisions techniques majeures

### Pile asynchrone end-to-end

- **Backend** : FastAPI / Starlette / asyncio + SQLAlchemy 2.0 async (asyncpg) + redis-py async.
- **Pool DB** : `pool_size=20, max_overflow=10, pool_pre_ping=True`.
- **Pool Redis** : `max_connections=50`.
- **Tous les endpoints sont `async def`**, pas de threadlocal, pas de blocking I/O.

### Source de vérité = serveur

- Toute la logique de jeu est validée serveur. Le client n'effectue **aucun calcul de jeu**.
- `current_stats` jamais stocké en BDD. Calculé à la volée par `ship_stats_service.get_current_stats(ship_id, db)`.
- Cache Redis `ship:{id}:stats` TTL 300 s, invalidé sur mutation modules / grade.
- Le RNG côté client est purement décoratif (animations).

### Immuabilité base_stats

- **Trigger PostgreSQL** `prevent_base_stats_update` BEFORE UPDATE sur `ships`.
- Lève `EXCEPTION integrity_constraint_violation` si `NEW.base_stats != OLD.base_stats` ET que la session n'a pas `SET LOCAL emago.bypass_stats_trigger = 'true'`.
- Bypass réservé aux migrations Alembic contrôlées.
- Une contrainte applicative seule serait insuffisante.

### Source de RNG

- Build / forge / scar pick / trait pick : `secrets.SystemRandom()` — entropie OS, non prédictible, non seedable.
- Combat rounds : seed sauvegardé `combat_seed = SystemRandom().randint(0, 2^32-1)` + `random.Random(seed)` → rejouabilité possible.

### Scheduler

- **APScheduler** intégré au processus FastAPI (pas Celery). Sur-ingénierie pour <1000 joueurs.
- Lifecycle : `init_redis() → _register_jobs() → scheduler.start() → ... → scheduler.shutdown(wait=False) → close_redis()`.
- Tous les jobs : `max_instances=1, coalesce=True` (anti-doublon, anti-rattrapage).

### Redis pub/sub vs in-memory

- `ConnectionManager` est un singleton mémoire (par process). Multi-onglets supporté.
- `subscribe_player_events(player_id)` ouvre un pubsub Redis sur `emago:events:player:{id}` ; à chaque message, forward au client via `manager.send_to_player(...)`.
- Les services publient via `publish_event(channel, event)` → `r.publish("emago:events:" + channel, json)`.
- Cette indirection permet au scale horizontal multi-processus : tout worker reçoit les events relatifs à ses sockets.

### Verrous pessimistes

- `SELECT ... FOR UPDATE` utilisé dans : `ships.demolish_ship`, `fleets.send_fleet`, `fleets.recall_fleet`, `planets.build_building`, `forge_service.start_forge` (sur 2 ships ordre IDs triés + planète), `forge_service.finalize_forge` (parents).
- Absent (race condition possible, à corriger) : `expeditions.launch`, `tech.start_research`, `alliances.create_alliance`, `daily.claim_daily_login`.

---

## 3. Contrats API REST

Préfixe global : `/api/v1`. Auth : `Authorization: Bearer <jwt access>`. Les détails par endpoint sont dans [`05_dev_backend.md`](./05_dev_backend.md). Synthèse ici.

### 3.1 auth

| Méthode | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | Non | Crée un compte → tokens |
| POST | `/auth/login` | Non | Authentifie → tokens |
| POST | `/auth/refresh` | Non (refresh dans body) | Rotation refresh + access |

### 3.2 ships / modules

| Méthode | Path | Auth | Description |
|---|---|---|---|
| GET | `/ships` | Oui | Liste hangar |
| GET | `/ships/{id}` | Oui | Détail + current_stats |
| POST | `/ships/build` | Oui | Construction (RNG + pedigree optionnel) |
| DELETE | `/ships/{id}` | Oui | Démolition (Pedigree si Grade ≥ 3) |
| GET | `/ships/{id}/modules` | Oui | Liste modules installés |
| PUT | `/ships/{id}/modules/{slot}` | Oui | Installer / remplacer |
| DELETE | `/ships/{id}/modules/{slot}` | Oui | Retirer |

### 3.3 forge

| Méthode | Path | Auth | Description |
|---|---|---|---|
| POST | `/forge` | Oui | Lance fusion 8h |
| GET | `/forge/history` | Oui | 50 dernières (toujours AVANT `/forge/{id}`) |
| GET | `/forge/{id}` | Oui | Statut depuis Redis (fallback BDD) |

### 3.4 planets

| Méthode | Path | Auth | Description |
|---|---|---|---|
| GET | `/planets` | Oui | Liste (crée homeworld si aucune) |
| GET | `/planets/{id}` | Oui | Détail + production lazy + queue |
| POST | `/planets/{id}/build` | Oui | Lance construction bâtiment |
| GET | `/planets/{id}/queue` | Oui | File de construction |

### 3.5 fleets

| Méthode | Path | Auth | Description |
|---|---|---|---|
| GET | `/fleets` | Oui | Flottes actives |
| GET | `/fleets/incoming` | Oui | Flottes ennemies en approche |
| POST | `/fleets` | Oui | Envoi flotte |
| DELETE | `/fleets/{id}` | Oui | Rappel (avant arrivée) |

### 3.6 combat

| Méthode | Path | Auth | Description |
|---|---|---|---|
| GET | `/combat/history` | Oui | 50 derniers (joueur participant) |
| GET | `/combat/{id}` | Oui | Rapport (cache Redis 600s) |

### 3.7 ranking / scars / galaxy

| Méthode | Path | Auth | Description |
|---|---|---|---|
| GET | `/ranking` | **Non** | Top 100 (cap 500) |
| GET | `/ranking/me` | Oui | Rang du joueur |
| GET | `/ships/{id}/scars` | Oui (lecture publique) | Cicatrices |
| GET | `/ships/{id}/missions` | Oui (owner) | Missions actives (Grade ≥ 2) |
| POST | `/ships/{id}/missions/{mid}/claim` | Oui (owner) | Claim récompense |
| GET | `/galaxy?galaxy=&system=` | Oui | 15 slots orbitaux |

### 3.8 expeditions

| Méthode | Path | Auth | Description |
|---|---|---|---|
| GET | `/expeditions/active` | Oui | Actives (Redis) |
| GET | `/expeditions/history` | Oui | Terminées |
| GET | `/expeditions/events` | **Non** | Catalogue events |
| POST | `/expeditions/launch` | Oui | Lance expé (Redis 48h) |
| GET | `/expeditions/{id}/result` | Oui | Résultat |

### 3.9 tech / daily

| Méthode | Path | Auth | Description |
|---|---|---|---|
| GET | `/tech/tree` | Oui | Arbre + état |
| POST | `/tech/research` | Oui | Lance recherche |
| POST | `/tech/research/complete` | Oui | Finalise |
| GET | `/daily/status` | Oui | Streak + missions |
| POST | `/daily/login` | Oui | Claim login (idempotent) |
| POST | `/daily/missions/{id}/claim` | Oui | Récompense mission |
| POST | `/daily/missions/{id}/progress` | Oui | Update progression |

### 3.10 alliances

| Méthode | Path | Auth | Description |
|---|---|---|---|
| GET | `/alliances` | **Non** | Top 50 |
| GET | `/alliances/{id}` | **Non** | Détail |
| POST | `/alliances` | Oui | Création (10k métal + 5k cristal, score ≥ 500) |
| POST | `/alliances/{id}/join` | Oui | Rejoindre (admission directe v1) |
| DELETE | `/alliances/{id}/members/{pid}` | Oui | Quitter (soi) ou expulser (officer+) |
| POST | `/alliances/{id}/wars` | Oui (leader) | Déclarer la guerre |
| DELETE | `/alliances/{id}/wars/{wid}` | Oui (leader) | Déclarer la paix (≥48h) |

### 3.11 health

| Méthode | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | Non | Check DB + Redis (200 ok / 503 dégradé) |

---

## 4. Codes d'erreur HTTP — convention

| Code | Sémantique Emago |
|---:|---|
| 400 | Donnée invalide (ship_type inconnu, ship_a == ship_b, mission inconnue) |
| 401 | Token absent / expiré / mauvais kind / login invalide |
| 402 | Ressources insuffisantes (`Payment Required` détourné) |
| 403 | Owner ≠ joueur quand on ne veut pas masquer (forge parents, alliance role) |
| 404 | Resource introuvable. **Aussi utilisé pour masquer un ship d'un autre joueur** (anti-énumération) |
| 409 | Conflit d'état (ship pas DOCKED, déjà en queue, déjà membre alliance) |
| 422 | Validation Pydantic (slot invalide, level non compatible, rareté différente, etc.) |
| 429 | Rate limit dépassé (header `Retry-After: 60`) |
| 500 | Erreur serveur (rollback automatique) |
| 503 | `/health` dégradé (DB ou Redis KO) |

### Convention sécurité

- **Ownership masqué** : un GET sur un ship qui n'appartient pas au joueur retourne **404 NOT FOUND**, pas 403 (anti-énumération).
- **Anti-énumération login** : email inconnu et mauvais mot de passe renvoient le même message 401.

---

## 5. Événements WebSocket

Endpoint : `ws://host/ws?token=<jwt access>`

### Connexion

```
Client → ws.connect(token)
Serveur → decode_token(token, expected="access")
       → SELECT Player (4004 si absent)
       → manager.connect(ws, player_id)
       → asyncio.create_task(subscribe_player_events(player_id))
       → send {"type": "connected", "data": {"player_id": "..."}}
       → loop: receive_text → _handle_client_message
```

Codes de fermeture : `4001` token invalide, `4004` joueur introuvable.

### Messages Client → Serveur

| Type | Payload | Effet |
|---|---|---|
| `ping` | `{}` | Réponse `{"type": "pong"}` |
| `forge.poll` | `{"forge_id": "uuid"}` | Réponse `{"type": "forge.status", "data": ForgeStatusResponse}` ou `{forge_id, error: "introuvable"}` |
| (autre) | | `{"type": "error", "detail": "Type de message inconnu : ..."}` |

JSON invalide → `{"type": "error", "detail": "JSON invalide."}` (boucle continue).

### Messages Serveur → Client

| Event | Déclencheur | Données clés |
|---|---|---|
| `connected` | Connexion établie | `player_id` |
| `pong` | Réponse à ping | (vide) |
| `forge.status` | Réponse à forge.poll | `forge_id, completed_at, progress_pct, eta_seconds, result_ship_id` |
| `forge.complete` | Scheduler finalise (8h) | `forge_id, new_ship_id, rarity, base_stats, combat_xp, slots_total, slots_premium, trait, name, is_drift` |
| `combat.result` | Combat résolu | `combat_id, winner, total_rounds, attacker_power, defender_power, ships_lost{att,def}, xp_diff{ship_id:int}, loot, grade_ups[], scars[], synergies` |
| `ship.grade_up` | Seuil XP franchi | `ship_id, owner_id, old_grade, new_grade, combat_xp` |
| `ship.scar_earned` | Survie cicatrice | `ship_id, owner_id, tag` |
| `fleet.arrived` | Flotte arrive | `fleet_id, mission, target_planet_id` |
| `fleet.recalled` | Rappel par joueur | `fleet_id` |
| `alliance.war_declared` | Leader déclare guerre | `attacker_id, defender_id, war_id, declared_at` |

### Convention canal Redis pub/sub

```
emago:events:player:{player_id}    # cible un joueur précis
emago:events:planet:{planet_id}    # (réservé phase 2)
emago:events:alliance:{alliance_id}# (réservé phase 2)
```

Tous les events serveur passent par `publish_event(channel, dict)` → JSON sur Redis. Le subscriber WS local reçoit et forward.

---

## 6. Stratégie Redis

| Clé | Contenu | TTL | Invalidation |
|---|---|---:|---|
| `ship:{ship_id}:stats` | `current_stats` JSON | 300 s | PUT/DELETE modules, grade_up, fin de forge, démolition |
| `player:{player_id}:hangar` | Liste `[{id,rarity,class,grade,status}]` | 120 s | build, demolish, forge complete |
| `forge:{forge_id}:status` | `{progress_pct, eta_seconds, ...}` | 8h+10min (29 400 s) | Forge complete |
| `combat:{combat_id}:result` | Rapport sérialisé | 600 s | Jamais (lecture seule) |
| `expedition:{exp_id}` | JSON expé complet | 48 h | Résolution finale |
| `player_expeditions:{pid}` | SET d'expedition_ids actifs | 48 h | SREM à résolution |
| `ratelimit:{pid}:{tag}` | Sorted set sliding-window | 61 s | Auto |
| `emago:events:*` | Pub/sub uniquement | (transient) | — |

---

## 7. Schéma de données — synthèse

13 tables, 7 enums PostgreSQL. Détails dans [`07_base_de_donnees.md`](./07_base_de_donnees.md).

```
players ←─ planets ←─ build_queue
   ↓          ↓
   ├── ships ←─ ship_modules
   ├── ships ←─ ship_scars ←─ scar_tags
   ├── ships ←─ ship_missions
   ├── ships ↔  fleet_ships ↔  fleets
   ├── technologies (1:1)
   ├── alliance_members ←─ alliances
   ↓
forge_queue (ship_a, ship_b, result_ship)
combat_logs (snapshots JSONB)
alliance_wars (attacker_id, defender_id)
expedition_logs (ship_ids JSONB, result JSONB)
```

Triggers :
- `prevent_base_stats_update` BEFORE UPDATE on ships.
- `set_updated_at` BEFORE UPDATE on ships (`NEW.updated_at = now()`).

---

## 8. Particularités d'architecture

### Ordre des routes dynamiques

Plusieurs routers placent les routes statiques AVANT les routes paramétrées pour éviter les conflits de parsing FastAPI :
- `/forge/history` AVANT `/forge/{id}`
- `/combat/history` AVANT `/combat/{id}`
- `/fleets/incoming` AVANT `/fleets/{id}`
- `/expeditions/active`, `/history`, `/events` AVANT `/expeditions/{id}/result`

### Boucle async safe-by-default

- Tous les endpoints en `async def`.
- `get_db_dep` (FastAPI Depends) ouvre une session, commit en fin de requête, rollback sur exception, close en finally.
- Auth headers via `HTTPBearer(auto_error=True)` → `get_current_player(credentials, db)` retourne le `Player` ou raise 401.
- Type alias : `DbDep`, `CurrentPlayer` pour signatures compactes.

### Scheduler de production (APScheduler)

Lifecycle FastAPI :
```python
@asynccontextmanager
async def lifespan(app):
    await init_redis()
    _register_jobs()  # 6 jobs
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)
    await close_redis()
```

Les 6 jobs (tous `coalesce=True, max_instances=1`) :

| Job | Fréquence | Fichier |
|---|---|---|
| resource_tick | 60 s | tasks/resource_tick.py |
| build_tick | 10 s | tasks/build_tick.py |
| fleet_arrivals | 5 s | tasks/fleet_arrival.py |
| forge_tick | 60 s | tasks/forge_tick.py |
| ranking | 10 min | tasks/ranking.py |
| immunity_reset | 5 min | tasks/immunity_reset.py |

---

## 9. Points de vigilance pour les autres agents

### Pour Agent 5 (Backend)

- Toute opération qui consomme des ressources ET modifie `ships` doit être dans **une seule transaction** PostgreSQL avec `SELECT ... FOR UPDATE`.
- `ship_stats_service.get_current_stats(ship_id)` est l'**unique** fonction qui calcule `current_stats`. Lit Redis, recalcule si miss, invalide après mutation.
- La formule XP différentielle est **systématiquement loggée** dans `combat_logs.rounds_log` (auditable).
- Cap +150 % vérifié dans `ship_stats_service` ET retourné dans `ModuleInstallResponse.cap_reached`.

### Pour Agent 6 (Frontend)

- Le client ne calcule **jamais** `current_stats`. Il affiche `GET /ships/{id}.current_stats`.
- Interpolation locale (compteurs ressources) est cosmétique. La vérité = `GET /planets/{id}` (avec lazy production).
- Polling forge `GET /forge/{id}` est le fallback si WS coupé (toutes les 30 s en dev). En nominal : `forge.complete` via WS.
- Rareté lue depuis le champ API. Jamais inférée côté client.

### Pour Agent 7 (BDD)

- Index obligatoires (déjà en place) : `forge_queue.completed_at` partiel WHERE `is_completed = FALSE`, `ships.owner_id+status`, `ship_modules.ship_id`.
- Trigger `prevent_base_stats_update` couvre aussi les UPDATE en masse. Bypass via `SET LOCAL emago.bypass_stats_trigger = 'true'`.

### Pour Agent 8 (QA & Sécurité)

- **Vecteurs critiques traités** : ownership 404 vs 403, double-spend Forge (SELECT FOR UPDATE 2 ships ordre tri), immuabilité base_stats (trigger PG), JWT kind expected, anti-énumération login.
- **À surveiller** : routes sans `with_for_update` (expeditions/launch, tech/research, alliances/create, daily/login), filtrage participation combat en Python (lent à scale, voir TODO ligne 107 combat.py).

### Pour Agent 9 (DevOps)

- WebSocket : Nginx doit proxifier les headers `Upgrade` et `Connection` correctement (cf. `nginx/conf.d/emago.conf`).
- Le scheduler tourne **dans le process FastAPI** : 1 instance suffit. Si scale-out vers plusieurs workers Uvicorn, externaliser le scheduler (Celery beat ou pgcron).

---

## 10. Améliorations à prévoir

| Tâche | Priorité | Notes |
|---|---|---|
| Spec endpoints Phase 2 (espionnage, marché) | Haute | |
| Migration `_active_research` (mémoire) → BDD | Haute | Perdu au redémarrage Uvicorn |
| Index JSONB pour participation combat | Moyenne | `combat.py` ligne 107 |
| Charger `alliance_tag` dans ranking | Basse | `ranking.py` ligne 53 |
| Stratégie multi-VPS (api + db séparés) à 500 joueurs | Basse | |
| WebSocket sticky sessions / Redis pub/sub strict pour scale | Basse | |
| Heartbeat WS côté serveur (timeout détection) | Moyenne | |
| Audit perf complet (EXPLAIN ANALYZE) | Moyenne | Surtout fleet_arrival, ranking, hangar |
| Spec Phase 2 alliances (chat, sous-guildes) | Basse | |

---

*Document Agent 3 — Mai 2026*
