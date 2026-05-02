# 14 routers Emago existants — référence

Pour s'inspirer des patterns établis. Détails complets dans `docs/05_dev_backend.md` section 4.

## auth (97 lignes)
Préfixe `/auth`, tags `["auth"]`.
3 endpoints : register/login/refresh. **Pas d'auth requise** (endpoints publics).
- 409 si username/email dupliqué (register).
- 401 anti-énumération identique pour email inconnu et mauvais MDP (login).
- Rotation refresh+access tokens.

## ships (159 lignes)
Préfixe `/ships`, tags `["ships"]`.
4 endpoints : list, get, build, demolish.
- Helper `_get_owned_ship` 404.
- `with_for_update` sur démolition.
- Build délègue à `ship_build_service`.

## modules (164 lignes)
Préfixe `/ships`, tags `["modules"]` (réutilise préfixe ships).
3 endpoints : list, install (PUT), remove (DELETE).
- 409 si IN_FORGE, 422 si slot ou niveau invalide.
- Invalidation `ship:{id}:stats` après mutation.

## forge (105 lignes)
Préfixe `/forge`, tags `["forge"]`.
3 endpoints : start, history, status.
- ⚠️ `/history` AVANT `/{forge_id}` (ordre critique).
- Cache Redis lu d'abord, fallback BDD.
- Délègue à `forge_service.start_forge` + `get_forge_status`.

## planets (487 lignes — le plus gros)
Préfixe `/planets`, tags `["planets"]`.
4 endpoints : list, detail, build, queue.
- `BUILDING_CONFIG` enrichi inline (label, base_cost, build_time_base, icon, category, description, per_level, synergies, unlocks, tip).
- Helpers `_compute_rates`, `_apply_lazy_production`, `_create_homeworld`.
- ⚠️ `math.floor(float(planet.metal))` pour fix bug arrondi (commentaire ligne 419-422).

## fleets (382 lignes)
Préfixe `/fleets`, tags `["fleets"]`.
4 endpoints : list, incoming, send, recall.
- ⚠️ `/incoming` AVANT `/{fleet_id}`.
- `with_for_update` sur ships+fleet.
- Helpers `_compute_distance` (UA), `_fleet_speed`.
- INSERT fleet_ships via `text("INSERT INTO fleet_ships ...")` (SQLAlchemy async ne gère pas executemany).
- `publish_event` pour `fleet.recalled`.

## combat (189 lignes)
Préfixe `/combat`, tags `["combat"]`.
2 endpoints : history, get_report.
- ⚠️ `/history` AVANT `/{combat_id}`.
- Helper `_is_participant` vérifie owner_id dans snapshots JSONB.
- Cache Redis `combat:{id}:result` TTL 600s.
- 403 si pas participant, 404 si introuvable.
- TODO ligne 107 : index JSONB pour participation Phase 2.

## ranking (74 lignes)
Préfixe `/ranking`, tags `["ranking"]`.
2 endpoints : list (public), me.
- `/ranking` est **public** (pas de CurrentPlayer).
- `limit` capé à 500.
- TODO ligne 53 : charger `alliance_tag` depuis relation.

## scars (178 lignes)
Préfixe `/ships`, tags `["scars & missions"]`.
3 endpoints : list scars (public lecture), list missions (owner only), claim mission.
- Scars visibles par tous (intentionnel — narratif).
- Missions Grade ≥ 2 requis.

## galaxy (83 lignes)
Préfixe `/galaxy`, tags `["galaxy"]`.
1 endpoint : list slots.
- Lecture publique (mais auth requise).
- Batch SELECT planets + usernames pour optim.

## expeditions (323 lignes)
Préfixe `/expeditions`, tags `["expeditions"]`.
5 endpoints : active, history, events (public), launch, result.
- ⚠️ `/active`, `/history`, `/events` AVANT `/{id}/result`.
- ⚠️ Stockage **Redis** (TTL 48h) et non BDD (fix v2 critique).
- `_save_expedition`, `_get_expedition`, `_update_expedition` helpers.
- Publish WS via `publish_event` au launcher.

## tech (367 lignes)
Préfixe `/tech`, tags `["tech"]`.
3 endpoints : tree, research, complete.
- `TECH_TREE` global (14 techs en 4 classes).
- `_active_research: dict` **EN MÉMOIRE** (TODO ligne 212 : migrer en BDD — perdu au redémarrage).
- Bonus permanents par classe.

## daily (317 lignes)
Préfixe `/daily`, tags `["daily"]`.
4 endpoints : status, login, claim mission, progress.
- `STREAK_REWARDS` cycle 7 jours.
- `MISSION_POOL` 8 missions, sélection déterministe sha256.
- `/daily/login` idempotent (200 si déjà claim aujourd'hui).

## alliances (470 lignes)
Préfixe `/alliances`, tags `["alliances"]`.
7 endpoints : list (public), get (public), create, join, leave/kick, declare_war, declare_peace.
- Constantes `_MAX_MEMBERS=20, _MIN_SCORE_TO_CREATE=500, _CREATE_COST=10k+5k, _WAR_MIN_DURATION=48h`.
- Helpers `_get_member`, `_require_role(min_role)` 403.
- `publish_event` pour `alliance.war_declared`.
- TODO docstring : phase 2 dual-leader peace.

## Patterns récurrents

### Helper ownership
Dans 80% des routers : `_get_owned_<resource>` qui lève 404.

### Routes statiques avant paramétrées
- forge : `/history` avant `/{id}`.
- combat : `/history` avant `/{id}`.
- fleets : `/incoming` avant `/{id}`.
- expeditions : `/active`, `/history`, `/events` avant `/{id}/result`.

### Délégation au service
- ships → ship_build_service, ship_stats_service.
- forge → forge_service.
- expeditions → expedition_service.
- combat → combat_engine.

### Endpoints publics (sans auth)
- auth/* (par nature).
- /ranking (top public).
- /alliances (top public).
- /alliances/{id} (détail public).
- /expeditions/events (catalogue).
- /galaxy (lecture publique entre joueurs).

### Cache Redis
- `combat:{id}:result` (TTL 600s).
- `forge:{id}:status` (via service).
- `expedition:{id}` + `player_expeditions:{pid}` (TTL 48h).
- `ship:{id}:stats`, `player:{pid}:hangar` invalidations.

### publish_event
- `fleet.recalled` (fleets/recall).
- `alliance.war_declared` (alliances/declare_war).
- `forge.complete` (depuis forge_service.finalize_forge).
- `combat.result`, `ship.grade_up`, `ship.scar_earned` (depuis combat_engine).
- `fleet.arrived` (depuis tasks/fleet_arrival).

## Routers Phase 2 à créer

| Router | Endpoints prévus | Notes |
|---|---|---|
| espionage | POST /probe, GET /reports, GET /detection | Sondes + détection adverse |
| market | GET /offers, POST /offers, DELETE /offers/{id}, POST /offers/{id}/accept | Marché galactique |
| profile | GET /profile, GET /profile/{player_id} | Stats publiques d'un joueur |
| messages (Phase 3) | POST /messages, GET /messages, DELETE /messages/{id} | Messagerie alliance |
