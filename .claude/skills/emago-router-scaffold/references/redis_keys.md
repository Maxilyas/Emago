# Clés Redis Emago — convention & invalidation

Source : `docs/03_architecte.md` section 6 + `docs/07_base_de_donnees.md` section 6.

## Clés actuelles

| Clé | Contenu | TTL | Quand invalider |
|---|---|---:|---|
| `ship:{ship_id}:stats` | `current_stats` JSON complet | 300 s | PUT/DELETE modules, grade_up, fin de forge, démolition |
| `player:{player_id}:hangar` | Liste `[{id, rarity, class, grade, status}]` | 120 s | build, demolish, forge complete |
| `forge:{forge_id}:status` | `{forge_id, completed_at, progress_pct, eta_seconds, result_ship_id?}` | 8h+10min (29 400 s) | Forge finalisée |
| `combat:{combat_id}:result` | Rapport sérialisé complet | 600 s | Jamais (lecture seule) |
| `expedition:{exp_id}` | JSON expédition complète | 48 h | Résolution finale |
| `player_expeditions:{pid}` | SET d'expedition_ids actifs | 48 h | SREM à résolution |
| `ratelimit:{pid}:{tag}` | Sorted set sliding-window | 61 s | Auto |

## Pub/sub (channels)

```
emago:events:player:{player_id}      # cible un joueur précis
emago:events:planet:{planet_id}      # (réservé phase 2)
emago:events:alliance:{alliance_id}  # (réservé phase 2)
```

## Conventions de naming

```
<resource_type>:{id}[:<aspect>]
```

Exemples :
- `ship:{uuid}:stats` — l'aspect "stats" du ship.
- `forge:{uuid}:status` — l'aspect "status" de la forge.
- `player:{uuid}:hangar` — la liste hangar du joueur.

## Helpers à utiliser

```python
# app/services/ship_stats_service.py
from app.services.ship_stats_service import (
    get_current_stats,        # lit cache + recalcule si miss
    invalidate_ship_cache,    # DEL ship:{id}:stats
    invalidate_hangar_cache,  # DEL player:{pid}:hangar
)

# app/core/redis_client.py
from app.core.redis_client import get_redis, publish_event

# Lecture/écriture cache générique
r = get_redis()
cached = await r.get(key)
if cached:
    return json.loads(cached)
# ... compute ...
await r.setex(key, TTL, json.dumps(value))
```

## Quand invalider — par action

### Action : POST /ships/build
```python
await invalidate_hangar_cache(player.id)
# Pas besoin d'invalidate_ship_cache : le ship vient d'être créé, pas en cache encore
```

### Action : DELETE /ships/{id}
```python
await invalidate_ship_cache(ship_id)
await invalidate_hangar_cache(player.id)
```

### Action : PUT /ships/{id}/modules/{slot}
```python
await invalidate_ship_cache(ship_id)
# Le hangar n'a pas besoin (pas de stats dans la liste)
```

### Action : POST /forge (start)
```python
await invalidate_hangar_cache(player.id)
# 2 ships passent en IN_FORGE — le hangar est obsolète
# Status forge stocké via _store_forge_status
```

### Action : forge.complete (scheduler)
```python
await invalidate_ship_cache(ship_a_id)  # parent (status SCRAPPED)
await invalidate_ship_cache(ship_b_id)  # parent (status SCRAPPED)
await invalidate_hangar_cache(player_id)  # nouveau ship + parents disparus
# Status forge à 100 % via _store_forge_status
```

### Action : combat.result (combat_engine)
```python
# Pour chaque ship survivant ayant changé de grade :
await invalidate_ship_cache(ship_id)

# Pas de cache global combat — chaque combat a son cache permanent (jamais invalidé) :
await r.setex(f"combat:{combat_id}:result", 600, json.dumps(report))
```

### Action : grade_up / shield_regen
```python
# Géré par combat_engine après combat
await invalidate_ship_cache(ship_id)
```

### Action : expedition launch / résolution
```python
# Stockage actif :
key = f"expedition:{exp_id}"
await r.setex(key, 48*3600, json.dumps(exp_data))

# Indexation par joueur :
await r.sadd(f"player_expeditions:{player_id}", exp_id)
await r.expire(f"player_expeditions:{player_id}", 48*3600)

# À la résolution :
await r.set(key, json.dumps(updated_exp))
# (TTL préservé)
```

## Pub/sub publish — par event

| Event WS | Channel | Payload type |
|---|---|---|
| `forge.complete` | `player:{owner_id}` | ForgeCompleteData |
| `combat.result` | `player:{att_owner}`, `player:{def_owner}` | CombatResultData |
| `ship.grade_up` | `player:{owner_id}` | GradeUpData |
| `ship.scar_earned` | `player:{owner_id}` | ScarEarnedData |
| `fleet.arrived` | `player:{owner_id}` | FleetArrivedData |
| `fleet.recalled` | `player:{owner_id}` | `{fleet_id}` |
| `alliance.war_declared` | `player:{member_id}` × N membres défenseur | `{attacker_id, defender_id, war_id, declared_at}` |

Code type :
```python
await publish_event(
    channel=f"player:{owner_id}",
    event={"type": "espionage.report_ready", "data": {...}},
)
```

`publish_event` préfixe automatiquement `emago:events:`.

## Clés Redis prévues Phase 2

| Clé | Contenu | TTL |
|---|---|---:|
| `espionage:{report_id}` | Rapport d'espionnage sérialisé | 24h |
| `player_espionage:{pid}` | SET reports reçus | 24h |
| `market:offers:active` | Cache top offres marché | 60s |
| `market:offer:{id}` | Détail offre | 60s |
| `notification:{nid}` | Notification non-lue | 7 jours |

## Anti-patterns

### ❌ Cache sans TTL
```python
await r.set(key, value)  # JAMAIS expire — risque mémoire
```

### ❌ Cache des données utilisateur sans isolation
```python
key = "ships_list"  # MAUVAIS — partagé entre joueurs
key = f"player:{pid}:ships"  # BON
```

### ❌ Oubli d'invalidation après mutation
```python
# Mutation ship sans invalidate → stats stales en cache
ship.combat_xp += 100
await db.flush()
# OUBLI : await invalidate_ship_cache(ship.id)
```

### ❌ Invalidation excessive
```python
# Pour chaque ship du joueur ?
for ship in player.ships:
    await invalidate_ship_cache(ship.id)
# MIEUX : invalidate_hangar_cache uniquement (les stats sont calculées à la demande)
```

### ❌ Utiliser Redis pour persistence critique
```python
# MAUVAIS — la donnée doit être en BDD aussi
await r.set("player:123:gold", 5000)  # perdu si Redis crash sans persistence
```

Redis = cache + pub/sub + queue. PostgreSQL = source de vérité.
