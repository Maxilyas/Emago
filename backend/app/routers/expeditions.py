"""
app/routers/expeditions.py — v2
Agent 5 — Développeur Backend

Fix critique : stockage des expéditions migré de dict Python en mémoire
vers Redis (TTL 48h). Le dict en mémoire était vidé à chaque redémarrage
d'Uvicorn → vaisseaux bloqués IN_FLEET indéfiniment.

Clé Redis : expedition:{expedition_id}  → JSON de l'expédition
Index :     player_expeditions:{player_id} → SET d'expedition_ids actifs

GET  /expeditions/active     — expéditions en cours
POST /expeditions/launch     — lancer une expédition
GET  /expeditions/history    — historique (50 dernières)
GET  /expeditions/events     — types d'événements possibles
GET  /expeditions/:id/result — résultat d'une expédition terminée
"""
from __future__ import annotations

import json
import math
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.core.deps import CurrentPlayer, DbDep
from app.core.redis_client import get_redis
from app.models.models import Planet, Ship, ShipStatus
from app.services.expedition_service import (
    DURATION_COST, DURATION_HOURS, EXPEDITION_EVENTS,
    ExpeditionDuration, resolve_expedition,
)

router = APIRouter(prefix="/expeditions", tags=["expeditions"])

# TTL Redis : 48h (les expéditions durent max 12h + marge pour récupérer le résultat)
_EXPEDITION_TTL = 48 * 3600

# ---------------------------------------------------------------------------
# Helpers Redis
# ---------------------------------------------------------------------------

def _exp_key(exp_id: str) -> str:
    return f"expedition:{exp_id}"

def _player_index_key(player_id: str) -> str:
    return f"player_expeditions:{player_id}"


async def _save_expedition(exp_id: str, data: dict, player_id: str) -> None:
    """Sauvegarde une expédition dans Redis + l'ajoute à l'index joueur."""
    r = get_redis()
    await r.setex(_exp_key(exp_id), _EXPEDITION_TTL, json.dumps(data))
    await r.sadd(_player_index_key(player_id), exp_id)
    await r.expire(_player_index_key(player_id), _EXPEDITION_TTL)


async def _get_expedition(exp_id: str) -> dict | None:
    """Lit une expédition depuis Redis."""
    r = get_redis()
    raw = await r.get(_exp_key(exp_id))
    if raw is None:
        return None
    return json.loads(raw)


async def _update_expedition(exp_id: str, data: dict) -> None:
    """Met à jour une expédition sans changer le TTL."""
    r = get_redis()
    ttl = await r.ttl(_exp_key(exp_id))
    if ttl > 0:
        await r.setex(_exp_key(exp_id), ttl, json.dumps(data))
    else:
        await r.setex(_exp_key(exp_id), _EXPEDITION_TTL, json.dumps(data))


async def _get_player_expedition_ids(player_id: str) -> list[str]:
    """Retourne tous les IDs d'expéditions d'un joueur depuis l'index Redis."""
    r = get_redis()
    ids = await r.smembers(_player_index_key(player_id))
    return list(ids)


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

# CRITIQUE : routes statiques AVANT /:id pour éviter les conflits FastAPI

@router.get("/active", response_model=list[ExpeditionOut])
async def get_active_expeditions(player: CurrentPlayer, db: DbDep) -> list[ExpeditionOut]:
    """Retourne toutes les expéditions actives du joueur (depuis Redis)."""
    player_id = str(player.id)
    now = datetime.now(UTC)
    active = []

    exp_ids = await _get_player_expedition_ids(player_id)

    for exp_id in exp_ids:
        exp = await _get_expedition(exp_id)
        if exp is None:
            continue  # Expédition expirée du cache Redis
        if exp.get("player_id") != player_id:
            continue

        returns_at = datetime.fromisoformat(exp["returns_at"])
        is_complete = returns_at <= now
        eta = max(0, int((returns_at - now).total_seconds()))

        result = exp.get("result")

        # Résolution automatique si terminée et pas encore résolue
        if is_complete and not exp.get("resolved"):
            try:
                result = await resolve_expedition(
                    expedition_id=exp_id,
                    ship_ids=[uuid.UUID(sid) for sid in exp["ship_ids"]],
                    duration=ExpeditionDuration(exp["duration"]),
                    db=db,
                )
                exp["resolved"] = True
                exp["result"] = result

                # Remettre les vaisseaux en DOCKED
                for sid in exp["ship_ids"]:
                    r = await db.execute(select(Ship).where(Ship.id == uuid.UUID(sid)))
                    ship = r.scalar_one_or_none()
                    if ship and ship.status == ShipStatus.IN_FLEET:
                        ship.status = ShipStatus.DOCKED
                        db.add(ship)

                await db.commit()
                await _update_expedition(exp_id, exp)

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
            result=result,
        ))

    return active


@router.get("/history", response_model=list[ExpeditionOut])
async def get_expedition_history(player: CurrentPlayer, db: DbDep) -> list[ExpeditionOut]:
    """Retourne les expéditions terminées du joueur (depuis Redis, triées par date)."""
    player_id = str(player.id)
    now = datetime.now(UTC)

    exp_ids = await _get_player_expedition_ids(player_id)
    history = []

    for exp_id in exp_ids:
        exp = await _get_expedition(exp_id)
        if exp is None or exp.get("player_id") != player_id:
            continue

        returns_at = datetime.fromisoformat(exp["returns_at"])
        if returns_at > now:
            continue  # pas encore terminée

        history.append(ExpeditionOut(
            expedition_id=exp_id,
            ship_ids=exp["ship_ids"],
            duration=exp["duration"],
            launched_at=exp["launched_at"],
            returns_at=exp["returns_at"],
            eta_seconds=0,
            is_complete=True,
            result=exp.get("result"),
        ))

    # Trier par date de retour décroissante, limiter à 50
    history.sort(key=lambda e: e.returns_at, reverse=True)
    return history[:50]


@router.get("/events")
async def get_expedition_events() -> list[dict]:
    """Retourne les types d'événements possibles (pour l'UI d'info)."""
    return [
        {"id": e["id"], "title": e["title"], "weight": e["weight"]}
        for e in EXPEDITION_EVENTS
    ]


@router.post("/launch", response_model=ExpeditionOut, status_code=201)
async def launch_expedition(
    body: LaunchExpeditionRequest,
    player: CurrentPlayer,
    db: DbDep,
) -> ExpeditionOut:
    """Lance une expédition. Stocke les données dans Redis (survit aux redémarrages)."""

    if not body.ship_ids:
        raise HTTPException(status_code=400, detail="Sélectionnez au moins un vaisseau.")
    if len(body.ship_ids) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 vaisseaux par expédition.")

    # Valider les vaisseaux
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
    r = await db.execute(
        select(Planet).where(Planet.owner_id == player.id, Planet.is_homeworld == True)  # noqa: E712
    )
    homeworld = r.scalar_one_or_none()
    if not homeworld:
        raise HTTPException(status_code=404, detail="Planète natale introuvable.")

    deut_needed = cost.get("deuterium", 0)
    if math.floor(float(homeworld.deuterium)) < deut_needed:
        raise HTTPException(
            status_code=402,
            detail=f"Deutérium insuffisant. Requis : {deut_needed}, disponible : {math.floor(float(homeworld.deuterium))}",
        )

    # Déduire le deutérium + marquer les vaisseaux IN_FLEET
    homeworld.deuterium = float(homeworld.deuterium) - deut_needed
    db.add(homeworld)

    for ship in ships:
        ship.status = ShipStatus.IN_FLEET
        db.add(ship)

    await db.commit()

    # Créer l'expédition dans Redis
    now = datetime.now(UTC)
    hours = DURATION_HOURS[body.duration]
    returns_at = now + timedelta(hours=hours)
    exp_id = str(uuid.uuid4())

    exp_data = {
        "player_id": str(player.id),
        "ship_ids": [str(sid) for sid in body.ship_ids],
        "duration": body.duration.value,
        "launched_at": now.isoformat(),
        "returns_at": returns_at.isoformat(),
        "resolved": False,
        "result": None,
    }

    await _save_expedition(exp_id, exp_data, str(player.id))

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


@router.get("/{expedition_id}/result", response_model=ExpeditionOut)
async def get_expedition_result(
    expedition_id: str,
    player: CurrentPlayer,
    db: DbDep,
) -> ExpeditionOut:
    """Retourne le résultat d'une expédition spécifique."""
    exp = await _get_expedition(expedition_id)
    if exp is None or exp.get("player_id") != str(player.id):
        raise HTTPException(status_code=404, detail="Expédition introuvable.")

    now = datetime.now(UTC)
    returns_at = datetime.fromisoformat(exp["returns_at"])
    is_complete = returns_at <= now
    eta = max(0, int((returns_at - now).total_seconds()))

    return ExpeditionOut(
        expedition_id=expedition_id,
        ship_ids=exp["ship_ids"],
        duration=exp["duration"],
        launched_at=exp["launched_at"],
        returns_at=exp["returns_at"],
        eta_seconds=eta,
        is_complete=is_complete,
        result=exp.get("result"),
    )
