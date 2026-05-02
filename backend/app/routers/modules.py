"""
app/routers/modules.py
GET    /ships/{id}/modules          — liste des modules installés
PUT    /ships/{id}/modules/{slot}   — installer/remplacer un module
DELETE /ships/{id}/modules/{slot}   — retirer un module

Validations serveur (Agent 3) :
  - Propriété du vaisseau vérifiée avant toute opération
  - Slot valide pour la rareté du vaisseau
  - Module niveau IV/V → slot premium obligatoire
  - Cap +150% vérifié dans ship_stats_service et retourné dans cap_reached
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from fastapi import Response


from app.core.deps import CurrentPlayer, DbDep
from app.middleware.rate_limit import check_rate_limit
from app.models.models import Ship, ShipModule, ShipStatus
from app.schemas.ship import InstallModuleRequest, ModuleInstallResponse
from app.services.ship_stats_service import (
    _load_ship_with_modules,
    compute_and_store_stats,
    invalidate_ship_cache,
    validate_module_slot,
)

router = APIRouter(prefix="/ships", tags=["modules"])


@router.get("/{ship_id}/modules")
async def list_modules(
    ship_id: uuid.UUID,
    player: CurrentPlayer,
    db: DbDep,
) -> list[dict]:
    """Retourne les modules installés triés par slot_index."""
    ship = await _get_owned_ship(ship_id, player.id, db)
    _, modules = await _load_ship_with_modules(ship_id, db)

    return [
        {
            "slot": m.slot_index,
            "type": m.module_type.value if hasattr(m.module_type, "value") else m.module_type,
            "level": m.level,
            "affinity_bonus": m.affinity_bonus,
        }
        for m in modules
    ]


@router.put("/{ship_id}/modules/{slot_index}", response_model=ModuleInstallResponse)
async def install_module(
    ship_id: uuid.UUID,
    slot_index: int,
    body: InstallModuleRequest,
    player: CurrentPlayer,
    db: DbDep,
) -> ModuleInstallResponse:
    """
    Installe ou remplace un module dans un slot.
    Invalide le cache Redis et retourne les current_stats mises à jour.
    """
    await check_rate_limit(str(player.id), "modules:install")
    ship = await _get_owned_ship(ship_id, player.id, db)

    if ship.status == ShipStatus.IN_FORGE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Impossible de modifier un vaisseau en cours de forge.",
        )

    # Validation du slot
    is_valid, err = validate_module_slot(ship, slot_index, body.level)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=err)

    # Upsert du module (INSERT ou UPDATE selon existence)
    existing = await db.execute(
        select(ShipModule).where(
            ShipModule.ship_id == ship_id,
            ShipModule.slot_index == slot_index,
        )
    )
    mod: ShipModule | None = existing.scalar_one_or_none()

    # Calcul affinité (pour stockage)
    from app.services.ship_stats_service import _MODULE_EFFECT
    effect = _MODULE_EFFECT.get(body.module_type, {})
    has_affinity = (ship.class_.value == effect.get("affinity_class", ""))

    if mod is None:
        mod = ShipModule(
            id=uuid.uuid4(),
            ship_id=ship_id,
            slot_index=slot_index,
            module_type=body.module_type,
            level=body.level,
            affinity_bonus=has_affinity,
        )
        db.add(mod)
    else:
        mod.module_type = body.module_type
        mod.level = body.level
        mod.affinity_bonus = has_affinity
        db.add(mod)

    # Invalide le cache avant de recalculer
    await invalidate_ship_cache(ship_id)

    # Recharge les modules (dont le nouveau) pour recalculer les stats
    _, modules = await _load_ship_with_modules(ship_id, db)
    current_stats = await compute_and_store_stats(ship, modules)

    return ModuleInstallResponse(
        current_stats=current_stats,
        cap_reached=current_stats.get("cap_reached", []),
    )


@router.delete("/{ship_id}/modules/{slot_index}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_module(
    ship_id: uuid.UUID,
    slot_index: int,
    player: CurrentPlayer,
    db: DbDep,
) -> Response:
    """Retire un module d'un slot. Le joueur récupère le module."""
    ship = await _get_owned_ship(ship_id, player.id, db)

    result = await db.execute(
        select(ShipModule).where(
            ShipModule.ship_id == ship_id,
            ShipModule.slot_index == slot_index,
        )
    )
    mod = result.scalar_one_or_none()
    if mod is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Aucun module installé dans le slot {slot_index}.",
        )

    await db.delete(mod)
    await invalidate_ship_cache(ship_id)

    return Response(status_code=204)



# ---------------------------------------------------------------------------
# Helper privé
# ---------------------------------------------------------------------------

async def _get_owned_ship(ship_id: uuid.UUID, player_id: uuid.UUID, db) -> Ship:
    """Charge un vaisseau et vérifie qu'il appartient au joueur. Lève 404 sinon."""
    result = await db.execute(select(Ship).where(Ship.id == ship_id))
    ship: Ship | None = result.scalar_one_or_none()
    if ship is None or ship.owner_id != player_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vaisseau introuvable.")
    return ship
