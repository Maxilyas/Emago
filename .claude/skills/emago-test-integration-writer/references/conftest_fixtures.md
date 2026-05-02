# Fixtures pytest Emago — `tests/conftest.py`

Liste exhaustive des fixtures disponibles, leur scope, leur signature et un exemple d'usage.

## Configuration

- **DSN test** : `postgresql+asyncpg://emago:emago_dev@localhost:5432/emago_test`
- **Mode asyncio** : `auto` (cf. `pytest.ini`).
- **Coverage** : `--cov=app --cov-report=term-missing`.

## Fixtures disponibles

### `test_engine` (scope=session)

Engine SQLAlchemy async pour les tests. Drop_all + create_all en début, dispose en fin.

**Usage** : implicite, ne pas utiliser directement.

### `db_session` (scope=function)

Session async avec transaction par test, rollback final.

**Signature** : `AsyncSession`

**Usage** :
```python
@pytest.mark.asyncio
async def test_truc(db_session: AsyncSession):
    obj = Player(username="x", email="x@x.com", password_hash="...")
    db_session.add(obj)
    await db_session.flush()
    # ... assertions ...
    # rollback automatique en fin de test
```

### `client` (scope=function)

`AsyncClient` ASGI **sans authentification**. `get_db_dep` overridé pour utiliser `db_session`. Redis mocké.

**Signature** : `AsyncClient`

**Usage** :
```python
@pytest.mark.asyncio
async def test_endpoint_public(client: AsyncClient):
    res = await client.get("/api/v1/ranking")
    assert res.status_code == 200
```

### `auth_client` (scope=function)

`AsyncClient` avec header `Authorization: Bearer <create_token(player_id, "access")>`. Le player utilisé est `registered_player`.

**Signature** : `AsyncClient`

**Usage** :
```python
@pytest.mark.asyncio
async def test_endpoint_authentifie(auth_client: AsyncClient):
    res = await auth_client.get("/api/v1/ships")
    assert res.status_code == 200
```

### `registered_player` (scope=function)

Player aléatoire en BDD avec mot de passe `password123`.

**Signature** : `Player`

**Usage** :
```python
async def test_login(client, registered_player):
    res = await client.post("/api/v1/auth/login", json={
        "email": registered_player.email,
        "password": "password123"
    })
    assert res.status_code == 200
```

### `planet_id` (scope=function)

ID UUID d'une planète Homeworld appartenant à `registered_player`. Stocks confortables :
- metal=50000, crystal=20000, deuterium=10000
- capacité metal=500000, crystal=500000, deut=200000

**Signature** : `UUID`

**Usage** :
```python
async def test_build_ship(auth_client, planet_id):
    res = await auth_client.post("/api/v1/ships/build", json={
        "ship_type": "frigate_attack",
        "planet_id": str(planet_id)
    })
    assert res.status_code == 201
```

### `built_ship` (scope=function)

Construit un `frigate_attack` via `POST /ships/build` (donc 100 % légitime du point de vue de l'app).

**Signature** : `dict` avec clés `ship_id, rarity, ship_class, base_stats, slots_total, slots_premium, pedigree_applied`.

**Usage** :
```python
async def test_get_ship(auth_client, built_ship):
    res = await auth_client.get(f"/api/v1/ships/{built_ship['ship_id']}")
    assert res.status_code == 200
    assert res.json()["base_stats"] == built_ship["base_stats"]
```

### `other_player_ship_id` (scope=function)

Player ALTER + Ship lui appartenant. Utilisé pour tester le vecteur **ownership masqué** (404 quand on tente d'accéder en tant que `registered_player`).

**Signature** : `UUID` (ID du ship)

**Usage** :
```python
async def test_get_ship_other_player(auth_client, other_player_ship_id):
    res = await auth_client.get(f"/api/v1/ships/{other_player_ship_id}")
    assert res.status_code == 404
    assert "introuvable" in res.json()["detail"]
```

### `ship_in_fleet` (scope=function)

Ship appartenant à `registered_player` mais avec `status = ShipStatus.IN_FLEET`. Utilisé pour tester rejection 409 sur opérations qui exigent DOCKED.

**Signature** : `Ship`

**Usage** :
```python
async def test_demolish_in_fleet(auth_client, ship_in_fleet):
    res = await auth_client.delete(f"/api/v1/ships/{ship_in_fleet.id}")
    assert res.status_code == 409
```

### `two_ships_different_rarity` (scope=function)

Tuple (ship_a COMMON, ship_b RARE) appartenant à `registered_player`, tous deux DOCKED. Pour tester rejection forge 422 (raretés différentes).

**Signature** : `tuple[Ship, Ship]`

**Usage** :
```python
async def test_forge_different_rarities(auth_client, two_ships_different_rarity):
    a, b = two_ships_different_rarity
    res = await auth_client.post("/api/v1/forge", json={
        "ship_a_id": str(a.id),
        "ship_b_id": str(b.id)
    })
    assert res.status_code == 422
```

## Mock Redis

Le `_make_redis_mock()` (utilisé en interne par `client` et `auth_client`) retourne un `AsyncMock` avec :
- `get`, `setex`, `delete`, `publish` mockés (retournent valeurs fixes).
- `pipeline().zremrangebyscore() / zadd() / zcard() / expire() / execute()` retourne `[0, 1, 1, True]`.

Pour personnaliser :
```python
from unittest.mock import AsyncMock

custom_redis = AsyncMock()
custom_redis.get.return_value = '{"forge_id": "..."}'
client.app.dependency_overrides[get_redis] = lambda: custom_redis
```

## Fixtures à ajouter pour les futurs tests

| Fixture | Pourquoi | Signature |
|---|---|---|
| `alliance_with_leader` | Tests alliances | `Alliance` (avec `registered_player` comme leader) |
| `alliance_full_20_members` | Tester 409 alliance pleine | `Alliance` (20 membres) |
| `forge_in_progress` | Tests forge.poll WS | `ForgeQueue` |
| `combat_log` | Tests `/combat/{id}` participation | `CombatLog` |
| `expedition_active` | Tests `/expeditions/active` | dict Redis |
| `legendary_ship` | Tests forge LEGENDARY rejection | `Ship` rarity=LEGENDARY |
| `grade_5_ship` | Tests Spectre overlay | `Ship` grade=5, combat_xp >= 40000 |
| `second_player_authclient` | Tests cross-player WS isolation | `AsyncClient` second auth |

## Conventions

- **Toujours utiliser `db_session`** pour le rollback per test.
- **Préférer les fixtures aux objets créés à la main** — DRY, plus facile à maintenir.
- **Si une fixture est utilisée par ≥ 2 tests, l'extraire** dans `conftest.py`.
- **Si elle n'est utilisée qu'une fois, la garder inline** (mais commenter pourquoi).
- **Toujours rollback** — ne jamais commit dans un test.
