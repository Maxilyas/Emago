"""
app/tasks/fleet_arrival.py
Job APScheduler : traite les flottes dont arrives_at <= now().
Fréquence : toutes les 5 secondes.

Pour chaque flotte arrivée :
  - ATTACK   → appelle combat_engine.resolve_combat()
  - TRANSPORT → dépose le cargo sur la planète cible
  - ESPIONAGE → rapport d'espionnage (stub — Agent 5 phase 2)
  - COLONIZE  → crée une nouvelle planète (stub)
  - RECALL    → retourne la flotte à l'origine

La logique de combat est déléguée à combat_engine.
Ce tick est uniquement le déclencheur temporel.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import and_, select

from app.core.database import AsyncSessionLocal
from app.core.redis_client import publish_event
from app.models.models import Fleet, FleetMission, Planet, Ship

logger = logging.getLogger(__name__)


async def run_fleet_arrivals() -> None:
    """Traite toutes les flottes dont l'heure d'arrivée est passée."""
    now = datetime.now(UTC)

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(Fleet).where(
                    and_(
                        Fleet.arrives_at <= now,
                        Fleet.is_recalled == False,  # noqa: E712
                    )
                )
            )
            fleets = result.scalars().all()

            for fleet in fleets:
                try:
                    await _process_fleet_arrival(fleet, db, now)
                except Exception as exc:
                    logger.error(
                        "fleet_arrival erreur fleet=%s : %s", fleet.id, exc, exc_info=True
                    )

            if fleets:
                await db.commit()
                logger.info("fleet_arrival : %d flottes traitées", len(fleets))

        except Exception as exc:
            await db.rollback()
            logger.error("fleet_arrival erreur globale : %s", exc, exc_info=True)


async def _process_fleet_arrival(fleet: Fleet, db, now: datetime) -> None:
    """Dispatch selon la mission de la flotte."""

    if fleet.mission == FleetMission.ATTACK:
        await _handle_attack(fleet, db)

    elif fleet.mission == FleetMission.TRANSPORT:
        await _handle_transport(fleet, db)

    elif fleet.mission in (FleetMission.ESPIONAGE, FleetMission.COLONIZE):
        # Stub — implémentation phase 2
        logger.info("Mission %s fleet=%s : non implémentée", fleet.mission, fleet.id)
        fleet.is_recalled = True
        db.add(fleet)

    elif fleet.mission == FleetMission.RECALL:
        fleet.is_recalled = True
        db.add(fleet)

    # Notification WS au propriétaire
    await publish_event(
        channel=f"player:{fleet.owner_id}",
        event={
            "type": "fleet.arrived",
            "data": {
                "fleet_id": str(fleet.id),
                "mission":  fleet.mission.value,
                "target_planet_id": str(fleet.target_planet_id) if fleet.target_planet_id else None,
            },
        },
    )


async def _handle_attack(fleet: Fleet, db) -> None:
    """Déclenche un combat. Délègue à combat_engine."""
    from app.services.combat_engine import resolve_combat

    if fleet.target_planet_id is None:
        logger.warning("Flotte ATTACK sans target_planet_id : %s", fleet.id)
        fleet.is_recalled = True
        db.add(fleet)
        return

    # Vaisseaux de la flotte attaquante (via table fleet_ships)
    from sqlalchemy import text
    ships_result = await db.execute(
        text("SELECT ship_id FROM fleet_ships WHERE fleet_id = :fid"),
        {"fid": str(fleet.id)},
    )
    attacker_ship_ids = [row[0] for row in ships_result]

    if not attacker_ship_ids:
        fleet.is_recalled = True
        db.add(fleet)
        return

    # Vaisseaux défenseurs (DOCKED sur la planète cible)
    defender_result = await db.execute(
        select(Ship).where(
            Ship.planet_id == fleet.target_planet_id,
            Ship.status == "DOCKED",
        )
    )
    defender_ships = defender_result.scalars().all()
    defender_ship_ids = [s.id for s in defender_ships]

    if not defender_ship_ids:
        # Pas de défense → victoire automatique, pas de combat
        logger.info("Flotte %s : aucun défenseur, victoire automatique", fleet.id)
        fleet.is_recalled = True
        db.add(fleet)
        return

    await resolve_combat(
        db=db,
        attacker_fleet_id=fleet.id,
        defender_planet_id=fleet.target_planet_id,
        attacker_ship_ids=attacker_ship_ids,
        defender_ship_ids=defender_ship_ids,
    )

    fleet.is_recalled = True
    db.add(fleet)


async def _handle_transport(fleet: Fleet, db) -> None:
    """Dépose le cargo sur la planète cible."""
    if fleet.target_planet_id is None:
        fleet.is_recalled = True
        db.add(fleet)
        return

    planet_result = await db.execute(
        select(Planet).where(Planet.id == fleet.target_planet_id).with_for_update()
    )
    planet: Planet | None = planet_result.scalar_one_or_none()

    if planet:
        planet.metal    = min(float(planet.metal_capacity),   float(planet.metal)    + float(fleet.cargo_metal))
        planet.crystal  = min(float(planet.crystal_capacity), float(planet.crystal)  + float(fleet.cargo_crystal))
        planet.deuterium = min(float(planet.deut_capacity),   float(planet.deuterium) + float(fleet.cargo_deuterium))
        db.add(planet)

    fleet.cargo_metal     = 0
    fleet.cargo_crystal   = 0
    fleet.cargo_deuterium = 0
    fleet.is_recalled     = True
    db.add(fleet)
