---
name: emago-test-integration-writer
description: Génère les tests pytest d'intégration pour un router FastAPI Emago en utilisant les fixtures du conftest.py existant (auth_client, registered_player, planet_id, built_ship, other_player_ship_id, ship_in_fleet, two_ships_different_rarity). Couvre systématiquement les vecteurs d'attaque connus du projet — ownership 404 anti-énumération, double-soumission, statut invalide, ressources insuffisantes 402, validation 422, rate-limit 429. Sortie un fichier tests/routers/test_<router>.py avec classes TestXxx organisées par endpoint. Use when l'utilisateur dit "tests pytest pour", "tests intégration router", "couverture tests Emago", "test router alliances", "test endpoint /espionage".
license: MIT
metadata:
  author: Antoine
  version: 1.0.0
  project: emago
  agent: 8-qa-securite
---

# emago-test-integration-writer

Génère des tests pytest d'intégration cohérents avec l'écosystème de tests Emago. Couvre les vecteurs d'attaque documentés dans `docs/08_qa_securite.md` section 5.

---

## Quand utiliser ce skill

- Nouveau router créé, besoin des tests d'intégration → utilise après `emago-router-scaffold`.
- Router existant sans tests (cf. gaps section 5 de `docs/08_qa_securite.md`).
- Couverture sécurité à compléter (ownership masqué, double-soumission).
- Régression à reproduire en test après bug.

## Quand NE PAS utiliser ce skill

- Tests unitaires d'un service métier → utilise `emago-service-test-generator` (à venir) ou écris directement.
- Tests E2E (Cypress/Playwright) → pas géré par ce skill.
- Tests de charge → utilise `emago-load-test` (à venir) ou k6/locust direct.

---

## Instructions

### Étape 1 — Cadrer le router

Demande :
1. **Nom du router** (ex. `alliances`, `espionage`, `market`).
2. **Liste des endpoints** à tester (méthode + path).
3. **Statut actuel** : déjà des tests partiels ? Refonte complète ou ajout incrémental ?
4. **Dépendances** : autres routers/services testés (ex. tests alliances dépendent de `registered_player` + score ≥ 500) ?

### Étape 2 — Lire le router

Lis `app/routers/<name>.py` pour identifier :
- Les schémas Pydantic (request/response).
- Les codes d'erreur HTTP (401/402/403/404/409/422/429).
- Les helpers d'ownership (`_get_owned_*`, `_require_role`).
- Les transactions `with_for_update`.
- Les invalidations Redis.
- Les events WS publiés.
- Les TODO/FIXME.

### Étape 3 — Choisir les fixtures

Le `tests/conftest.py` Emago fournit déjà :

| Fixture | Quoi | Quand utiliser |
|---|---|---|
| `client` | AsyncClient ASGI sans auth | Endpoints publics (auth, ranking public) |
| `auth_client` | client + Bearer token | La plupart des endpoints authentifiés |
| `registered_player` | Player aléatoire avec mot de passe `password123` | Reuse pour login flow |
| `planet_id` | Homeworld 50k metal / 20k crystal / 10k deut, capacités 500k | Build/forge/research tests |
| `built_ship` | POST `/ships/build` frigate_attack → 201 | Tests qui ont besoin d'un ship existant |
| `other_player_ship_id` | Ship d'un AUTRE joueur | **Crucial** pour vecteur ownership 404 |
| `ship_in_fleet` | Ship status IN_FLEET | Tests qui doivent rejeter ce statut (409) |
| `two_ships_different_rarity` | ship_a COMMON + ship_b RARE | Tests forge rejection (422) |
| `db_session` | Session async avec rollback per test | Tests qui besoin de tweaker la BDD directement |

Si le router teste d'autres entités (alliances, expeditions), envisage **ajouter** des fixtures dans `conftest.py` plutôt que dupliquer.

### Étape 4 — Couverture obligatoire par endpoint

Pour CHAQUE endpoint, écrire au minimum :

#### Endpoints GET

- ☐ **happy path 200** : récupération basique, format réponse correct.
- ☐ **404 si ressource d'autrui** (ownership masqué) — utilise `other_player_ship_id`.
- ☐ **404 si ressource inexistante** (UUID random).
- ☐ **401 si token manquant** (utilise `client` au lieu de `auth_client`).

#### Endpoints POST

- ☐ **happy path 201** : création réussie avec response shape correct.
- ☐ **402 si ressources insuffisantes** (drainer planet_id avant le POST).
- ☐ **404 si ressource cible introuvable** (UUID random).
- ☐ **403 si ownership cross-player** sur ressource fournie en input (cf. forge avec ship d'autrui).
- ☐ **409 si statut conflit** (ship pas DOCKED, alliance pleine, déjà membre).
- ☐ **422 si validation Pydantic** (champ manquant, type invalide, regex tag).
- ☐ **429 si rate-limit** (si endpoint dans `_LIMITS` du middleware).

#### Endpoints PUT

- ☐ **happy path 200** + check side effect (e.g. `current_stats` updated, cap_reached signalé).
- ☐ **404 ownership masqué**.
- ☐ **409 statut bloquant** (ex. IN_FORGE → 409 sur PUT modules).
- ☐ **422 contrainte business** (ex. niveau 4-5 dans slot standard).

#### Endpoints DELETE

- ☐ **happy path 204** (No Content, pas de body).
- ☐ **404 ownership masqué**.
- ☐ **409 statut bloquant** (ex. ship pas DOCKED → 409 sur démolition).

### Étape 5 — Vecteurs sécurité spécifiques

Pour chaque router, vérifier les vecteurs spécifiques du projet (cf. `references/attack_vectors_checklist.md`) :

| Vecteur | Test à ajouter |
|---|---|
| **Double-soumission Forge** | `test_forge_double_submission` : 2 POST simultanés sur les mêmes ships → un seul réussit |
| **Manipulation base_stats** | Tenter UPDATE direct via SQL → trigger PG raise |
| **Cross-player WebSocket** | Connect WS playerA, vérifier qu'il NE reçoit PAS les events de playerB |
| **Énumération login** | login email inconnu vs mauvais MDP → même message 401, même temps de réponse |
| **Pedigree avec parent d'autrui** | POST /ships/build avec parent_ship_id d'un autre joueur → 403 |
| **Re-roll RNG** | Build N ships, vérifier distribution rareté ~ 55/27/12/5/1 (test statistique) |
| **JSONB injection** | POST avec payload JSON crafted contenant `'; DROP TABLE ships; --` → escape OK |

### Étape 6 — Structure du fichier

Toujours organiser comme dans les tests existants Emago :

```python
"""Tests d'intégration — router <name>."""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from uuid import uuid4

# Imports modèles si besoin de manipuler db_session directement
from app.models.models import ...


class TestList<Resource>:
    """GET /<resource>"""

    @pytest.mark.asyncio
    async def test_list_success(self, auth_client: AsyncClient, ...):
        ...

    @pytest.mark.asyncio
    async def test_list_no_auth(self, client: AsyncClient):
        ...


class TestCreate<Resource>:
    """POST /<resource>"""

    @pytest.mark.asyncio
    async def test_create_success(self, auth_client: AsyncClient, planet_id):
        ...

    @pytest.mark.asyncio
    async def test_create_insufficient_resources(self, auth_client, planet_id, db_session):
        # Drainer la planète
        ...

    @pytest.mark.asyncio
    async def test_create_other_player_resource(self, auth_client, other_player_ship_id):
        # Ownership masqué
        ...
```

Une classe `TestX` par endpoint, méthodes `test_<scenario>` claires.

### Étape 7 — Lister les fixtures à ajouter

Si le router introduit une nouvelle entité (alliance, espionage_report, market_offer), suggère d'ajouter dans `conftest.py` :

```python
@pytest.fixture
async def alliance_with_leader(db_session, registered_player) -> Alliance:
    """Alliance créée avec registered_player comme leader."""
    ...
```

Ne pas dupliquer la création dans chaque test — extraire en fixture.

### Étape 8 — Mettre à jour `docs/08_qa_securite.md`

Une fois les tests écrits, mettre à jour la table section 5 ("Tests à compléter") en cochant les items couverts.

---

## Examples

### Exemple 1 — Tests router alliances

**User** : "Génère les tests d'intégration pour app/routers/alliances.py"

**Actions** :
1. Lit le router, identifie 7 endpoints (list, get, create, join, leave/kick, declare_war, declare_peace).
2. Identifie les helpers `_get_member`, `_require_role` → tester role insuffisant 403.
3. Constantes _MAX_MEMBERS=20, _MIN_SCORE=500, _CREATE_COST=10k+5k → tests dédiés.
4. Suggère fixture nouvelle : `alliance_with_leader`, `alliance_full_20_members`.
5. Génère `tests/routers/test_alliances.py` avec ~40 tests :
   - TestListAlliances : success, public no-auth.
   - TestCreateAlliance : success, 409 already member, 403 score < 500, 409 dup name/tag, 404 no homeworld, 402 insufficient.
   - TestJoinAlliance : success, 409 already member, 409 full alliance, 404 unknown.
   - TestLeaveAlliance : self leave, kick by officer, 409 leader can't leave, 403 role insuffisant, 404 unknown member.
   - TestDeclareWar : success, 403 not leader, 400 self, 409 already active.
   - TestDeclarePeace : success ≥48h, 403 not leader, 404 unknown war, 409 < 48h.
   - TestAttackVectors : war_declared spam (rate-limit), join after kick (24h candidacy delay).

### Exemple 2 — Compléter un router existant

**User** : "Le router fleets a peu de tests, complète-les"

**Actions** :
1. Lit `tests/routers/test_fleets.py` (s'il existe).
2. Identifie les gaps vs checklist section 5 de `docs/08_qa_securite.md`.
3. Ajoute les tests manquants : `test_send_with_other_player_ship` (403), `test_send_with_in_flight_ship` (409), `test_recall_already_arrived` (409), `test_incoming_only_enemies`.

### Exemple 3 — Test régression

**User** : "On a eu un bug : un joueur a réussi à forger un ship in_fleet. Écris le test régression."

**Actions** :
1. Reproduit le bug : POST /forge avec un ship status IN_FLEET dans `ship_a_id`.
2. Génère `test_forge_in_fleet_ship_rejected` qui assert 409.
3. Suggère que ce test soit dans `tests/routers/test_forge.py` classe `TestForgeRegression`.

---

## Troubleshooting

### Fixture manquante

**Cause** : la fixture nécessaire n'existe pas dans `conftest.py`.
**Solution** : proposer son ajout dans `conftest.py`. Format attendu :
```python
@pytest.fixture
async def fixture_name(db_session, ...) -> Type:
    """Brief docstring."""
    obj = Type(...)
    db_session.add(obj)
    await db_session.flush()
    return obj
```

### Test asynchrone qui ne s'exécute pas

**Cause** : oubli `@pytest.mark.asyncio`.
**Solution** : décorer la méthode (ou marquer la classe). `pytest.ini` doit contenir `asyncio_mode = auto`.

### Mock Redis ne réagit pas comme attendu

**Cause** : le mock par défaut dans `_make_redis_mock()` du conftest renvoie des valeurs fixes.
**Solution** : passer un mock spécifique au test : `client.app.dependency_overrides[get_redis] = lambda: my_custom_mock`.

### Test cross-player demande créer un autre Player

**Cause** : seule fixture `registered_player` existe (un seul player).
**Solution** : utiliser `other_player_ship_id` qui crée déjà un Player + Ship pour les tests ownership. Ou créer une nouvelle fixture `second_player`.

### Trigger PG bloquant les fixtures qui modifient base_stats

**Cause** : trigger `prevent_base_stats_update` lève une exception.
**Solution** : dans la fixture, créer le Ship avec les `base_stats` directement à l'INSERT — ne jamais UPDATE après. OU utiliser session var bypass `await db.execute("SET LOCAL emago.bypass_stats_trigger = 'true'")`.

---

## References

- `references/conftest_fixtures.md` — fixtures disponibles + signatures.
- `references/attack_vectors_checklist.md` — checklist sécurité par type d'endpoint.
- `references/test_patterns.md` — extraits de tests existants (`test_auth.py`, `test_ships.py`, `test_forge.py`).
- `references/router_to_test_mapping.md` — table router → tests requis avec niveau de criticité.

## Scripts

- `scripts/scan_router.py` — parse un router Python et liste les endpoints + codes d'erreur, pour pré-remplir la checklist de tests à écrire.
