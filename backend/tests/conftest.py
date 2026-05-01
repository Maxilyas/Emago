"""
tests/conftest.py — v2
Agent 8 — QA & Sécurité | Sprint 2

Fixtures d'intégration complètes avec BDD de test PostgreSQL.

Prérequis :
  - BDD de test : postgresql://emago:emago_dev@localhost:5432/emago_test
  - `pytest.ini` : asyncio_mode = auto

Usage :
  pytest tests/ -v --tb=short
"""
from __future__ import annotations

import asyncio
import uuid
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db_dep
from app.main import app
from app.models.models import Base, Planet, Player, Ship, ShipStatus
from app.core.security import create_token, hash_password

TEST_DATABASE_URL = "postgresql+asyncpg://emago:emago_dev@localhost:5432/emago_test"

# ---------------------------------------------------------------------------
# Engine & session de test
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Session isolée par test avec rollback automatique."""
    Session = async_sessionmaker(test_engine, expire_on_commit=False)
    async with Session() as session:
        async with session.begin():
            yield session
            await session.rollback()


# ---------------------------------------------------------------------------
# Override dépendances FastAPI
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Client HTTP sans auth."""
    async def override_db():
        yield db_session

    app.dependency_overrides[get_db_dep] = override_db

    with patch("app.core.redis_client._redis_pool", _make_redis_mock()):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as c:
            yield c

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Fixtures joueurs
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def registered_player(db_session: AsyncSession) -> dict:
    """Crée un joueur en BDD et retourne ses credentials."""
    player = Player(
        id=uuid.uuid4(),
        username=f"player_{uuid.uuid4().hex[:8]}",
        email=f"{uuid.uuid4().hex[:8]}@emago.io",
        password_hash=hash_password("password123"),
    )
    db_session.add(player)
    await db_session.flush()
    return {
        "id": str(player.id),
        "username": player.username,
        "email": player.email,
        "password": "password123",
    }


@pytest_asyncio.fixture
async def auth_client(db_session: AsyncSession, registered_player: dict) -> AsyncGenerator[AsyncClient, None]:
    """Client HTTP avec JWT du joueur enregistré."""
    async def override_db():
        yield db_session

    app.dependency_overrides[get_db_dep] = override_db
    token = create_token(registered_player["id"], "access")

    with patch("app.core.redis_client._redis_pool", _make_redis_mock()):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"Authorization": f"Bearer {token}"},
        ) as c:
            yield c

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Fixtures Planète & Vaisseaux
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def planet_id(db_session: AsyncSession, registered_player: dict) -> str:
    """Crée une planète natale avec des ressources pour construire."""
    planet = Planet(
        id=uuid.uuid4(),
        owner_id=uuid.UUID(registered_player["id"]),
        galaxy=1, system=1, position=1,
        name="Planète de test",
        is_homeworld=True,
        metal=50_000.0,
        crystal=20_000.0,
        deuterium=10_000.0,
        metal_capacity=500_000,
        crystal_capacity=500_000,
        deut_capacity=200_000,
        buildings={},
    )
    db_session.add(planet)
    await db_session.flush()
    return str(planet.id)


@pytest_asyncio.fixture
async def built_ship(auth_client: AsyncClient, planet_id: str) -> dict:
    """Construit un vaisseau via l'API et retourne la réponse."""
    resp = await auth_client.post("/api/v1/ships/build", json={
        "ship_type": "frigate_attack",
        "planet_id": planet_id,
    })
    assert resp.status_code == 201
    return resp.json()


@pytest_asyncio.fixture
async def other_player_ship_id(db_session: AsyncSession) -> str:
    """Crée un vaisseau appartenant à un AUTRE joueur (pour tester l'ownership)."""
    other = Player(
        id=uuid.uuid4(),
        username=f"other_{uuid.uuid4().hex[:8]}",
        email=f"other_{uuid.uuid4().hex[:8]}@emago.io",
        password_hash=hash_password("pass"),
    )
    db_session.add(other)
    await db_session.flush()

    ship = Ship(
        id=uuid.uuid4(),
        owner_id=other.id,
        ship_type="frigate_attack",
        class_="ATTACK",
        rarity="COMMON",
        status=ShipStatus.DOCKED,
        grade=0,
        combat_xp=0,
        base_stats={"hull": 100, "shield": 20, "dps": 80, "speed": 45.0,
                    "cargo": 200, "stealth": 0.0, "support_aura": 0.0},
    )
    db_session.add(ship)
    await db_session.flush()
    return str(ship.id)


@pytest_asyncio.fixture
async def ship_in_fleet(db_session: AsyncSession, registered_player: dict) -> str:
    """Crée un vaisseau avec statut IN_FLEET."""
    ship = Ship(
        id=uuid.uuid4(),
        owner_id=uuid.UUID(registered_player["id"]),
        ship_type="frigate_attack",
        class_="ATTACK",
        rarity="COMMON",
        status=ShipStatus.IN_FLEET,
        grade=0,
        combat_xp=0,
        base_stats={"hull": 100, "shield": 20, "dps": 80, "speed": 45.0,
                    "cargo": 200, "stealth": 0.0, "support_aura": 0.0},
    )
    db_session.add(ship)
    await db_session.flush()
    return str(ship.id)


@pytest_asyncio.fixture
async def two_ships_different_rarity(db_session: AsyncSession, registered_player: dict) -> tuple[str, str]:
    """Deux vaisseaux du même joueur avec des raretés différentes."""
    player_id = uuid.UUID(registered_player["id"])
    base = {"hull": 100, "shield": 20, "dps": 80, "speed": 45.0,
            "cargo": 200, "stealth": 0.0, "support_aura": 0.0}

    ship_a = Ship(id=uuid.uuid4(), owner_id=player_id, ship_type="frigate_attack",
                  class_="ATTACK", rarity="COMMON", status=ShipStatus.DOCKED,
                  grade=0, combat_xp=0, base_stats=base)
    ship_b = Ship(id=uuid.uuid4(), owner_id=player_id, ship_type="frigate_attack",
                  class_="ATTACK", rarity="RARE", status=ShipStatus.DOCKED,
                  grade=0, combat_xp=0, base_stats={k: int(v * 1.55) if isinstance(v, (int, float)) else v
                                                    for k, v in base.items()})
    db_session.add_all([ship_a, ship_b])
    await db_session.flush()
    return str(ship_a.id), str(ship_b.id)


# ---------------------------------------------------------------------------
# Helper Redis mock
# ---------------------------------------------------------------------------

def _make_redis_mock():
    mock = AsyncMock()
    mock.get = AsyncMock(return_value=None)
    mock.setex = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=1)
    mock.publish = AsyncMock(return_value=1)
    # Pour le rate limiting (pipeline)
    pipeline_mock = AsyncMock()
    pipeline_mock.__aenter__ = AsyncMock(return_value=pipeline_mock)
    pipeline_mock.__aexit__ = AsyncMock(return_value=None)
    pipeline_mock.zremrangebyscore = AsyncMock()
    pipeline_mock.zadd = AsyncMock()
    pipeline_mock.zcard = AsyncMock()
    pipeline_mock.expire = AsyncMock()
    pipeline_mock.execute = AsyncMock(return_value=[0, 1, 1, True])
    mock.pipeline = MagicMock(return_value=pipeline_mock)
    return mock
