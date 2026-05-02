# Patterns de tests Emago — extraits

Squelettes inspirés de `tests/routers/test_auth.py`, `test_ships.py`, `test_forge.py`.

## Structure de fichier type

```python
"""
Tests d'intégration — router <name>.
Couvre les endpoints du router et les vecteurs sécurité critiques.
"""
from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Player, Ship, ShipStatus, ...


class TestList<Resource>:
    """GET /<resource>"""

    @pytest.mark.asyncio
    async def test_list_success(self, auth_client: AsyncClient, ...):
        res = await auth_client.get("/api/v1/<resource>")
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_list_no_auth(self, client: AsyncClient):
        res = await client.get("/api/v1/<resource>")
        assert res.status_code == 401  # ou 200 si endpoint public


class TestGet<Resource>:
    """GET /<resource>/{id}"""

    @pytest.mark.asyncio
    async def test_get_success(self, auth_client, built_ship):
        res = await auth_client.get(f"/api/v1/ships/{built_ship['ship_id']}")
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == built_ship["ship_id"]
        assert "current_stats" in data

    @pytest.mark.asyncio
    async def test_get_not_found(self, auth_client):
        res = await auth_client.get(f"/api/v1/ships/{uuid4()}")
        assert res.status_code == 404

    @pytest.mark.asyncio
    async def test_get_other_player_returns_404(self, auth_client, other_player_ship_id):
        """Vecteur sécurité V1 : ownership masqué."""
        res = await auth_client.get(f"/api/v1/ships/{other_player_ship_id}")
        assert res.status_code == 404, "Doit être 404 (anti-énumération), pas 403"


class TestCreate<Resource>:
    """POST /<resource>"""

    @pytest.mark.asyncio
    async def test_create_success(self, auth_client, planet_id):
        res = await auth_client.post("/api/v1/ships/build", json={
            "ship_type": "frigate_attack",
            "planet_id": str(planet_id)
        })
        assert res.status_code == 201
        data = res.json()
        assert data["ship_class"] == "ATTACK"
        assert data["rarity"] in {"COMMON", "UNCOMMON", "RARE", "EPIC", "LEGENDARY"}
        assert data["base_stats"]["hull"] > 0

    @pytest.mark.asyncio
    async def test_create_unknown_type(self, auth_client, planet_id):
        res = await auth_client.post("/api/v1/ships/build", json={
            "ship_type": "battlestar_galactica",
            "planet_id": str(planet_id)
        })
        assert res.status_code == 400

    @pytest.mark.asyncio
    async def test_create_insufficient_resources(self, auth_client, planet_id, db_session):
        # Drainer la planète
        from app.models.models import Planet
        planet = await db_session.get(Planet, planet_id)
        planet.metal = 0
        planet.crystal = 0
        await db_session.flush()

        res = await auth_client.post("/api/v1/ships/build", json={
            "ship_type": "frigate_attack",
            "planet_id": str(planet_id)
        })
        assert res.status_code == 402

    @pytest.mark.asyncio
    async def test_create_validation_error(self, auth_client, planet_id):
        res = await auth_client.post("/api/v1/ships/build", json={
            # ship_type manquant
            "planet_id": str(planet_id)
        })
        assert res.status_code == 422


class TestModify<Resource>:
    """PUT /<resource>/{id}"""

    @pytest.mark.asyncio
    async def test_modify_in_invalid_status(self, auth_client, ship_in_fleet):
        res = await auth_client.put(f"/api/v1/ships/{ship_in_fleet.id}/modules/0", json={
            "module_type": "CANNON",
            "level": 1
        })
        # Si le router le permet → 409. Sinon adapter.
        assert res.status_code in (409, 200)

    @pytest.mark.asyncio
    async def test_modify_other_player_returns_404(self, auth_client, other_player_ship_id):
        """V1."""
        res = await auth_client.put(f"/api/v1/ships/{other_player_ship_id}/modules/0", json={
            "module_type": "CANNON",
            "level": 1
        })
        assert res.status_code == 404


class TestDelete<Resource>:
    """DELETE /<resource>/{id}"""

    @pytest.mark.asyncio
    async def test_delete_success(self, auth_client, built_ship):
        res = await auth_client.delete(f"/api/v1/ships/{built_ship['ship_id']}")
        assert res.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_in_invalid_status(self, auth_client, ship_in_fleet):
        res = await auth_client.delete(f"/api/v1/ships/{ship_in_fleet.id}")
        assert res.status_code == 409

    @pytest.mark.asyncio
    async def test_delete_other_player_returns_404(self, auth_client, other_player_ship_id):
        res = await auth_client.delete(f"/api/v1/ships/{other_player_ship_id}")
        assert res.status_code == 404


class TestSecurityVectors:
    """Vecteurs d'attaque critiques."""

    @pytest.mark.asyncio
    async def test_double_submission(self, auth_client, ...):
        """V2 — race condition."""
        res1, res2 = await asyncio.gather(
            auth_client.post("/api/v1/forge", json={...}),
            auth_client.post("/api/v1/forge", json={...}),
        )
        statuses = sorted([res1.status_code, res2.status_code])
        # Un succès, un conflit
        assert 201 in statuses
        assert any(s in statuses for s in (404, 409))

    @pytest.mark.asyncio
    async def test_pedigree_with_other_player_parent(self, auth_client, other_player_ship_id, planet_id):
        """V9."""
        res = await auth_client.post("/api/v1/ships/build", json={
            "ship_type": "frigate_attack",
            "planet_id": str(planet_id),
            "parent_ship_id": str(other_player_ship_id)
        })
        assert res.status_code == 403
```

## Patterns réutilisables

### Lecture/écriture BDD directe dans un test

```python
from app.models.models import Player

async def test_truc(db_session: AsyncSession, registered_player: Player):
    # Mutation BDD via session
    registered_player.score = 1000
    await db_session.flush()

    # Vérification
    refreshed = await db_session.get(Player, registered_player.id)
    assert refreshed.score == 1000
```

### Concurrence avec asyncio

```python
async def test_concurrent_calls(self, auth_client):
    results = await asyncio.gather(
        auth_client.post("/api/v1/x", json={...}),
        auth_client.post("/api/v1/x", json={...}),
        auth_client.post("/api/v1/x", json={...}),
        return_exceptions=True,
    )
    # Vérifier qu'un seul a réussi
    successes = [r for r in results if hasattr(r, 'status_code') and r.status_code == 201]
    assert len(successes) == 1
```

### Patcher Redis

```python
from unittest.mock import AsyncMock

async def test_with_custom_redis(self, client):
    custom = AsyncMock()
    custom.get.return_value = '{"forge_id": "stored"}'

    # Override la dépendance
    from app.core.redis_client import get_redis
    client.app.dependency_overrides[get_redis] = lambda: custom

    res = await client.get("/api/v1/forge/abc")
    # Le router lit Redis avant de fallback BDD
    ...
```

### Helper pour générer un token expiré

```python
import jwt
from datetime import datetime, timedelta, UTC

def expired_token(player_id: str) -> str:
    payload = {
        "sub": player_id,
        "kind": "access",
        "iat": int((datetime.now(UTC) - timedelta(hours=2)).timestamp()),
        "exp": int((datetime.now(UTC) - timedelta(hours=1)).timestamp()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


async def test_expired_token(self, client):
    token = expired_token(str(uuid4()))
    res = await client.get("/api/v1/ships", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401
```

### Test distribution RNG

```python
@pytest.mark.asyncio
async def test_rarity_distribution(self, auth_client, planet_id, db_session):
    """V6 inverse : vérifier que la distribution rareté est conforme."""
    from collections import Counter
    rarities = []

    for _ in range(200):
        # Refill ressources avant chaque build
        from app.models.models import Planet
        p = await db_session.get(Planet, planet_id)
        p.metal = 100000
        p.crystal = 100000
        await db_session.flush()

        res = await auth_client.post("/api/v1/ships/build", json={
            "ship_type": "frigate_attack",
            "planet_id": str(planet_id)
        })
        assert res.status_code == 201
        rarities.append(res.json()["rarity"])

    counter = Counter(rarities)
    assert 0.45 <= counter["COMMON"] / 200 <= 0.65  # autour de 55 %
    # ... autres assertions
```

## Conventions de nommage

- `test_<endpoint>_<scenario>` — toujours en snake_case.
- `Test<Endpoint>` (PascalCase) pour les classes.
- `TestSecurityVectors` pour les vecteurs spécifiques (en plus des classes par endpoint).
- `TestRegression` pour les tests d'anti-régression suite à un bug.
