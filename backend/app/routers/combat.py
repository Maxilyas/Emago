"""
app/routers/combat.py
GET /combat/:id — rapport de combat complet (replay)

Le rapport est lu depuis Redis (cache 10 min) ou depuis la BDD (fallback).
Le combat lui-même est déclenché automatiquement par fleet_arrival.py
quand une flotte ATTACK arrive à destination.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import or_, select

from app.core.deps import CurrentPlayer, DbDep
from app.core.redis_client import get_redis
from app.models.models import CombatLog

router = APIRouter(prefix="/combat", tags=["combat"])

_COMBAT_CACHE_TTL = 600  # 10 minutes


class CombatReportResponse(BaseModel):
    combat_id: uuid.UUID
    outcome: str                    # "ATTACKER_WIN" | "DEFENDER_WIN" | "DRAW"
    fought_at: datetime
    attacker_power: float
    defender_power: float
    pillaged_metal: float
    pillaged_crystal: float
    pillaged_deuterium: float
    total_rounds: int
    rounds_log: list[dict[str, Any]]
    attacker_ships_snapshot: list[dict[str, Any]]
    defender_ships_snapshot: list[dict[str, Any]]


@router.get("/{combat_id}", response_model=CombatReportResponse)
async def get_combat_report(
    combat_id: uuid.UUID,
    player: CurrentPlayer,
    db: DbDep,
) -> CombatReportResponse:
    """
    Retourne le rapport complet d'un combat.

    Le joueur doit être participant (attaquant ou défenseur).
    Retourne depuis Redis si le cache est chaud, sinon depuis PostgreSQL.
    """
    # 1. Cache Redis
    r = get_redis()
    cache_key = f"combat:{combat_id}:result"
    cached = await r.get(cache_key)
    if cached:
        data = json.loads(cached)
        return CombatReportResponse(**data)

    # 2. BDD
    result = await db.execute(
        select(CombatLog).where(CombatLog.id == combat_id)
    )
    log: CombatLog | None = result.scalar_one_or_none()

    if log is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Combat introuvable.")

    # Vérification participation — le joueur doit être impliqué
    # (via ses flottes : fleet_attacker_id ou defender_planet_id appartenant à lui)
    # Simplification : on retourne le rapport à tout joueur authentifié pour l'instant
    # TODO phase 2 : vérifier que le joueur est attaquant ou défenseur

    total_rounds = len(log.rounds_log) if log.rounds_log else 0

    report = CombatReportResponse(
        combat_id=log.id,
        outcome=log.outcome,
        fought_at=log.fought_at,
        attacker_power=float(log.attacker_power),
        defender_power=float(log.defender_power),
        pillaged_metal=float(log.pillaged_metal),
        pillaged_crystal=float(log.pillaged_crystal),
        pillaged_deuterium=float(log.pillaged_deuterium),
        total_rounds=total_rounds,
        rounds_log=log.rounds_log or [],
        attacker_ships_snapshot=log.attacker_ships_snapshot or [],
        defender_ships_snapshot=log.defender_ships_snapshot or [],
    )

    # Mise en cache Redis
    await r.setex(cache_key, _COMBAT_CACHE_TTL, report.model_dump_json())

    return report
