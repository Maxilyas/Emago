---
name: emago-service-pattern
description: Implémente la logique métier d'une feature Emago dans un service Python (app/services/<feature>_service.py) en respectant les patterns du projet — AsyncSession via paramètre (pas AsyncSessionLocal direct), SELECT FOR UPDATE sur mutations, secrets.SystemRandom pour RNG, invalidation cache Redis après mutation, publish_event WS via canal player:{id}, transactions déléguées à l'appelant (router ou scheduler), type hints stricts, docstrings sur fonctions publiques. Met à jour docs/05_dev_backend.md. Use when l'utilisateur dit "implémenter service Emago", "logique métier pour", "service espionnage", "service marché", "ajoute la logique de", "code le service de".
license: MIT
metadata:
  author: Antoine
  version: 1.0.0
  project: emago
  agent: 5-dev-backend
---

# emago-service-pattern

Implémente des services métier FastAPI Emago cohérents avec l'architecture existante. Encapsule les patterns de `forge_service.py`, `combat_engine.py` et `ship_build_service.py`.

---

## Quand utiliser ce skill

- Implémenter la logique métier d'une nouvelle feature (espionnage, marché, artefacts…).
- Extraire de la logique métier d'un router vers un service (refactoring).
- Ajouter une fonction à un service existant.

## Quand NE PAS utiliser ce skill

- Pour le router FastAPI (endpoints, auth, validation) → utilise `emago-router-scaffold`.
- Pour la migration BDD → utilise `emago-migration-alembic` (Agent 7) AVANT.
- Pour le GDD de la mécanique → utilise `emago-gdd-writer` (Agent 2) AVANT.

---

## Instructions

### Étape 1 — Cadrer le service

Demande :
1. **Nom du service** (kebab-case → `<feature>_service.py`).
2. **Fonctions publiques** à implémenter (liste avec signature estimée).
3. **Tables BDD** impliquées (existantes ou nouvelles).
4. **Cache Redis** : keys à lire / écrire / invalider.
5. **Events WebSocket** à publier.
6. **Jobs scheduler** si traitement asynchrone (60s tick, arrivée de flotte…).

### Étape 2 — Vérifier les patterns existants

Avant de coder, lire les services similaires dans `app/services/` pour réutiliser les helpers :

| Helper | Source | Quand utiliser |
|---|---|---|
| `invalidate_ship_cache(ship_id)` | `ship_stats_service.py` | Après modification d'un ship |
| `invalidate_hangar_cache(player_id)` | `ship_stats_service.py` | Après build/forge/delete ship |
| `get_current_stats(db, ship)` | `ship_stats_service.py` | Pour lire les stats effectives |
| `publish_event(channel, event)` | `core/redis_client.py` | Events WS joueur |
| `get_redis()` | `core/redis_client.py` | Accès Redis direct |
| `generate_ship_name(class, rarity)` | `naming_service.py` | Nom procédural vaisseau |
| `roll_trait()` | `ship_trait_service.py` | Trait narratif vaisseau |

### Étape 3 — Conventions obligatoires

#### A. Session async — JAMAIS AsyncSessionLocal directement

```python
# ✅ Correct : session passée en paramètre
async def do_thing(db: AsyncSession, player_id: UUID, ...) -> dict:
    ...

# ❌ Interdit : session créée dans le service
async def do_thing(player_id: UUID) -> dict:
    async with AsyncSessionLocal() as db:  # ← jamais ici
        ...
```

La session est créée par le router via `DbDep` ou par le scheduler. Le service ne gère jamais la transaction.

#### B. SELECT FOR UPDATE sur mutations

```python
# Toujours verrouiller les ressources concurrentes
result = await db.execute(
    select(Planet)
    .where(Planet.id == planet_id)
    .with_for_update()
)
planet = result.scalar_one_or_none()
if not planet or planet.owner_id != player_id:
    raise HTTPException(404, "Planète introuvable.")
```

#### C. RNG avec secrets.SystemRandom

```python
import secrets

_srng = secrets.SystemRandom()  # module-level

# Usage
result = _srng.random()         # float [0, 1)
chosen = _srng.choice(items)    # tirage
rolled = _srng.randint(1, 100)  # entier
```

Jamais `random.random()` pour les décisions de jeu (reproductibles, exploitables).

#### D. Invalidation cache Redis après mutation ship

```python
from app.services.ship_stats_service import invalidate_ship_cache, invalidate_hangar_cache

# Après mutation d'un ship existant :
await invalidate_ship_cache(ship_id)

# Après ajout / suppression d'un ship :
await invalidate_hangar_cache(player_id)
```

#### E. Publish event WebSocket

```python
from app.core.redis_client import publish_event

await publish_event(
    channel=f"player:{player_id}",   # TOUJOURS ce format
    event={
        "type": "feature.action_done",
        "data": {
            "field": value,
            ...
        },
    },
)
```

Le channel est TOUJOURS `f"player:{UUID}"`. Le subscriber WebSocket forward au bon client.

#### F. Gestion des erreurs

```python
from fastapi import HTTPException, status

# Codes standard Emago :
raise HTTPException(status.HTTP_404_NOT_FOUND, "Ressource introuvable.")
raise HTTPException(status.HTTP_409_CONFLICT, "Statut incompatible.")
raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "Ressources insuffisantes.")
raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Validation échouée.")

# Pour les erreurs internes (scheduler) :
logger.error("Service X : erreur sur action Y : %s", exc, exc_info=True)
raise RuntimeError(f"Impossible de finaliser X : {exc}") from exc
```

#### G. Flush avant d'utiliser l'ID

```python
db.add(new_entity)
await db.flush()          # obtenir new_entity.id sans commit
# ... utiliser new_entity.id pour des INSERT liés
```

### Étape 4 — Structure du fichier

```python
"""
app/services/<feature>_service.py
Agent 5 — Développeur Backend

Responsabilité : [Description en 1 ligne]

Architecture (Agent 3, décision X) :
  - [Choix technique et justification]
"""
from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_client import get_redis, publish_event
from app.models.models import (...)
from app.services.ship_stats_service import invalidate_ship_cache, invalidate_hangar_cache

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
_CONSTANT = value

# ---------------------------------------------------------------------------
# Fonctions publiques
# ---------------------------------------------------------------------------

async def main_action(
    db: AsyncSession,
    player_id: uuid.UUID,
    ...
) -> dict[str, Any]:
    """
    Description claire de ce que fait la fonction.

    Raises:
        HTTPException 40X : [conditions].
    """
    ...

# ---------------------------------------------------------------------------
# Helpers privés
# ---------------------------------------------------------------------------

def _helper_fn(...) -> ...:
    """Description."""
    ...
```

### Étape 5 — Jobs scheduler (si asynchrone)

Si la feature nécessite un traitement différé (ex. arrivée de sonde d'espionnage) :

```python
async def run_<feature>_tick(db: AsyncSession) -> None:
    """Job APScheduler — appelé toutes les 60s."""
    now = datetime.now(UTC)
    pending = (await db.execute(
        select(FeatureQueue).where(
            FeatureQueue.arrives_at <= now,
            FeatureQueue.result.is_(None),
        )
    )).scalars().all()

    for entry in pending:
        try:
            await finalize_<feature>(db, entry)
            await db.commit()
        except Exception as exc:
            await db.rollback()
            logger.error("Erreur tick %s %s : %s", feature_name, entry.id, exc, exc_info=True)
```

Enregistrer dans `app/tasks/<feature>_tasks.py` et monter dans `app/main.py` lifespan.

### Étape 6 — Mettre à jour `docs/05_dev_backend.md` (obligatoire)

- Section 3 (Services) : ajouter le nouveau service avec ses fonctions publiques et leur rôle.
- Section 4 (Routers) : si un router délègue à ce service, mettre à jour la description.
- Si nouveau job scheduler : ajouter à la section 5 (APScheduler jobs).

---

## Examples

### Exemple 1 — Service espionnage

**User** : "Implémente le service d'espionnage : lancer une sonde, finaliser à l'arrivée"

**Actions** :
1. Cadrage : fonctions `launch_probe(db, player_id, target_planet_id, ship_ids)` + `finalize_probe(db, probe_entry)`.
2. Tables : `EspionageReport`, `Fleet` (mission ESPIONAGE), `Planet`, `Ship`.
3. Redis : pas de cache probe (données fraîches), invalider hangar si ship consommé.
4. WS : `espionage.report_ready` au prober après finalisation.
5. `launch_probe` : SELECT FOR UPDATE sur ships + deutérium, INSERT EspionageReport + Fleet, publish_event `espionage.launched`.
6. `finalize_probe` : calcul détection via `P = tech_def / tech_att`, populate result JSONB, publish_event `espionage.report_ready`, envoyer `espionage.detected` au défenseur si détecté.
7. `run_espionage_tick` : SELECT EspionageReport WHERE arrives_at <= now AND result IS NULL.
8. Met à jour `docs/05_dev_backend.md`.

### Exemple 2 — Extraction logique vers service

**User** : "La logique de production de ressources est dans planets.py, extrais-la dans un service"

**Actions** :
1. Identifie les fonctions dans `app/routers/planets.py` : `_calculate_production`, `_apply_production`.
2. Crée `app/services/production_service.py` avec ces fonctions + async session param.
3. Update `planets.py` pour importer depuis le service.
4. Docstring + type hints sur toutes les fonctions.
5. Met à jour `docs/05_dev_backend.md`.

---

## Troubleshooting

### Session utilisée après commit dans le scheduler

**Cause** : le scheduler fait `await db.commit()` dans la boucle, puis utilise encore `db`.
**Solution** : après un commit dans une boucle, la session est toujours utilisable (SQLAlchemy async réinitialise l'état). OK tant qu'on ne mix pas rollback et usage après.

### Event WS jamais reçu par le client

**Cause** : channel mal formé ou player_id différent de celui du WebSocket.
**Solution** : toujours `f"player:{player_id}"` avec l'UUID du joueur cible (pas le sender). Vérifier que `subscribe_player_events` est actif pour ce player_id.

### RNG non reproductible côté test

**Cause** : `secrets.SystemRandom` est par design non seedable.
**Solution** : dans les tests, mocker `_srng_<service>.choice` ou `_srng_<service>.random` via `unittest.mock.patch`.

---

## References

- `references/service_template.py` — template service complet avec toutes les conventions.
- `references/existing_services.md` — résumé des services existants et leurs patterns (forge, combat, ship_build, naming, trait).
- `references/redis_keys.md` — keys Redis Emago avec format, TTL, et quand invalider.
