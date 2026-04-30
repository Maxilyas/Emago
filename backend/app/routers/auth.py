"""
app/routers/auth.py
POST /auth/register  — Inscription
POST /auth/login     — Connexion
POST /auth/refresh   — Rotation des tokens
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import create_token, decode_token, hash_password, verify_password
from app.models.models import Player
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest) -> TokenResponse:
    """Crée un compte et retourne une paire de tokens."""
    async with AsyncSessionLocal() as db:
        try:
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
            await db.commit()
            await db.refresh(player)
        except HTTPException:
            raise
        except Exception:
            await db.rollback()
            raise

    return TokenResponse(
        access_token=create_token(str(player.id), "access"),
        refresh_token=create_token(str(player.id), "refresh"),
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest) -> TokenResponse:
    """Authentifie et retourne les tokens. Message d'erreur volontairement vague."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Player).where(Player.email == body.email))
        player: Player | None = result.scalar_one_or_none()

        if player is None or not verify_password(body.password, player.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou mot de passe incorrect.",
            )

        player.last_login_at = datetime.now(UTC)
        db.add(player)
        await db.commit()

    return TokenResponse(
        access_token=create_token(str(player.id), "access"),
        refresh_token=create_token(str(player.id), "refresh"),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest) -> TokenResponse:
    """Échange un refresh token contre une nouvelle paire. Rotation obligatoire."""
    try:
        player_id = decode_token(body.refresh_token, expected_kind="refresh")
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Refresh token invalide : {exc}",
        ) from exc

    return TokenResponse(
        access_token=create_token(player_id, "access"),
        refresh_token=create_token(player_id, "refresh"),
    )
