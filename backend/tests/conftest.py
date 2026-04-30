"""
tests/conftest.py
Fixtures partagées pour tous les tests.
"""
from __future__ import annotations

import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest


# ---------------------------------------------------------------------------
# Fixture Redis mock — évite une vraie connexion Redis en tests unitaires
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_redis():
    """Mock du client Redis pour les tests qui n'ont pas besoin du vrai Redis."""
    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.setex = AsyncMock(return_value=True)
    redis_mock.delete = AsyncMock(return_value=1)
    redis_mock.publish = AsyncMock(return_value=1)

    with patch("app.core.redis_client._redis_pool", redis_mock):
        yield redis_mock


# ---------------------------------------------------------------------------
# Fixture Player mock
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_player():
    player = MagicMock()
    player.id = uuid.uuid4()
    player.username = "test_player"
    player.email = "test@emago.io"
    player.score = 0
    return player
