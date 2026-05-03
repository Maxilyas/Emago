"""
app/routers/modules.py
Système d'inventaire de modules — Phase 1.

Endpoints ships/{id}/modules (inchangés côté URL) :
  GET    /ships/{id}/modules          — modules installés
  PUT    /ships/{id}/modules/{slot}   — installer depuis inventaire
  DELETE /ships/{id}/modules/{slot}   — désinstaller → retour inventaire

Nouveaux endpoints /modules :
  GET  /modules                       — inventaire complet du joueur
  GET  /modules/shards                — compteurs de shards par type
  POST /modules/craft                 — artisanat 3:1

Nouveaux endpoints /loot-crates :
  GET  /loot-crates                   — caisses non ouvertes
  POST /loot-crates/{id}/open         — ouvrir une caisse
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from fastapi import Response

from app.core.deps import CurrentPlayer, DbDep
from app.middleware.rate_limit import check_rate_limit
from app.models.models import LootCrate, PlayerModule, Ship, ShipModule, ShipStatus
from app.schemas.modules import (
    CraftModuleRequest,
    InstallModuleFromInventoryRequest,
    LootCrateOpenResult,
    LootCrateOut,
    PlayerModuleOut,
    ShardCountOut,
)
from app.schemas.ship import ModuleInstallResponse
from app.services.module_inventory_service import (
    craft_module,
    create_loot_crate,
    get_inventory,
    get_shard_counts,
    install_module,
    open_loot_crate,
    uninstall_module,
)
from app.services.ship_stats_service import (
    _load_ship_with_modules,
    compute_and_store_stats,
    invalidate_ship_cache,
)

router = APIRouter(tags=["modules"])


# ---------------------------------------------------------------------------
# Inventaire
# ---------------------------------------------------------------------------

@router.get("/modules", response_model=list[PlayerModuleOut])
async def list_inventory(player: CurrentPlayer, db: DbDep) -> list[PlayerModuleOut]:
    """Retourne l'inventaire complet de modules du joueur (y compris détruits)."""
    mods = await get_inventory(player.id, db)
    return [PlayerModuleOut.model_validate(m) for m in mods]


@router.get("/modules/shards", response_model=ShardCountOut)
async def get_shards(player: CurrentPlayer, db: DbDep) -> ShardCountOut:
    """Retourne les compteurs de shards par type de module."""
    counts = await get_shard_counts(player.id, db)
    return ShardCountOut(shards=counts)


@router.post("/modules/craft", response_model=PlayerModuleOut, status_code=status.HTTP_201_CREATED)
async def craft_module_endpoint(
    body: CraftModuleRequest,
    player: CurrentPlayer,
    db: DbDep,
) -> PlayerModuleOut:
    """Fusionne 3 modules identiques → 1 module de niveau supérieur."""
    await check_rate_limit(str(player.id), "modules:craft")
    result = await craft_module(
        player_id=player.id,
        source_ids=list(body.module_ids),
        planet_id=body.planet_id,
        db=db,
    )
    return PlayerModuleOut.model_validate(result)


# ---------------------------------------------------------------------------
# Loot crates
# ---------------------------------------------------------------------------

@router.get("/loot-crates", response_model=list[LootCrateOut])
async def list_loot_crates(player: CurrentPlayer, db: DbDep) -> list[LootCrateOut]:
    """Retourne les caisses de butin non ouvertes du joueur."""
    result = await db.execute(
        select(LootCrate)
        .where(LootCrate.player_id == player.id, LootCrate.opened == False)  # noqa: E712
        .order_by(LootCrate.obtained_at.desc())
    )
    crates = result.scalars().all()
    return [LootCrateOut.model_validate(c) for c in crates]


@router.post("/loot-crates/{crate_id}/open", response_model=LootCrateOpenResult)
async def open_crate_endpoint(
    crate_id: uuid.UUID,
    player: CurrentPlayer,
    db: DbDep,
) -> LootCrateOpenResult:
    """Ouvre une caisse de butin et retourne le contenu."""
    await check_rate_limit(str(player.id), "modules:open_crate")
    result = await open_loot_crate(player.id, crate_id, db)
    mod = result["module"]
    return LootCrateOpenResult(
        crate_id=crate_id,
        module=PlayerModuleOut.model_validate(mod) if mod else None,
        shards=result["shards"],
        empty=result["empty"],
    )


# ---------------------------------------------------------------------------
# Installation / désinstallation (routes /ships/{id}/modules)
# ---------------------------------------------------------------------------

@router.get("/ships/{ship_id}/modules")
async def list_installed_modules(
    ship_id: uuid.UUID,
    player: CurrentPlayer,
    db: DbDep,
) -> list[dict]:
    """Retourne les modules installés sur le vaisseau, triés par slot."""
    ship = await _get_owned_ship(ship_id, player.id, db)
    _, modules = await _load_ship_with_modules(ship_id, db)

    result = []
    for m in modules:
        entry: dict = {
            "slot":          m.slot_index,
            "type":          m.module_type.value if hasattr(m.module_type, "value") else m.module_type,
            "level":         m.level,
            "affinity_bonus": m.affinity_bonus,
        }
        # Informations enrichies depuis le PlayerModule si disponible
        if m.player_module is not None:
            pm = m.player_module
            entry["player_module_id"]     = str(pm.id)
            entry["trait"]                = pm.trait
            entry["trait_value"]          = pm.trait_value
            entry["bonus_trait"]          = pm.bonus_trait
            entry["is_corrupted"]         = pm.is_corrupted
            entry["corruption_malus_stat"]  = pm.corruption_malus_stat
            entry["corruption_malus_value"] = pm.corruption_malus_value
            entry["reinstall_charges"]    = pm.reinstall_charges
            entry["memory_ship_name"]     = pm.memory_ship_name
        result.append(entry)
    return result


@router.put(
    "/ships/{ship_id}/modules/{slot_index}",
    response_model=ModuleInstallResponse,
)
async def install_module_endpoint(
    ship_id: uuid.UUID,
    slot_index: int,
    body: InstallModuleFromInventoryRequest,
    player: CurrentPlayer,
    db: DbDep,
) -> ModuleInstallResponse:
    """
    Installe un module depuis l'inventaire sur le slot indiqué.
    Si le slot est déjà occupé, l'ancien module est renvoyé dans l'inventaire (-1 charge).
    """
    await check_rate_limit(str(player.id), "modules:install")
    current_stats = await install_module(
        player_id=player.id,
        module_id=body.module_id,
        ship_id=ship_id,
        slot_index=slot_index,
        db=db,
    )
    return ModuleInstallResponse(
        current_stats=current_stats,
        cap_reached=current_stats.get("cap_reached", []),
    )


@router.delete(
    "/ships/{ship_id}/modules/{slot_index}",
    status_code=status.HTTP_200_OK,
)
async def remove_module_endpoint(
    ship_id: uuid.UUID,
    slot_index: int,
    player: CurrentPlayer,
    db: DbDep,
) -> dict:
    """
    Retire un module du slot — retourne dans l'inventaire (-1 charge).
    Retourne {destroyed: bool} pour informer le client si le module a été détruit.
    """
    _, destroyed = await uninstall_module(
        player_id=player.id,
        ship_id=ship_id,
        slot_index=slot_index,
        db=db,
    )
    return {"destroyed": destroyed}


# ---------------------------------------------------------------------------
# Helper privé
# ---------------------------------------------------------------------------

async def _get_owned_ship(ship_id: uuid.UUID, player_id: uuid.UUID, db) -> Ship:
    result = await db.execute(select(Ship).where(Ship.id == ship_id))
    ship: Ship | None = result.scalar_one_or_none()
    if ship is None or ship.owner_id != player_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Vaisseau introuvable.")
    return ship
