"""
app/routers/fleets.py
POST   /fleets        — envoyer une flotte en mission
DELETE /fleets/:id    — rappeler une flotte (si pas encore arrivée)
GET    /fleets        — liste des flottes actives du joueur

Le calcul de l'heure d'arrivée est fait côté serveur :
    arrival = now + (distance / fleet_speed)
La vitesse de flotte = vitesse du vaisseau le plus lent × FLEET_SPEED_BASE.
"""
from __future__ import annotations

import math
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, text
from fastapi import Response

from app.core.config import get_settings
from app.core.deps import CurrentPlayer, DbDep
from app.core.redis_client import publish_event
from app.middleware.rate_limit import check_rate_limit
from app.models.models import Fleet, FleetMission, Planet, Ship, ShipStatus

router = APIRouter(prefix="/fleets", tags=["fleets"])
settings = get_settings()

# ---------------------------------------------------------------------------
# Schemas locaux
# ---------------------------------------------------------------------------

class SendFleetRequest(BaseModel):
    ship_ids: list[uuid.UUID]
    origin_planet_id: uuid.UUID
    mission: str  # "ATTACK" | "TRANSPORT" | "ESPIONAGE" | "COLONIZE"
    target_galaxy: int
    target_system: int
    target_position: int
    cargo_metal: float = 0.0
    cargo_crystal: float = 0.0
    cargo_deuterium: float = 0.0


class FleetResponse(BaseModel):
    fleet_id: uuid.UUID
    mission: str
    origin_planet_id: uuid.UUID
    target_galaxy: int
    target_system: int
    target_position: int
    departed_at: datetime
    arrives_at: datetime
    ship_count: int


class IncomingFleetResponse(BaseModel):
    """Flotte ennemie en approche — visible par le défenseur."""
    fleet_id: uuid.UUID
    mission: str
    target_galaxy: int
    target_system: int
    target_position: int
    target_planet_id: uuid.UUID | None
    arrives_at: datetime
    ship_count: int
    # Note : on ne révèle PAS origin_planet_id ni owner_id (info militaire)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compute_distance(
    og: int, os: int, op: int,
    tg: int, ts: int, tp: int,
) -> float:
    """
    Distance en unités astronomiques (UA).
    Formule simplifiée OGame-like :
      - Même galaxie : |system_diff| × 5
      - Même système : |position_diff| × 1000
      - Galaxies différentes : |galaxy_diff| × 20000
    """
    if og != tg:
        return abs(og - tg) * 20_000.0
    if os != ts:
        return abs(os - ts) * 5.0 + 1000.0
    return abs(op - tp) * 5.0 + 100.0


def _fleet_speed(ships: list[Ship]) -> float:
    """
    Vitesse de la flotte = vaisseau le plus lent × FLEET_SPEED_BASE.
    La vitesse est extraite de base_stats (en UA/heure).
    """
    speeds = [float(s.base_stats.get("speed", 1.0)) for s in ships]
    return min(speeds) * settings.FLEET_SPEED_BASE


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=list[FleetResponse])
async def list_fleets(player: CurrentPlayer, db: DbDep) -> list[FleetResponse]:
    """Retourne les flottes actives (non rappelées) du joueur."""
    result = await db.execute(
        select(Fleet).where(
            Fleet.owner_id == player.id,
            Fleet.is_recalled == False,  # noqa: E712
        )
    )
    fleets = result.scalars().all()

    out = []
    for f in fleets:
        # Compte les vaisseaux via la table d'association
        count_result = await db.execute(
            text("SELECT COUNT(*) FROM fleet_ships WHERE fleet_id = :fid"),
            {"fid": str(f.id)},
        )
        count = count_result.scalar() or 0
        out.append(FleetResponse(
            fleet_id=f.id,
            mission=f.mission.value if hasattr(f.mission, 'value') else f.mission,
            origin_planet_id=f.origin_planet_id,
            target_galaxy=f.target_galaxy or 0,
            target_system=f.target_system or 0,
            target_position=f.target_position or 0,
            departed_at=f.departed_at,
            arrives_at=f.arrives_at,
            ship_count=count,
        ))
    return out


# IMPORTANT : /incoming doit être AVANT /{fleet_id} pour éviter le conflit de route
@router.get("/incoming", response_model=list[IncomingFleetResponse])
async def list_incoming_fleets(player: CurrentPlayer, db: DbDep) -> list[IncomingFleetResponse]:
    """
    Retourne les flottes ennemies en approche vers les planètes du joueur.
    Permet au défenseur de voir une attaque arriver et de se préparer.

    Stratégie : cherche les flottes dont target_planet_id appartient au joueur,
    non rappelées, pas encore arrivées.
    """
    from sqlalchemy import text as sql_text

    # Récupérer les IDs des planètes du joueur
    planets_result = await db.execute(
        select(Planet.id).where(Planet.owner_id == player.id)
    )
    my_planet_ids = [row[0] for row in planets_result]

    if not my_planet_ids:
        return []

    # Flottes ennemies qui ciblent mes planètes, pas encore arrivées, pas rappelées
    now = datetime.now(UTC)
    result = await db.execute(
        select(Fleet).where(
            Fleet.target_planet_id.in_(my_planet_ids),
            Fleet.owner_id != player.id,          # flottes ennemies uniquement
            Fleet.is_recalled == False,            # noqa: E712
            Fleet.arrives_at > now,               # pas encore arrivées
        )
    )
    incoming = result.scalars().all()

    out = []
    for f in incoming:
        count_result = await db.execute(
            sql_text("SELECT COUNT(*) FROM fleet_ships WHERE fleet_id = :fid"),
            {"fid": str(f.id)},
        )
        count = count_result.scalar() or 0
        out.append(IncomingFleetResponse(
            fleet_id=f.id,
            mission=f.mission.value if hasattr(f.mission, "value") else f.mission,
            target_galaxy=f.target_galaxy or 0,
            target_system=f.target_system or 0,
            target_position=f.target_position or 0,
            target_planet_id=f.target_planet_id,
            arrives_at=f.arrives_at,
            ship_count=count,
        ))
    return out


@router.post("", response_model=FleetResponse, status_code=status.HTTP_201_CREATED)
async def send_fleet(
    body: SendFleetRequest,
    player: CurrentPlayer,
    db: DbDep,
) -> FleetResponse:
    """
    Envoie une flotte en mission.

    Validations :
    - Tous les vaisseaux appartiennent au joueur
    - Tous sont DOCKED sur la planète d'origine
    - Mission valide
    - Cargo ≤ capacité totale de la flotte

    L'heure d'arrivée est calculée côté serveur.
    """
    await check_rate_limit(str(player.id), "fleets:send")
    # Validation mission
    try:
        mission_enum = FleetMission(body.mission.upper())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Mission invalide : {body.mission!r}. "
                   f"Valeurs : ATTACK, TRANSPORT, ESPIONAGE, COLONIZE",
        )

    if not body.ship_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Aucun vaisseau sélectionné.")

    # Chargement et validation des vaisseaux
    result = await db.execute(
        select(Ship)
        .where(Ship.id.in_(body.ship_ids))
        .with_for_update()
    )
    ships = result.scalars().all()

    if len(ships) != len(body.ship_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Un ou plusieurs vaisseaux introuvables.",
        )

    for ship in ships:
        if ship.owner_id != player.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail=f"Le vaisseau {ship.id} ne vous appartient pas.")
        if ship.status != ShipStatus.DOCKED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Le vaisseau {ship.id} n'est pas amarré (statut: {ship.status.value}).",
            )
        if ship.planet_id != body.origin_planet_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Le vaisseau {ship.id} n'est pas sur la planète d'origine.",
            )

    # Validation cargo
    total_cargo = sum(float(s.base_stats.get("cargo", 0)) for s in ships)
    cargo_used = body.cargo_metal + body.cargo_crystal + body.cargo_deuterium
    if cargo_used > total_cargo:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Cargo demandé ({cargo_used:.0f}) > capacité totale ({total_cargo:.0f}).",
        )

    # Planète origine pour les coordonnées
    origin_result = await db.execute(select(Planet).where(Planet.id == body.origin_planet_id))
    origin: Planet | None = origin_result.scalar_one_or_none()
    if origin is None or origin.owner_id != player.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Planète d'origine introuvable.")

    # Calcul temps de vol
    distance = _compute_distance(
        origin.galaxy, origin.system, origin.position,
        body.target_galaxy, body.target_system, body.target_position,
    )
    speed = _fleet_speed(ships)   # UA/heure
    travel_hours = distance / max(speed, 0.1)

    now = datetime.now(UTC)
    arrives_at = now + timedelta(hours=travel_hours)

    # Trouver la planète cible si elle existe (nullable)
    target_result = await db.execute(
        select(Planet).where(
            Planet.galaxy == body.target_galaxy,
            Planet.system == body.target_system,
            Planet.position == body.target_position,
        )
    )
    target_planet: Planet | None = target_result.scalar_one_or_none()

    # Création de la flotte
    fleet = Fleet(
        id=uuid.uuid4(),
        owner_id=player.id,
        origin_planet_id=body.origin_planet_id,
        target_planet_id=target_planet.id if target_planet else None,
        target_galaxy=body.target_galaxy,
        target_system=body.target_system,
        target_position=body.target_position,
        mission=mission_enum,
        cargo_metal=body.cargo_metal,
        cargo_crystal=body.cargo_crystal,
        cargo_deuterium=body.cargo_deuterium,
        departed_at=now,
        arrives_at=arrives_at,
    )
    db.add(fleet)
    await db.flush()  # Flush obligatoire : écrit la flotte en base AVANT d'insérer
                      # fleet_ships qui a une FK sur fleets.id. Sans flush, PostgreSQL
                      # lève ForeignKeyViolationError car la ligne n'existe pas encore.

    # Mise à jour statut vaisseaux → IN_FLEET
    for ship in ships:
        ship.status = ShipStatus.IN_FLEET
        db.add(ship)

    # Association fleet_ships — INSERT un par un (SQLAlchemy async ne supporte
    # pas executemany via text() — chaque appel doit être une seule ligne)
    for ship in ships:
        await db.execute(
            text("INSERT INTO fleet_ships (fleet_id, ship_id) VALUES (:fid, :sid)"),
            {"fid": str(fleet.id), "sid": str(ship.id)},
        )

    return FleetResponse(
        fleet_id=fleet.id,
        mission=fleet.mission.value if hasattr(fleet.mission, 'value') else fleet.mission,
        origin_planet_id=fleet.origin_planet_id,
        target_galaxy=fleet.target_galaxy,
        target_system=fleet.target_system,
        target_position=fleet.target_position,
        departed_at=fleet.departed_at,
        arrives_at=fleet.arrives_at,
        ship_count=len(ships),
    )


@router.delete("/{fleet_id}", status_code=status.HTTP_204_NO_CONTENT)
async def recall_fleet(
    fleet_id: uuid.UUID,
    player: CurrentPlayer,
    db: DbDep,
) -> Response:
    """
    Rappelle une flotte avant son arrivée.
    Les vaisseaux retournent à DOCKED immédiatement (retour instantané simplifié).
    """
    result = await db.execute(
        select(Fleet).where(Fleet.id == fleet_id).with_for_update()
    )
    fleet: Fleet | None = result.scalar_one_or_none()

    if fleet is None or fleet.owner_id != player.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flotte introuvable.")

    if fleet.is_recalled:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Flotte déjà rappelée.")

    if fleet.arrives_at <= datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La flotte est déjà arrivée — impossible de la rappeler.",
        )

    fleet.is_recalled = True
    db.add(fleet)

    # Remettre les vaisseaux à DOCKED
    ships_result = await db.execute(
        text("SELECT ship_id FROM fleet_ships WHERE fleet_id = :fid"),
        {"fid": str(fleet_id)},
    )
    for row in ships_result:
        ship_r = await db.execute(select(Ship).where(Ship.id == row[0]))
        ship = ship_r.scalar_one_or_none()
        if ship:
            ship.status = ShipStatus.DOCKED
            db.add(ship)

    # Notification WS
    await publish_event(
        channel=f"player:{player.id}",
        event={"type": "fleet.recalled", "data": {"fleet_id": str(fleet_id)}},
    )

    return Response(status_code=204)
