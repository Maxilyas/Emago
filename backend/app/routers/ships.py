"""
app/routers/ships.py
GET  /ships              — liste du hangar
GET  /ships/{id}         — détail complet
POST /ships/build        — construire un vaisseau
DELETE /ships/{id}       — démolir (Pedigree si Grade ≥ 3)

Aucune logique métier ici — tout délégué aux services.
"""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from fastapi import Response

from app.core.deps import CurrentPlayer, DbDep
from app.models.models import Ship, ShipStatus
from app.schemas.ship import (
    BuildShipRequest,
    BuildShipResponse,
    ShipDetailOut,
    ShipSummaryOut,
)
from app.services.ship_build_service import (
    _RARITY_SLOTS,
    build_ship,
    find_best_stat,
)
from app.middleware.rate_limit import check_rate_limit
from app.services.ship_stats_service import (
    get_current_stats,
    invalidate_hangar_cache,
    invalidate_ship_cache,
)

router = APIRouter(prefix="/ships", tags=["ships"])

def _enum_val(v) -> str:
    """Retourne la valeur string d'un enum ou la string elle-même."""
    return v.value if hasattr(v, 'value') else str(v)

@router.get("", response_model=list[ShipSummaryOut])
async def list_ships(player: CurrentPlayer, db: DbDep) -> list[ShipSummaryOut]:
    """
    Retourne tous les vaisseaux du joueur (statuts DOCKED, IN_FLEET, IN_FORGE).
    """
    result = await db.execute(
        select(Ship).where(Ship.owner_id == player.id)
    )
    ships = result.scalars().all()

    return [
        ShipSummaryOut(
            id=s.id,
            ship_type=s.ship_type,
            ship_class=_enum_val(s.class_),
            rarity=_enum_val(s.rarity),
            grade=s.grade,
            status=_enum_val(s.status),
            planet_id=s.planet_id,
        )
        for s in ships
    ]


@router.get("/{ship_id}", response_model=ShipDetailOut)
async def get_ship(ship_id: uuid.UUID, player: CurrentPlayer, db: DbDep) -> ShipDetailOut:
    """
    Retourne le détail complet d'un vaisseau avec current_stats calculé.
    """
    result = await db.execute(select(Ship).where(Ship.id == ship_id))
    ship: Ship | None = result.scalar_one_or_none()

    if ship is None or ship.owner_id != player.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vaisseau introuvable.")

    current = await get_current_stats(ship_id, db)

    return ShipDetailOut(
        id=ship.id,
        ship_type=ship.ship_type,
        ship_class=_enum_val(ship.class_),
        rarity=_enum_val(ship.rarity),
        grade=ship.grade,
        combat_xp=ship.combat_xp,
        status=_enum_val(ship.status),
        parent_ship_id=ship.parent_ship_id,
        base_stats=ship.base_stats,
        current_stats=current,
    )


@router.post("/build", response_model=BuildShipResponse, status_code=status.HTTP_201_CREATED)
async def build_ship_endpoint(
    body: BuildShipRequest,
    player: CurrentPlayer,
    db: DbDep,
) -> BuildShipResponse:
    """
    Lance la fabrication d'un vaisseau.
    Déduit les ressources, tire RNG, applique Pedigree optionnel.
    """
    await check_rate_limit(str(player.id), "ships:build")
    ship = await build_ship(
        db=db,
        player_id=player.id,
        ship_type=body.ship_type,
        planet_id=body.planet_id,
        parent_ship_id=body.parent_ship_id,
    )

    # Flush pour que PostgreSQL génère l'UUID server_default
    await db.flush()
    await db.refresh(ship)

    rarity_key = ship.rarity.value if hasattr(ship.rarity, 'value') else ship.rarity
    total_slots, premium_slots = _RARITY_SLOTS[rarity_key]

    return BuildShipResponse(
        ship_id=ship.id,
        rarity=rarity_key,
        ship_class=ship.class_.value if hasattr(ship.class_, 'value') else ship.class_,
        base_stats=ship.base_stats,
        slots_total=total_slots,
        slots_premium=premium_slots,
        pedigree_applied=ship.parent_ship_id is not None,
    )


@router.delete("/{ship_id}", status_code=status.HTTP_204_NO_CONTENT)
async def demolish_ship(
    ship_id: uuid.UUID,
    player: CurrentPlayer,
    db: DbDep,
) -> Response:
    """
    Démolition volontaire d'un vaisseau.
    - Seuls les vaisseaux DOCKED peuvent être démolis.
    - Si Grade ≥ 3, marque parent_ship_id pour permettre un Pedigree
      sur le prochain build du même type (logique dans build_ship).
    """
    result = await db.execute(
        select(Ship).where(Ship.id == ship_id).with_for_update()
    )
    ship: Ship | None = result.scalar_one_or_none()

    if ship is None or ship.owner_id != player.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vaisseau introuvable.")

    if ship.status != ShipStatus.DOCKED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Impossible de démolir un vaisseau {ship.status.value}.",
        )

    await db.delete(ship)
    await invalidate_ship_cache(ship_id)
    await invalidate_hangar_cache(player.id)
    return Response(status_code=204)