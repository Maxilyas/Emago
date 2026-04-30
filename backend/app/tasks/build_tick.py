"""
app/tasks/build_tick.py
Job APScheduler : finalise les éléments de build_queue dont completes_at <= now().
Fréquence : toutes les 10 secondes.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import and_, select

from app.core.database import AsyncSessionLocal
from app.models.models import BuildQueue, Planet

logger = logging.getLogger(__name__)


async def run_build_tick() -> None:
    """Finalise les constructions dont le timer est écoulé."""
    now = datetime.now(UTC)

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(BuildQueue).where(
                    and_(
                        BuildQueue.completes_at <= now,
                        BuildQueue.completed == False,  # noqa: E712
                    )
                ).order_by(BuildQueue.completes_at)
            )
            items = result.scalars().all()

            for item in items:
                # Charger la planète avec verrou
                planet_result = await db.execute(
                    select(Planet).where(Planet.id == item.planet_id).with_for_update()
                )
                planet: Planet | None = planet_result.scalar_one_or_none()
                if planet is None:
                    item.completed = True
                    item.completed_at = now
                    db.add(item)
                    continue

                # Appliquer le niveau du bâtiment
                buildings = dict(planet.buildings or {})
                if item.item_type == "BUILDING":
                    buildings[item.item_name] = item.target_level or (
                        int(buildings.get(item.item_name, 0)) + 1
                    )
                    planet.buildings = buildings
                    db.add(planet)

                item.completed = True
                item.completed_at = now
                db.add(item)

            await db.commit()

            if items:
                logger.info("build_tick : %d constructions finalisées", len(items))

        except Exception as exc:
            await db.rollback()
            logger.error("build_tick erreur : %s", exc, exc_info=True)
