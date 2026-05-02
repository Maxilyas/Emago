"""
app/routers/<name>.py — <description>
Agent 5 — Développeur Backend

Conventions Emago appliquées :
- Préfixe /api/v1/<name>, tags pour Swagger
- CurrentPlayer + DbDep injectés
- Helper _get_owned_<resource> → 404 anti-énumération
- Codes erreur français
- Routes statiques avant paramétrées
- with_for_update sur mutations
- math.floor pour comparer ressources
- Délégation logique métier au service
- invalidation cache Redis
- publish_event WS canal player:{id}
"""
from __future__ import annotations

import math
from datetime import datetime, UTC
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentPlayer, DbDep
from app.core.redis_client import publish_event
from app.models.models import (
    Player,
    Planet,
    # Ship,        # importer ce qui est utile
    # ShipStatus,
)
# from app.services import <feature>_service
# from app.services.ship_stats_service import invalidate_ship_cache, invalidate_hangar_cache


router = APIRouter(prefix="/<name>", tags=["<name>"])


# ─── Schémas Pydantic ───────────────────────────────────────────────────────

class CreateXxxRequest(BaseModel):
    """Body pour POST /<name>"""
    name: str = Field(..., min_length=3, max_length=64)
    target_id: UUID
    # … champs spécifiques


class XxxResponse(BaseModel):
    """Response pour GET /<name>/{id} et POST /<name>"""
    id: UUID
    name: str
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Helpers privés ─────────────────────────────────────────────────────────

async def _get_owned_xxx(xxx_id: UUID, player_id: UUID, db: AsyncSession):
    """
    Lève 404 si introuvable OU pas owner — anti-énumération.

    NE JAMAIS lever 403 pour ressource d'autrui. Le 404 empêche la découverte d'IDs.
    """
    # Adapter le modèle SQLAlchemy
    # res = (await db.execute(
    #     select(Xxx).where(Xxx.id == xxx_id)
    # )).scalar_one_or_none()
    # if not res or res.owner_id != player_id:
    #     raise HTTPException(status_code=404, detail="Xxx introuvable.")
    # return res
    raise NotImplementedError


def _check_resources(planet: Planet, cost: dict[str, int]) -> None:
    """
    Compare ressources avec math.floor pour éviter bug arrondi (1999.87 vs 2000).
    Lève 402 avec message FR si insuffisant.
    """
    available = {
        "metal": math.floor(float(planet.metal)),
        "crystal": math.floor(float(planet.crystal)),
        "deuterium": math.floor(float(planet.deuterium)),
    }
    if any(available.get(k, 0) < cost.get(k, 0) for k in cost):
        raise HTTPException(
            status_code=402,
            detail=(
                f"Ressources insuffisantes. "
                f"Requis : métal={cost.get('metal',0)}, "
                f"cristal={cost.get('crystal',0)}, "
                f"deutérium={cost.get('deuterium',0)}. "
                f"Disponible : métal={available['metal']}, "
                f"cristal={available['crystal']}, "
                f"deutérium={available['deuterium']}."
            ),
        )


# ─── Endpoints ──────────────────────────────────────────────────────────────

# ⚠️ ROUTES STATIQUES TOUJOURS AVANT ROUTES PARAMÉTRÉES
# Sinon FastAPI tente de parser "history" comme UUID → 422.

@router.get("", response_model=list[XxxResponse])
async def list_xxx(player: CurrentPlayer, db: DbDep) -> list[XxxResponse]:
    """Retourne les éléments du joueur."""
    # res = (await db.execute(
    #     select(Xxx).where(Xxx.owner_id == player.id)
    # )).scalars().all()
    # return [XxxResponse.model_validate(x) for x in res]
    raise NotImplementedError


@router.get("/history", response_model=list[XxxResponse])
async def get_xxx_history(player: CurrentPlayer, db: DbDep) -> list[XxxResponse]:
    """Historique. ⚠️ DÉFINI AVANT /{xxx_id}."""
    raise NotImplementedError


@router.get("/{xxx_id}", response_model=XxxResponse)
async def get_xxx(xxx_id: UUID, player: CurrentPlayer, db: DbDep) -> XxxResponse:
    """Détail d'un élément. 404 si pas owner (anti-énumération)."""
    xxx = await _get_owned_xxx(xxx_id, player.id, db)
    return XxxResponse.model_validate(xxx)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=XxxResponse)
async def create_xxx(
    body: CreateXxxRequest,
    player: CurrentPlayer,
    db: DbDep,
) -> XxxResponse:
    """
    Crée un élément.

    Validations :
    - Ressources suffisantes (math.floor)
    - Statut OK
    - Pas de doublon

    Raises:
        402 si ressources insuffisantes
        404 si target introuvable
        409 si conflit d'état
        422 si validation Pydantic
    """
    # 1. SELECT FOR UPDATE planète
    # planet = (await db.execute(
    #     select(Planet)
    #     .where(Planet.owner_id == player.id, Planet.is_homeworld == True)
    #     .with_for_update()
    # )).scalar_one_or_none()
    #
    # if not planet:
    #     raise HTTPException(status_code=404, detail="Planète natale introuvable.")
    #
    # 2. Check ressources
    # cost = {"metal": 1000, "crystal": 500}  # adapter
    # _check_resources(planet, cost)
    #
    # 3. Déduction ressources
    # planet.metal -= cost["metal"]
    # planet.crystal -= cost["crystal"]
    # db.add(planet)
    #
    # 4. Délégation au service
    # xxx = await xxx_service.create_xxx(db, player_id=player.id, body=body)
    # await db.flush()
    #
    # 5. Invalidation cache (si applicable)
    # await invalidate_hangar_cache(player.id)
    #
    # 6. Publish WS event (si applicable)
    # await publish_event(
    #     channel=f"player:{player.id}",
    #     event={"type": "xxx.created", "data": {"xxx_id": str(xxx.id)}},
    # )
    #
    # 7. Réponse
    # return XxxResponse.model_validate(xxx)
    raise NotImplementedError


@router.delete("/{xxx_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_xxx(xxx_id: UUID, player: CurrentPlayer, db: DbDep) -> None:
    """
    Supprime un élément.

    Raises:
        404 si introuvable ou pas owner (anti-énumération)
        409 si statut bloquant (ex. IN_FLEET, IN_FORGE)
    """
    # 1. Lock + ownership
    # xxx = (await db.execute(
    #     select(Xxx).where(Xxx.id == xxx_id).with_for_update()
    # )).scalar_one_or_none()
    # if not xxx or xxx.owner_id != player.id:
    #     raise HTTPException(status_code=404, detail="Xxx introuvable.")
    #
    # 2. Check statut
    # if xxx.status != Status.IDLE:
    #     raise HTTPException(
    #         status_code=409,
    #         detail=f"Impossible de supprimer un xxx {xxx.status.value}.",
    #     )
    #
    # 3. Delete
    # await db.delete(xxx)
    # await invalidate_<resource>_cache(xxx_id)
    raise NotImplementedError


# ─── Optionnel : endpoint avec rôle requis (cf. alliances) ──────────────────

# async def _require_role(alliance_id: UUID, player_id: UUID, min_role: str, db) -> AllianceMember:
#     """Lève 403 si rôle insuffisant. Membre < Officier < Leader."""
#     member = (await db.execute(
#         select(AllianceMember).where(
#             AllianceMember.alliance_id == alliance_id,
#             AllianceMember.player_id == player_id,
#         )
#     )).scalar_one_or_none()
#
#     ROLE_HIERARCHY = {"MEMBER": 0, "OFFICER": 1, "LEADER": 2}
#     if not member or ROLE_HIERARCHY.get(member.role, -1) < ROLE_HIERARCHY.get(min_role, 99):
#         raise HTTPException(status_code=403, detail="Rôle insuffisant pour cette action.")
#     return member


# ─── Optionnel : endpoint avec body & rate-limit ────────────────────────────

# @router.post("/sensitive-action", status_code=201)
# async def sensitive_action(
#     body: SensitiveRequest,
#     player: CurrentPlayer,
#     db: DbDep,
# ) -> SensitiveResponse:
#     """
#     Action sensible avec rate-limit.
#
#     Rate-limit : 5/min via app/middleware/rate_limit.py _LIMITS.
#     """
#     # ... logique ...
