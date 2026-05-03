"""
app/routers/auth.py
POST /auth/register  — Inscription
POST /auth/login     — Connexion
POST /auth/refresh   — Rotation des tokens

Sécurité :
  - Rate limiting sur register (5/min), login (10/min) et refresh (30/min) par IP
  - Refresh token stocké en base (hash SHA-256) — révocation effective
    à chaque rotation. Un token volé est invalidé dès le prochain refresh.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.core.config import get_settings
from app.core.deps import DbDep
from app.core.security import (
    create_token,
    decode_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.middleware.rate_limit import check_rate_limit
from app.models.models import Player
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(request: Request, body: RegisterRequest, db: DbDep) -> TokenResponse:
    """Crée un compte et retourne une paire de tokens."""
    await check_rate_limit(request.client.host, "auth:register")

    existing = await db.execute(
        select(Player).where(
            (Player.username == body.username) | (Player.email == body.email)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ce nom d'utilisateur ou cet email est déjà utilisé.",
        )

    player = Player(
        id=uuid.uuid4(),
        username=body.username,
        email=body.email,
        password_hash=hash_password(body.password),
    )
    db.add(player)
    await db.flush()

    refresh_tok = create_token(str(player.id), "refresh")
    player.refresh_token = hash_refresh_token(refresh_tok)
    player.refresh_token_expires_at = datetime.now(UTC) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    db.add(player)

    return TokenResponse(
        access_token=create_token(str(player.id), "access"),
        refresh_token=refresh_tok,
        player_id=str(player.id),
        username=player.username,
    )


@router.post("/login", response_model=TokenResponse)
async def login(request: Request, body: LoginRequest, db: DbDep) -> TokenResponse:
    """Authentifie et retourne les tokens. Message d'erreur volontairement vague."""
    await check_rate_limit(request.client.host, "auth:login")

    result = await db.execute(select(Player).where(Player.email == body.email))
    player: Player | None = result.scalar_one_or_none()

    if player is None or not verify_password(body.password, player.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect.",
        )

    refresh_tok = create_token(str(player.id), "refresh")
    player.last_login_at = datetime.now(UTC)
    player.refresh_token = hash_refresh_token(refresh_tok)
    player.refresh_token_expires_at = datetime.now(UTC) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    db.add(player)

    return TokenResponse(
        access_token=create_token(str(player.id), "access"),
        refresh_token=refresh_tok,
        player_id=str(player.id),
        username=player.username,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: Request, body: RefreshRequest, db: DbDep) -> TokenResponse:
    """
    Échange un refresh token contre une nouvelle paire. Rotation obligatoire.
    L'ancien token est invalidé en base — un token volé est révoqué dès ce moment.
    """
    await check_rate_limit(request.client.host, "auth:refresh")

    try:
        player_id = decode_token(body.refresh_token, expected_kind="refresh")
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Refresh token invalide : {exc}",
        ) from exc

    result = await db.execute(select(Player).where(Player.id == uuid.UUID(player_id)))
    player: Player | None = result.scalar_one_or_none()

    if player is None or player.refresh_token != hash_refresh_token(body.refresh_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token révoqué ou inconnu.",
        )

    refresh_tok = create_token(player_id, "refresh")
    player.refresh_token = hash_refresh_token(refresh_tok)
    player.refresh_token_expires_at = datetime.now(UTC) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    db.add(player)

    return TokenResponse(
        access_token=create_token(player_id, "access"),
        refresh_token=refresh_tok,
        player_id=str(player.id),
        username=player.username,
    )
