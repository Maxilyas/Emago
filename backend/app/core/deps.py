"""
app/core/deps.py
Dépendances FastAPI injectables via Depends().
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_dep
from app.core.security import decode_token
from app.models.models import Player

_bearer = HTTPBearer(auto_error=True)

DbDep = Annotated[AsyncSession, Depends(get_db_dep)]


async def get_current_player(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
    db: DbDep,
) -> Player:
    """
    Décode le JWT Bearer, charge le joueur depuis la BDD.
    Lève HTTP 401 si le token est invalide ou le joueur introuvable.
    """
    exc_401 = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Identifiants invalides ou token expiré.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        player_id = decode_token(credentials.credentials, expected_kind="access")
    except ValueError:
        raise exc_401

    result = await db.execute(select(Player).where(Player.id == uuid.UUID(player_id)))
    player = result.scalar_one_or_none()
    if player is None:
        raise exc_401

    return player


CurrentPlayer = Annotated[Player, Depends(get_current_player)]
