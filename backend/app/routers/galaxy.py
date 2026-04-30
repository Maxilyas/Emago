"""
app/routers/galaxy.py
Agent 5 — Backend

GET /galaxy?galaxy=1&system=1
Retourne les 15 slots d'un système avec les infos des planètes présentes.
Utilisé par la carte galactique frontend.
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select
import uuid

from app.core.deps import CurrentPlayer, DbDep
from app.models.models import Planet, Player

router = APIRouter(prefix="/galaxy", tags=["galaxy"])


class GalaxySlot(BaseModel):
    position: int
    planet_id: str | None
    planet_name: str | None
    owner_id: str | None
    owner_username: str | None
    is_mine: bool


@router.get("", response_model=list[GalaxySlot])
async def get_system(
    galaxy: int,
    system: int,
    player: CurrentPlayer,
    db: DbDep,
) -> list[GalaxySlot]:
    """
    Retourne les 15 positions orbitales d'un système.
    Positions sans planète ont planet_id = None.
    """
    # Charger toutes les planètes du système
    result = await db.execute(
        select(Planet).where(
            Planet.galaxy == galaxy,
            Planet.system == system,
        )
    )
    planets = {p.position: p for p in result.scalars().all()}

    # Charger les usernames des propriétaires en une seule requête
    owner_ids = {p.owner_id for p in planets.values() if p.owner_id}
    usernames: dict[uuid.UUID, str] = {}
    if owner_ids:
        players_result = await db.execute(
            select(Player).where(Player.id.in_(owner_ids))
        )
        usernames = {p.id: p.username for p in players_result.scalars().all()}

    # Construire les 15 slots
    slots = []
    for pos in range(1, 16):
        planet = planets.get(pos)
        if planet:
            slots.append(GalaxySlot(
                position=pos,
                planet_id=str(planet.id),
                planet_name=planet.name,
                owner_id=str(planet.owner_id) if planet.owner_id else None,
                owner_username=usernames.get(planet.owner_id) if planet.owner_id else None,
                is_mine=(planet.owner_id == player.id),
            ))
        else:
            slots.append(GalaxySlot(
                position=pos,
                planet_id=None,
                planet_name=None,
                owner_id=None,
                owner_username=None,
                is_mine=False,
            ))

    return slots
