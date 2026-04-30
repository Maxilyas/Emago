"""
app/routers/scars.py
GET  /ships/:id/scars                       — cicatrices d'un vaisseau
GET  /ships/:id/missions                    — missions actives (grade ≥ 2)
POST /ships/:id/missions/:mission_id/claim  — réclamer une récompense
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.core.deps import CurrentPlayer, DbDep
from app.models.models import Ship, ShipMission, ShipScar, ScarTag

router = APIRouter(prefix="/ships", tags=["scars & missions"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ScarOut(BaseModel):
    scar_id: uuid.UUID
    tag_code: str
    narrative: str
    earned_at: datetime


class MissionOut(BaseModel):
    mission_id: uuid.UUID
    mission_type: str
    condition: dict
    progress: dict
    reward: dict
    expires_at: datetime
    completed: bool
    reward_claimed: bool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_owned_ship(ship_id: uuid.UUID, player_id: uuid.UUID, db) -> Ship:
    result = await db.execute(select(Ship).where(Ship.id == ship_id))
    ship: Ship | None = result.scalar_one_or_none()
    if ship is None or ship.owner_id != player_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vaisseau introuvable.")
    return ship


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/{ship_id}/scars", response_model=list[ScarOut])
async def get_ship_scars(
    ship_id: uuid.UUID,
    player: CurrentPlayer,
    db: DbDep,
) -> list[ScarOut]:
    """
    Retourne les cicatrices narratives d'un vaisseau.
    Visibles par tous les joueurs (pas uniquement le propriétaire).
    """
    result = await db.execute(select(Ship).where(Ship.id == ship_id))
    ship: Ship | None = result.scalar_one_or_none()
    if ship is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vaisseau introuvable.")

    scars_result = await db.execute(
        select(ShipScar, ScarTag)
        .join(ScarTag, ShipScar.tag_id == ScarTag.id)
        .where(ShipScar.ship_id == ship_id)
        .order_by(ShipScar.earned_at.desc())
    )
    rows = scars_result.all()

    return [
        ScarOut(
            scar_id=scar.id,
            tag_code=tag.tag_code,
            narrative=tag.narrative,
            earned_at=scar.earned_at,
        )
        for scar, tag in rows
    ]


@router.get("/{ship_id}/missions", response_model=list[MissionOut])
async def get_ship_missions(
    ship_id: uuid.UUID,
    player: CurrentPlayer,
    db: DbDep,
) -> list[MissionOut]:
    """
    Retourne les missions actives d'un vaisseau (grade ≥ 2 requis).
    Les missions expirent toutes les 72h et se renouvellent automatiquement.
    """
    ship = await _get_owned_ship(ship_id, player.id, db)

    if ship.grade < 2:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Grade 2 minimum requis pour les missions. Ce vaisseau est Grade {ship.grade}.",
        )

    now = datetime.now(UTC)
    missions_result = await db.execute(
        select(ShipMission).where(
            ShipMission.ship_id == ship_id,
            ShipMission.expires_at > now,
        ).order_by(ShipMission.expires_at)
    )
    missions = missions_result.scalars().all()

    return [
        MissionOut(
            mission_id=m.id,
            mission_type=m.mission_type,
            condition=m.condition,
            progress=m.progress,
            reward=m.reward,
            expires_at=m.expires_at,
            completed=m.completed,
            reward_claimed=m.reward_claimed,
        )
        for m in missions
    ]


@router.post("/{ship_id}/missions/{mission_id}/claim", status_code=status.HTTP_200_OK)
async def claim_mission_reward(
    ship_id: uuid.UUID,
    mission_id: uuid.UUID,
    player: CurrentPlayer,
    db: DbDep,
) -> dict:
    """
    Réclame la récompense d'une mission complétée (skin, titre).
    """
    ship = await _get_owned_ship(ship_id, player.id, db)

    result = await db.execute(
        select(ShipMission).where(
            ShipMission.id == mission_id,
            ShipMission.ship_id == ship_id,
        )
    )
    mission: ShipMission | None = result.scalar_one_or_none()

    if mission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mission introuvable.")

    if not mission.completed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cette mission n'est pas encore complétée.",
        )

    if mission.reward_claimed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La récompense a déjà été réclamée.",
        )

    mission.reward_claimed = True
    db.add(mission)

    return {
        "mission_id": str(mission_id),
        "reward": mission.reward,
        "message": "Récompense réclamée avec succès.",
    }
