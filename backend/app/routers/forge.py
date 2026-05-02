"""
app/routers/forge.py
POST /forge              — démarrer une forge
GET  /forge/history      — historique des forges du joueur
GET  /forge/{id}         — statut en temps réel (Redis)

IMPORTANT : /forge/history AVANT /forge/{id} dans le router
pour éviter que "history" soit capturé comme un UUID.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import CurrentPlayer, DbDep
from app.middleware.rate_limit import check_rate_limit
from app.models.models import ForgeQueue
from app.schemas.forge import (
    ForgeHistoryItem,
    ForgeStartRequest,
    ForgeStatusResponse,
)
from app.services.forge_service import get_forge_status, start_forge

router = APIRouter(prefix="/forge", tags=["forge"])


@router.post("", response_model=ForgeStatusResponse, status_code=status.HTTP_201_CREATED)
async def start_forge_endpoint(
    body: ForgeStartRequest,
    player: CurrentPlayer,
    db: DbDep,
) -> ForgeStatusResponse:
    """
    Lance une opération de Forge entre deux vaisseaux.
    Toutes les validations sont dans forge_service.start_forge().
    """
    await check_rate_limit(str(player.id), "forge:start")
    result = await start_forge(
        db=db,
        player_id=player.id,
        ship_a_id=body.ship_a_id,
        ship_b_id=body.ship_b_id,
    )
    return ForgeStatusResponse(**result)


@router.get("/history", response_model=list[ForgeHistoryItem])
async def get_forge_history(player: CurrentPlayer, db: DbDep) -> list[ForgeHistoryItem]:
    """Retourne l'historique des forges du joueur (complètes et en cours)."""
    result = await db.execute(
        select(ForgeQueue)
        .where(ForgeQueue.player_id == player.id)
        .order_by(ForgeQueue.started_at.desc())
        .limit(50)
    )
    entries = result.scalars().all()

    return [
        ForgeHistoryItem(
            forge_id=e.id,
            ship_a_id=e.ship_a_id,
            ship_b_id=e.ship_b_id,
            result_ship_id=e.result_ship_id,
            started_at=e.started_at,
            completed_at=e.completed_at,
            is_completed=e.is_completed,
        )
        for e in entries
    ]


@router.get("/{forge_id}", response_model=ForgeStatusResponse)
async def get_forge_status_endpoint(
    forge_id: uuid.UUID,
    player: CurrentPlayer,
    db: DbDep,
) -> ForgeStatusResponse:
    """
    Retourne le statut d'une forge depuis Redis.
    Fallback vers la BDD si le cache est absent (WS interrompu).
    """
    # 1. Redis (chemin nominal)
    cached = await get_forge_status(forge_id)
    if cached:
        cached_owner = cached.get("player_id")
        if cached_owner is None:
            # Entrée Redis ancienne (sans player_id) — fallback BDD pour vérifier l'ownership
            pass
        elif cached_owner != str(player.id):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Forge introuvable.")
        else:
            return ForgeStatusResponse(**cached)

    # 2. Fallback BDD
    result = await db.execute(
        select(ForgeQueue).where(
            ForgeQueue.id == forge_id,
            ForgeQueue.player_id == player.id,
        )
    )
    entry: ForgeQueue | None = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Forge introuvable.")

    return ForgeStatusResponse(
        forge_id=entry.id,
        completed_at=entry.completed_at,
        progress_pct=100 if entry.is_completed else 0,
        eta_seconds=0,
        result_ship_id=entry.result_ship_id,
    )
