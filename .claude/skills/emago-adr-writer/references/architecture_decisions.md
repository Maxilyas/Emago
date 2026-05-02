# Décisions architecturales actées Emago

Extrait de `docs/03_architecte.md` section 2. Toute nouvelle décision (ADR) doit être cohérente avec ces décisions, ou les remplacer explicitement.

## Décisions structurantes

| # | Décision | Justification |
|---:|---|---|
| 1 | **Pile asynchrone end-to-end** : FastAPI / Starlette / asyncio + SQLAlchemy 2.0 async (asyncpg) + redis-py async | Performance + cohérence + tous les endpoints en `async def` |
| 2 | **Pool DB** : `pool_size=20, max_overflow=10, pool_pre_ping=True` | Adapté pour ~100-200 joueurs simultanés |
| 3 | **Pool Redis** : `max_connections=50` | Pub/sub + cache mutualisés |
| 4 | **Source de vérité = serveur** | Anti-triche : aucune logique de jeu côté client |
| 5 | **`current_stats` jamais stocké** : calculé à la volée + cache Redis TTL 300s | Évite désynchronisation après modules/grade |
| 6 | **Immuabilité `base_stats`** via trigger PostgreSQL `prevent_base_stats_update` BEFORE UPDATE | Garantie BDD imparable, contrainte applicative seule serait insuffisante |
| 7 | **RNG** : `secrets.SystemRandom()` pour build/forge/scar | Non prédictible, anti-triche |
| 8 | **RNG combat** : seed `random.Random(combat_seed)` | Rejouabilité possible (auditabilité combats) |
| 9 | **Scheduler** : APScheduler intégré FastAPI | Sur-ingénierie d'utiliser Celery pour <1000 joueurs |
| 10 | **WebSocket isolation** : channel `player:{id}` via Redis pub/sub | Permet scale horizontal futur |
| 11 | **Forge fallback** : polling REST si WS coupé | Robustesse réseau |
| 12 | **Expéditions storage** : Redis (TTL 48h) + index `player_expeditions:{pid}` | Fix v2 critique : avant en mémoire dict, vidé au redémarrage Uvicorn |
| 13 | **Combat outcome** : suppression définitive ships détruits | Simplifie + crée du poids tactique |
| 14 | **Auth** : JWT HS256 + rotation refresh | Stateless, scale facile |
| 15 | **Verrous pessimistes** : `SELECT FOR UPDATE` sur ships/fleets/planets | Anti-race conditions |
| 16 | **Anti-énumération** : 404 (pas 403) pour ressource d'autrui | Empêche découverte d'IDs |
| 17 | **Anti-énumération login** : même message 401 pour email inconnu vs mauvais MDP | Empêche découverte de comptes |
| 18 | **Codes erreur français** | Cohérence UX (locale FR) |
| 19 | **`math.floor(float(planet.X))`** pour comparer ressources | Fix bug arrondi 1999.87 vs 2000 |
| 20 | **Trigger BYPASS** : `SET LOCAL emago.bypass_stats_trigger = 'true'` | Réservé aux migrations Alembic contrôlées |

## Décisions explicitement écartées (avec ADR potentiels Phase 2/3)

| Option non retenue | Pourquoi (à date) | À réviser si |
|---|---|---|
| Celery + broker | Sur-ingénierie pour <1000 joueurs | Si on dépasse 1000 joueurs ou si on a besoin de retry distribué → ADR à venir |
| Multi-VPS api+db séparés | Complexité prématurée | À 500+ joueurs simultanés → ADR à venir |
| WebSocket sticky sessions Nginx ip_hash | Pas nécessaire en mono-process | Si scale-out plusieurs workers Uvicorn |
| Stocker `current_stats` en BDD | Risque désynchro | Jamais — décision figée |
| Sessions stateful | JWT scale mieux | Jamais — décision figée |
| Caddy v2 (vs Nginx) | Nginx déjà en place | À évaluer en Phase 3 si Caddy simplifie nettement |
| Loki + Grafana logs centralisés | Volume actuel ne le justifie pas | À envisager Phase 2C |
| pgBouncer | Pool DB suffit pour le moment | À 500+ joueurs simultanés |
| Sharding | Trop complexe avant 10k joueurs | Phase 4+ |

## Tableau de bord ADRs (à tenir à jour)

| ADR | Titre | Statut | Date |
|---|---|---|---|
| ADR-001 | Pile asynchrone Python | Accepted (rétroactif) | 2025-01 |
| ADR-002 | Trigger PG immuabilité base_stats | Accepted (rétroactif) | 2025-01 |
| ADR-003 | APScheduler vs Celery | Accepted | 2025-02 |
| ADR-004 | Redis pub/sub pour WebSocket | Accepted | 2025-03 |
| ADR-005 | Anti-énumération 404 vs 403 | Accepted | 2025-04 |
| ADR-006 | Suppression définitive ships détruits | Accepted | 2025-05 |
| … | (à venir) | | |

> **Note** : la table ci-dessus est indicative. À la première utilisation du skill, créer ces ADRs rétroactifs si pertinent pour formaliser l'historique.
