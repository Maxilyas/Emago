"""
app/tasks/resource_tick.py
Job APScheduler : calcule la production de ressources de toutes les planètes actives.
Fréquence : toutes les 60 secondes.

Stratégie : on ne parcourt que les planètes avec un propriétaire actif.
Le calcul lazy (à l'accès) reste la source de vérité — ce tick garantit
que les planètes non visitées restent à jour en BDD pour les calculs de classement.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.models import Planet, Player

logger = logging.getLogger(__name__)

# Constantes de production (horaire, niveau × 1.1^niveau)
_BASE_METAL_RATE = 30.0
_BASE_CRYSTAL_RATE = 15.0
_BASE_DEUT_RATE = 5.0


def _mine_output(base: float, level: int) -> float:
    """Production horaire : base × level × 1.1^level."""
    if level <= 0:
        return 0.0
    return base * level * (1.1 ** level)


def _get_building_level(buildings: dict, key: str) -> int:
    return int(buildings.get(key, 0))


async def run_resource_tick() -> None:
    """Calcule et applique la production depuis le dernier tick."""
    now = datetime.now(UTC)

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(Planet).where(Planet.owner_id.is_not(None))
            )
            planets = result.scalars().all()

            for planet in planets:
                elapsed_hours = (
                    now - planet.resources_last_updated_at.replace(tzinfo=UTC)
                ).total_seconds() / 3600

                if elapsed_hours < 0.001:  # moins de 3.6s — skip
                    continue

                b = planet.buildings or {}
                metal_level   = _get_building_level(b, "metal_mine")
                crystal_level = _get_building_level(b, "crystal_mine")
                deut_level    = _get_building_level(b, "deuterium_synthesizer")
                solar_level   = _get_building_level(b, "solar_plant")

                energy_prod = _mine_output(20.0, solar_level)
                energy_need = (
                    _mine_output(1.0, metal_level) * 10
                    + _mine_output(1.0, crystal_level) * 10
                    + _mine_output(1.0, deut_level) * 20
                )
                factor = min(1.0, energy_prod / energy_need) if energy_need > 0 else 1.0

                gained_metal   = _mine_output(_BASE_METAL_RATE, metal_level) * elapsed_hours * factor
                gained_crystal = _mine_output(_BASE_CRYSTAL_RATE, crystal_level) * elapsed_hours * factor
                gained_deut    = _mine_output(_BASE_DEUT_RATE, deut_level) * elapsed_hours * factor

                planet.metal    = min(float(planet.metal_capacity),   float(planet.metal)    + gained_metal)
                planet.crystal  = min(float(planet.crystal_capacity), float(planet.crystal)  + gained_crystal)
                planet.deuterium = min(float(planet.deut_capacity),   float(planet.deuterium) + gained_deut)
                planet.resources_last_updated_at = now
                db.add(planet)

            await db.commit()
            logger.debug("resource_tick : %d planètes mises à jour", len(planets))

        except Exception as exc:
            await db.rollback()
            logger.error("resource_tick erreur : %s", exc, exc_info=True)
