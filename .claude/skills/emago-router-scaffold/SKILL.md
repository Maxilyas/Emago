---
name: emago-router-scaffold
description: Génère un nouveau router FastAPI Emago en respectant toutes les conventions du projet — préfixe /api/v1/<name>, deps CurrentPlayer + DbDep, helper _get_owned_<resource> qui lève 404 anti-énumération (jamais 403), codes d'erreur en français (401/402/403/404/409/422/429), routes statiques avant paramétrées (cf. /forge/history avant /forge/{id}), with_for_update sur mutations ressources, math.floor(float(planet.X)) pour comparer ressources (anti-bug arrondi 1999.87), invalidation Redis cache, publish_event WS via canal player:{id}, délégation logique métier au service. Sortie un fichier app/routers/<name>.py prêt à inclure dans main.py. Use when l'utilisateur dit "scaffold router Emago", "crée endpoint", "nouveau router pour", "ajoute /espionage", "ajoute /market", "router profil joueur".
license: MIT
metadata:
  author: Antoine
  version: 1.0.0
  project: emago
  agent: 5-dev-backend
---

# emago-router-scaffold

Économise des heures sur chaque nouvel endpoint Emago en encapsulant toutes les conventions FastAPI du projet — sécurité, transactions, cache, WebSocket, codes erreur cohérents.

---

## Quand utiliser ce skill

- Ajouter un nouveau router complet (espionnage, marché galactique, profil…).
- Étendre un router existant avec un nouvel endpoint complexe (forge avec sub-resource, alliances avec war specifics).
- Refondre un router pour aligner sur les conventions actuelles.

## Quand NE PAS utiliser ce skill

- Pour la logique métier elle-même → utilise `emago-service-pattern`.
- Pour les tests pytest du router → utilise `emago-test-integration-writer` (à exécuter après).
- Pour la migration BDD si nouvelles tables → utilise `emago-migration-alembic` AVANT.

---

## Instructions

### Étape 1 — Cadrer le router

Demande à l'utilisateur :

1. **Nom kebab-case** (ex. `espionage`, `market`, `profile`).
2. **Liste des endpoints** (méthode + path + 1 phrase description).
3. **Schéma BDD** : table existante ou nouvelle (et migration faite) ?
4. **Service métier** : il existe ou à créer ?
5. **Auth requise** par défaut oui ; spécifier si endpoint public.
6. **Events WebSocket** à publier ?
7. **Rate-limit** : endpoint sensible (ajouter au middleware) ?

### Étape 2 — Vérifier les conventions Emago

Cf. `references/router_template.py` pour la structure complète. Les règles non négociables :

#### A. Ordre des routes

**Routes statiques AVANT routes paramétrées** :
```python
@router.get("/history")     # ← AVANT
@router.get("/active")      # ← AVANT
@router.get("/{forge_id}")  # ← APRÈS
```

Sinon FastAPI tente de parser `"history"` comme UUID → 422.

#### B. Auth & deps

```python
from app.core.deps import CurrentPlayer, DbDep

@router.get("")
async def list_resources(player: CurrentPlayer, db: DbDep) -> list[ResourceOut]:
    ...
```

#### C. Helper ownership masqué (CRITIQUE)

```python
async def _get_owned_<resource>(<id>: UUID, player_id: UUID, db: AsyncSession) -> <Type>:
    """Lève 404 si introuvable OU pas owner — anti-énumération."""
    res = (await db.execute(
        select(<Type>).where(<Type>.id == <id>)
    )).scalar_one_or_none()
    if not res or res.owner_id != player_id:
        raise HTTPException(status_code=404, detail="<Resource> introuvable.")
    return res
```

**JAMAIS 403** pour ressource d'autrui — toujours 404. Le 403 est réservé au cas où l'utilisateur sait déjà que la ressource existe (ex. forge avec parent d'autrui passé en input explicit).

#### D. Codes d'erreur en français

```python
raise HTTPException(status_code=404, detail="Vaisseau introuvable.")
raise HTTPException(status_code=409, detail=f"Impossible de démolir un vaisseau {status}.")
raise HTTPException(status_code=402,
    detail=f"Ressources insuffisantes. Requis : métal={m}, cristal={c}, deutérium={d}. "
           f"Disponible : métal={am}, cristal={ac}, deutérium={ad}.")
raise HTTPException(status_code=422, detail="Module niveau IV/V réservé aux slots premium.")
```

#### E. Transactions avec FOR UPDATE

```python
# Toute mutation ressources (ships, planets, fleets) :
planet = (await db.execute(
    select(Planet).where(Planet.id == planet_id).with_for_update()
)).scalar_one_or_none()

if not planet or planet.owner_id != player.id:
    raise HTTPException(status_code=404, detail="Planète introuvable.")
```

#### F. Comparaison ressources (math.floor)

```python
import math

def _check_resources(planet: Planet, cost: dict[str, int]) -> None:
    """Compare ressources avec math.floor pour éviter bug arrondi (1999.87 vs 2000)."""
    available = {
        "metal": math.floor(float(planet.metal)),
        "crystal": math.floor(float(planet.crystal)),
        "deuterium": math.floor(float(planet.deuterium)),
    }
    if any(available[k] < cost.get(k, 0) for k in cost):
        raise HTTPException(status_code=402,
            detail=f"Ressources insuffisantes. Requis : {cost}. Disponible : {available}.")
```

#### G. Délégation au service

Le router NE contient PAS la logique métier. Il :
1. Valide les inputs Pydantic.
2. Vérifie l'auth + ownership.
3. Délègue à `<feature>_service.action()`.
4. Sérialise la réponse.

```python
@router.post("/probe", status_code=201)
async def launch_probe(
    body: ProbeRequest,
    player: CurrentPlayer,
    db: DbDep,
) -> ProbeResponse:
    """Lance une sonde d'espionnage."""
    return await espionage_service.launch_probe(
        db=db,
        player_id=player.id,
        target_planet_id=body.target_planet_id,
        ship_ids=body.ship_ids,
    )
```

#### H. Cache Redis

Après mutation ressource :
```python
from app.services.ship_stats_service import invalidate_ship_cache, invalidate_hangar_cache

await invalidate_ship_cache(ship_id)        # `ship:{id}:stats`
await invalidate_hangar_cache(player.id)    # `player:{pid}:hangar`
```

#### I. Publish event WS

```python
from app.core.redis_client import publish_event

await publish_event(
    channel=f"player:{owner_id}",
    event={
        "type": "espionage.report_ready",
        "data": {
            "report_id": str(report.id),
            "target_username": target.username,
            ...
        }
    }
)
```

Channel TOUJOURS `f"player:{id}"` — le subscriber WebSocket forwarde au bon client.

### Étape 3 — Générer le code

Utilise `references/router_template.py` comme base. Liste les endpoints à scaffold.

Pour chaque endpoint, applique la checklist. Si tu n'es pas sûr d'un point → faire référence à un router existant similaire (cf. `references/existing_routers.md`).

### Étape 4 — Inclure dans `main.py`

```python
# app/main.py
from app.routers import (
    auth, ships, modules, forge, planets, fleets,
    combat, ranking, scars, galaxy, expeditions, tech, daily, alliances,
    espionage,  # ← nouveau
)

# Plus loin :
app.include_router(espionage.router, prefix="/api/v1")
```

### Étape 5 — Mettre à jour les docs

- `docs/05_dev_backend.md` section 4 (liste des routers).
- `docs/03_architecte.md` section 3 (contrats API).
- Si nouveaux events WS : section 5 de `03_architecte.md`.

### Étape 6 — Suggestions enchaînées

Une fois le router créé, suggère :
1. **`emago-test-integration-writer`** pour les tests pytest.
2. **`emago-attack-vector-audit`** pour valider la sécurité.
3. **`emago-screen-spec`** + **`emago-page-scaffold`** pour le frontend.

---

## Examples

### Exemple 1 — Router espionnage

**User** : "Scaffold le router /espionage avec POST /probe (lancer sonde) et GET /reports (voir rapports)"

**Actions** :
1. Vérifie : table `espionage_reports` existe (sinon → flag à Agent 7 pour migration).
2. Génère `app/routers/espionage.py` :
   - Préfixe `/espionage`, tags `["espionage"]`.
   - Helper `_get_owned_report(report_id, player_id, db)` → 404 si pas owner.
   - `POST /probe` : valide ships DOCKED + deutérium (avec `math.floor`), `with_for_update` sur deutérium et ships, INSERT `EspionageReport`, INSERT `Fleet` (mission ESPIONAGE), publish_event WS au launcher.
   - `GET /reports` : SELECT ordered by launched_at DESC, limit 50.
   - Rate-limit `_LIMITS["espionage:probe"] = 5/min`.
3. Inclut dans `main.py`.
4. Suggère `emago-test-integration-writer` pour les ~12 tests à écrire.

### Exemple 2 — Endpoint complémentaire forge

**User** : "Ajoute POST /forge/{id}/cancel pour annuler une forge en cours"

**Actions** :
1. Localise `app/routers/forge.py`.
2. Ajoute endpoint **avant** `/forge/{forge_id}` (qui est paramétré GET) ou **après** vu que méthode différente.
3. Body : pas requis.
4. Helper réutilise `_get_owned_forge` ou similaire.
5. Logique :
   - SELECT FOR UPDATE forge_queue + 2 ships.
   - 409 si déjà completed.
   - 409 si > 50% du temps écoulé (anti-abuse).
   - Restaurer status ships à DOCKED.
   - Refund 50% des ressources.
   - Publish_event WS `forge.cancelled`.
6. Code 200 (pas 204 car retourne info refund).

### Exemple 3 — Refonte router existant

**User** : "Refonds /tech avec gestion BDD au lieu de mémoire (TODO `_active_research` ligne 212)"

**Actions** :
1. Lit `app/routers/tech.py` actuel.
2. Identifie : `_active_research: dict` en mémoire perdu au redémarrage.
3. Suggère migration `0007_research_queue` créant la table.
4. Refonds le router :
   - SELECT FOR UPDATE sur `research_queue` au lieu du dict.
   - Service `tech_service` extrait du router (logique métier).
5. Tests régression à ajouter : `test_research_persists_after_restart`.

---

## Troubleshooting

### Conflit entre `/{id}` et `/static`

**Cause** : routes paramétrées avant statiques.
**Solution** : déclarer toujours statiques (`/history`, `/active`, `/incoming`) AVANT `/{id}`.

### Race condition sur création

**Cause** : deux requêtes simultanées (forge double-submission, alliance same name).
**Solution** : `select(...).with_for_update()` sur la ressource à protéger ; transaction unique.

### 404 vs 403 confusion

**Question** : quand 404 et quand 403 ?

| Cas | Code | Pourquoi |
|---|---:|---|
| GET ship d'autrui | 404 | Ne rien révéler sur l'existence (anti-énumération) |
| GET dans une alliance dont on n'est pas leader | 403 | OK, le user sait que l'alliance existe (top public) |
| POST avec ID d'un autre ship (forge parent) | 403 | Le user a explicitement fourni l'ID, donc il sait qu'il existe |
| Ranking, alliances list | (200) | Public, pas d'auth nécessaire |

### Bug "ressources insuffisantes" alors qu'il devrait y avoir assez

**Cause** : comparaison float sans `math.floor` (1999.87 affiché 2000 dans UI mais < 2000 strict).
**Solution** : toujours `math.floor(float(planet.metal))` pour comparer aux coûts entiers.

### Frontend reçoit pas l'event WS

**Cause** : channel mal formé ou pub/sub différent.
**Solution** : toujours `await publish_event(channel=f"player:{owner_id}", event=...)`. Vérifier que `subscribe_player_events(owner_id)` est bien actif côté client (instancié par AppLayout au login).

### Trigger PG bloque mon update

**Cause** : tentative de modifier `base_stats`.
**Solution** : `base_stats` est immuable par design. Si vraiment nécessaire (cas migration), utiliser `SET LOCAL emago.bypass_stats_trigger = 'true'` au sein d'une transaction explicite.

---

## References

- `references/router_template.py` — template Python complet prêt à copier.
- `references/checklist.md` — checklist exhaustive à appliquer avant de merger.
- `references/existing_routers.md` — exemples des 14 routers Emago (auth, ships, forge, alliances…).
- `references/error_codes_emago.md` — convention codes HTTP + messages français.
- `references/redis_keys.md` — clés Redis Emago à invalider selon le type de mutation.
