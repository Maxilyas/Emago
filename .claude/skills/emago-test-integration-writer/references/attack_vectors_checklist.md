# Checklist vecteurs d'attaque Emago — par type d'endpoint

Pour chaque endpoint d'un router, vérifier les cases pertinentes. Source : `docs/08_qa_securite.md` section 2.

## Vecteurs CRITIQUES (toujours tester si applicable)

### V1 — Ownership masqué (404 vs 403)

**Cas** : un joueur tente d'accéder à une ressource appartenant à un autre joueur.

**Test attendu** :
```python
async def test_<endpoint>_other_player_resource(self, auth_client, other_player_ship_id):
    res = await auth_client.<METHODE>(f"/api/v1/<path>/{other_player_ship_id}")
    assert res.status_code == 404  # PAS 403 (anti-énumération)
    assert "introuvable" in res.json()["detail"].lower()
```

S'applique à : tous les endpoints qui prennent un `<id>` de ressource appartenant à l'utilisateur (ships, planets, fleets, scars/missions, forge, combat, expeditions).

### V2 — Double-soumission (race condition)

**Cas** : deux requêtes simultanées qui consomment la même ressource (ex. forge qui débite ressources × 3, ou alliance create qui réserve un nom).

**Test attendu** :
```python
import asyncio

async def test_<endpoint>_double_submission(self, auth_client, ...):
    # Lance 2 POST simultanés
    res1, res2 = await asyncio.gather(
        auth_client.post("/api/v1/forge", json={"ship_a_id": ..., "ship_b_id": ...}),
        auth_client.post("/api/v1/forge", json={"ship_a_id": ..., "ship_b_id": ...}),
    )
    # Un seul réussit, l'autre 409 ou 404 (le ship a changé de status)
    statuses = sorted([res1.status_code, res2.status_code])
    assert statuses == [201, 409] or statuses == [201, 404]
```

S'applique à : `POST /forge`, `POST /ships/build`, `POST /alliances`, `POST /tech/research`, `POST /expeditions/launch`.

### V3 — Manipulation `base_stats` (trigger PG)

**Cas** : tentative de modifier `base_stats` après création.

**Test attendu** :
```python
async def test_base_stats_immutable(self, db_session, built_ship):
    ship = await db_session.get(Ship, built_ship["ship_id"])
    ship.base_stats = {"hull": 9999}  # tentative triche
    db_session.add(ship)
    with pytest.raises(Exception, match="immutable|integrity_constraint"):
        await db_session.flush()
```

### V4 — Anti-énumération login

**Cas** : message d'erreur identique pour email inconnu vs mauvais mot de passe.

**Test attendu** :
```python
async def test_login_unknown_email_same_message(self, client):
    res1 = await client.post("/api/v1/auth/login", json={"email": "x@x.com", "password": "wrong"})
    res2 = await client.post("/api/v1/auth/login", json={"email": "y@y.com", "password": "wrong"})
    # Même status, même détail
    assert res1.status_code == res2.status_code == 401
    assert res1.json()["detail"] == res2.json()["detail"]
```

### V5 — Token JWT expiré rejeté

**Test attendu** :
```python
async def test_expired_token_rejected(self, client):
    expired = create_token("any-id", "access")
    # Manipuler exp pour le rendre expiré, ou attendre/mocker
    res = await client.get("/api/v1/ships", headers={"Authorization": f"Bearer {expired}"})
    assert res.status_code == 401
```

### V6 — Manipulation XP en input

**Cas** : tentative d'ajouter du XP via un body API.

**Test attendu** : aucun endpoint n'accepte XP en input. Si on en trouve un en codant, c'est un fail à signaler.

## Vecteurs ÉLEVÉS

### V7 — Vaisseau IN_FLEET envoyé en forge

```python
async def test_forge_in_fleet_ship_rejected(self, auth_client, ship_in_fleet, built_ship):
    res = await auth_client.post("/api/v1/forge", json={
        "ship_a_id": str(ship_in_fleet.id),
        "ship_b_id": built_ship["ship_id"]
    })
    assert res.status_code == 409
```

### V8 — WebSocket cross-player

**Test attendu** : connecter playerA en WS, déclencher un event sur playerB, vérifier que A NE reçoit RIEN.

```python
async def test_ws_isolation(self, client_ws_a, client_ws_b):
    # client_ws_a et client_ws_b sont des fixtures à créer
    await client_ws_b.action_qui_genere_event()
    # client_ws_a ne doit PAS recevoir
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(client_ws_a.receive_text(), timeout=2.0)
```

### V9 — Pedigree avec parent d'autrui

```python
async def test_build_pedigree_other_player_ship(self, auth_client, other_player_ship_id, planet_id):
    res = await auth_client.post("/api/v1/ships/build", json={
        "ship_type": "frigate_attack",
        "planet_id": str(planet_id),
        "parent_ship_id": str(other_player_ship_id)
    })
    assert res.status_code == 403  # explicite ici
```

### V10 — Rate limiting

```python
async def test_build_rate_limited(self, auth_client, planet_id):
    # 10 builds rapides
    for _ in range(11):
        res = await auth_client.post("/api/v1/ships/build", json={...})
    # Le 11e doit être 429
    assert res.status_code == 429
    assert "Retry-After" in res.headers
```

## Vecteurs MOYENS

### V11 — `with_for_update` manquant

**Difficile à tester directement.** Plutôt : audit code + test concurrent (cf. V2).

### V12 — `math.floor` manquant sur ressources

```python
async def test_resources_rounding_safety(self, auth_client, planet_id, db_session):
    # Forcer planet.metal = 1999.87 (production lazy)
    planet = await db_session.get(Planet, planet_id)
    planet.metal = 1999.87
    await db_session.flush()
    # Tenter build qui coûte 2000 metal exactement → doit refuser
    res = await auth_client.post("/api/v1/ships/build", json={
        "ship_type": "frigate_support",  # 2000 metal
        "planet_id": str(planet_id)
    })
    assert res.status_code == 402
```

### V13 — N+1 queries (perf)

**Test indirect** : monitor avec `pytest-postgresql` ou logging SQL.

```python
async def test_ranking_no_n_plus_one(self, client, sqlalchemy_log_capture):
    res = await client.get("/api/v1/ranking?limit=100")
    # Compter le nombre de queries — doit être ≤ 3
    queries = sqlalchemy_log_capture.get_queries()
    assert len(queries) <= 3, f"N+1 detected: {len(queries)} queries"
```

## Checklist par méthode HTTP — résumé

### GET avec `<id>`
- ☐ V1 (ownership 404)
- ☐ 404 inexistant (UUID random)
- ☐ 401 sans auth

### POST création
- ☐ V2 (double-submission)
- ☐ V10 (rate-limit) si dans `_LIMITS`
- ☐ V12 (math.floor ressources)
- ☐ 402 ressources insuffisantes
- ☐ 409 conflit état
- ☐ 422 validation Pydantic

### PUT mutation
- ☐ V1 (ownership)
- ☐ V11 (concurrence)
- ☐ 409 statut bloquant

### DELETE
- ☐ V1 (ownership)
- ☐ 409 statut bloquant
- ☐ 204 No Content (pas de body)

## Scoring de couverture

Pour chaque endpoint :
- 1 point par test happy path.
- 1 point par vecteur sécurité testé.
- Cible : ≥ 4 points par endpoint qui modifie l'état.

Total cible projet : ≥ 80 % des endpoints à 4+ points.
