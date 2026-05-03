"""
app/routers/galaxy.py

GET  /galaxy?galaxy=1&system=1     — slots du système + ghost ships
POST /galaxy/ghost_ships/{id}/attack — attaquer un vaisseau fantôme
"""
from __future__ import annotations

import uuid as uuid_mod
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.core.deps import CurrentPlayer, DbDep
from app.models.models import Planet, Player
from app.models.ghost_ship_model import GhostShip
from app.services.ghost_ship_service import ensure_ghost_ships, respawn_defeated, attack_ghost

router = APIRouter(prefix="/galaxy", tags=["galaxy"])


# ─── Schemas ─────────────────────────────────────────────────────────────────

class GalaxySlot(BaseModel):
    position: int
    planet_id: str | None
    planet_name: str | None
    owner_id: str | None
    owner_username: str | None
    is_mine: bool


class GhostShipOut(BaseModel):
    id: str
    name: str
    ship_type: str
    rarity: str
    threat_level: int
    current_hull: int
    max_hull: int
    is_defeated: bool
    respawn_at: datetime | None


class SystemResponse(BaseModel):
    slots: list[GalaxySlot]
    ghost_ships: list[GhostShipOut]


class AttackRequest(BaseModel):
    ship_ids: list[str]


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get("", response_model=SystemResponse)
async def get_system(
    galaxy: int,
    system: int,
    player: CurrentPlayer,
    db: DbDep,
) -> SystemResponse:
    """Retourne les 15 slots du système + les vaisseaux fantômes actifs."""
    # Spawner ghost ships si premier chargement du système
    await ensure_ghost_ships(galaxy, system, db)
    # Respawn ceux qui sont prêts
    await respawn_defeated(galaxy, system, db)
    await db.commit()

    # Planètes
    result = await db.execute(
        select(Planet).where(Planet.galaxy == galaxy, Planet.system == system)
    )
    planets = {p.position: p for p in result.scalars().all()}

    owner_ids = {p.owner_id for p in planets.values() if p.owner_id}
    usernames: dict[uuid_mod.UUID, str] = {}
    if owner_ids:
        players_r = await db.execute(select(Player).where(Player.id.in_(owner_ids)))
        usernames = {p.id: p.username for p in players_r.scalars().all()}

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
                position=pos, planet_id=None, planet_name=None,
                owner_id=None, owner_username=None, is_mine=False,
            ))

    # Ghost ships du système
    ghosts_r = await db.execute(
        select(GhostShip).where(GhostShip.galaxy == galaxy, GhostShip.system == system)
    )
    ghost_ships = [
        GhostShipOut(
            id=str(g.id),
            name=g.name,
            ship_type=g.ship_type,
            rarity=g.rarity,
            threat_level=g.threat_level,
            current_hull=g.current_hull,
            max_hull=g.max_hull,
            is_defeated=g.is_defeated,
            respawn_at=g.respawn_at,
        )
        for g in ghosts_r.scalars().all()
    ]

    return SystemResponse(slots=slots, ghost_ships=ghost_ships)


@router.post("/ghost_ships/{ghost_id}/attack")
async def attack_ghost_ship(
    ghost_id: uuid_mod.UUID,
    body: AttackRequest,
    player: CurrentPlayer,
    db: DbDep,
) -> dict:
    """Attaque un vaisseau fantôme avec les vaisseaux du joueur."""
    try:
        ship_uuids = [uuid_mod.UUID(sid) for sid in body.ship_ids]
    except ValueError:
        raise HTTPException(status_code=400, detail="UUID de vaisseau invalide.")

    # Vérifier que les vaisseaux appartiennent bien au joueur
    from app.models.models import Ship
    from sqlalchemy import select as sel
    owned = await db.execute(
        sel(Ship.id).where(Ship.id.in_(ship_uuids), Ship.owner_id == player.id)
    )
    if owned.scalars().all().__len__() == 0:
        raise HTTPException(status_code=403, detail="Ces vaisseaux ne vous appartiennent pas.")

    try:
        result = await attack_ghost(ghost_id, ship_uuids, db)
        await db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
