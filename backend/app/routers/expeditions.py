"""
app/routers/expeditions.py
Agent 5 — Backend

GET  /expeditions/active          — expéditions en cours
POST /expeditions/launch          — lancer une expédition
GET  /expeditions/:id/result      — résultat d'une expédition terminée
GET  /expeditions/history         — historique (50 dernières)
"""
from __future__ import annotations

import uuid
import math
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.core.deps import CurrentPlayer, DbDep
from app.models.models import Planet, Ship, ShipStatus
from app.services.expedition_service import (
    ExpeditionDuration, DURATION_HOURS, DURATION_COST,
    resolve_expedition, EXPEDITION_EVENTS,
)

router = APIRouter(prefix="/expeditions", tags=["expeditions"])

# ---------------------------------------------------------------------------
# Modèle BDD simple — on stocke en JSON dans une table expedition_logs
# ---------------------------------------------------------------------------
# Pour ne pas créer une nouvelle migration complexe, on utilise un champ
# JSON dans la table des joueurs ou une table légère.
# Architecture simplifiée : tout en mémoire Redis (TTL 24h) + log BDD optionnel

# ---------------------------------------------------------------------------
# Stockage en mémoire (Redis-like via dict pour la démo — remplacer par Redis)
# ---------------------------------------------------------------------------
_active_expeditions: dict[str, dict] = {}  # expedition_id → données
_expedition_history: dict[str, list] = {}  # player_id → liste

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class LaunchExpeditionRequest(BaseModel):
    ship_ids: list[uuid.UUID]
    duration: ExpeditionDuration


class ExpeditionOut(BaseModel):
    expedition_id: str
    ship_ids: list[str]
    duration: str
    launched_at: str
    returns_at: str
    eta_seconds: int
    is_complete: bool
    result: dict | None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/active", response_model=list[ExpeditionOut])
async def get_active_expeditions(player: CurrentPlayer, db: DbDep) -> list[ExpeditionOut]:
    """Retourne toutes les expéditions actives du joueur."""
    player_id = str(player.id)
    now = datetime.now(UTC)
    active = []

    for exp_id, exp in list(_active_expeditions.items()):
        if exp.get("player_id") != player_id:
            continue

        returns_at = datetime.fromisoformat(exp["returns_at"])
        is_complete = returns_at <= now
        eta = max(0, int((returns_at - now).total_seconds()))

        result = None
        if is_complete and not exp.get("resolved"):
            # Résoudre automatiquement
            try:
                result = await resolve_expedition(
                    expedition_id=exp_id,
                    ship_ids=[uuid.UUID(sid) for sid in exp["ship_ids"]],
                    duration=ExpeditionDuration(exp["duration"]),
                    db=db,
                )
                _active_expeditions[exp_id]["resolved"] = True
                _active_expeditions[exp_id]["result"] = result
                # Remettre les vaisseaux en DOCKED
                for sid in exp["ship_ids"]:
                    r = await db.execute(select(Ship).where(Ship.id == uuid.UUID(sid)))
                    ship = r.scalar_one_or_none()
                    if ship:
                        ship.status = ShipStatus.DOCKED
                        db.add(ship)
            except Exception as e:
                result = {"error": str(e)}

        active.append(ExpeditionOut(
            expedition_id=exp_id,
            ship_ids=exp["ship_ids"],
            duration=exp["duration"],
            launched_at=exp["launched_at"],
            returns_at=exp["returns_at"],
            eta_seconds=eta,
            is_complete=is_complete,
            result=_active_expeditions[exp_id].get("result"),
        ))

    return active


@router.post("/launch", response_model=ExpeditionOut, status_code=201)
async def launch_expedition(
    body: LaunchExpeditionRequest,
    player: CurrentPlayer,
    db: DbDep,
) -> ExpeditionOut:
    """Lance une expédition avec les vaisseaux sélectionnés."""

    if not body.ship_ids:
        raise HTTPException(status_code=400, detail="Sélectionnez au moins un vaisseau.")
    if len(body.ship_ids) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 vaisseaux par expédition.")

    # Vérifier les vaisseaux
    ships = []
    for sid in body.ship_ids:
        r = await db.execute(select(Ship).where(Ship.id == sid))
        ship = r.scalar_one_or_none()
        if not ship or ship.owner_id != player.id:
            raise HTTPException(status_code=404, detail=f"Vaisseau {sid} introuvable.")
        if ship.status != ShipStatus.DOCKED:
            raise HTTPException(status_code=409, detail=f"Vaisseau {ship.ship_type} n'est pas amarré.")
        ships.append(ship)

    # Vérifier le coût en deutérium
    cost = DURATION_COST[body.duration]
    r = await db.execute(select(Planet).where(Planet.owner_id == player.id, Planet.is_homeworld == True))  # noqa: E712
    homeworld = r.scalar_one_or_none()
    if not homeworld:
        raise HTTPException(status_code=404, detail="Planète natale introuvable.")

    deut_needed = cost.get("deuterium", 0)
    if math.floor(float(homeworld.deuterium)) < deut_needed:
        raise HTTPException(
            status_code=402,
            detail=f"Deutérium insuffisant. Requis : {deut_needed}, disponible : {math.floor(float(homeworld.deuterium))}"
        )

    # Déduire le deutérium
    homeworld.deuterium = float(homeworld.deuterium) - deut_needed
    db.add(homeworld)

    # Marquer les vaisseaux comme IN_FLEET
    for ship in ships:
        ship.status = ShipStatus.IN_FLEET
        db.add(ship)

    # Créer l'expédition
    now = datetime.now(UTC)
    hours = DURATION_HOURS[body.duration]
    returns_at = now + timedelta(hours=hours)
    exp_id = str(uuid.uuid4())

    _active_expeditions[exp_id] = {
        "player_id": str(player.id),
        "ship_ids": [str(sid) for sid in body.ship_ids],
        "duration": body.duration.value,
        "launched_at": now.isoformat(),
        "returns_at": returns_at.isoformat(),
        "resolved": False,
        "result": None,
    }

    return ExpeditionOut(
        expedition_id=exp_id,
        ship_ids=[str(sid) for sid in body.ship_ids],
        duration=body.duration.value,
        launched_at=now.isoformat(),
        returns_at=returns_at.isoformat(),
        eta_seconds=int((returns_at - now).total_seconds()),
        is_complete=False,
        result=None,
    )


@router.get("/events")
async def get_expedition_events() -> list[dict]:
    """Retourne les types d'événements possibles (pour l'UI d'info)."""
    return [
        {"id": e["id"], "title": e["title"], "weight": e["weight"]}
        for e in EXPEDITION_EVENTS
    ]
