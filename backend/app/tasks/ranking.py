"""
app/tasks/ranking.py
Job APScheduler : recalcule le score de tous les joueurs.
Fréquence : toutes les 10 minutes.

Score = Σ(niveaux de bâtiments) × 1000
      + Σ(grade des vaisseaux) × 500
      + Σ(XP de combat) × 0.1
"""
from __future__ import annotations

import logging

from sqlalchemy import func, select

from app.core.database import AsyncSessionLocal
from app.models.models import Player, Planet, Ship

logger = logging.getLogger(__name__)


async def run_ranking_recalc() -> None:
    """Recalcule et met à jour le score de tous les joueurs actifs."""
    async with AsyncSessionLocal() as db:
        try:
            players_result = await db.execute(select(Player))
            players = players_result.scalars().all()

            for player in players:
                # Score bâtiments : somme de tous les niveaux
                building_score = 0
                planets_result = await db.execute(
                    select(Planet).where(Planet.owner_id == player.id)
                )
                for planet in planets_result.scalars():
                    buildings = planet.buildings or {}
                    building_score += sum(int(v) for v in buildings.values())

                # Score vaisseaux
                ships_result = await db.execute(
                    select(Ship).where(Ship.owner_id == player.id)
                )
                ship_score = 0
                xp_score = 0
                for ship in ships_result.scalars():
                    ship_score += ship.grade * 500
                    xp_score += int(ship.combat_xp * 0.1)

                player.score = building_score * 1000 + ship_score + xp_score
                db.add(player)

            await db.commit()
            logger.info("ranking_recalc : %d joueurs mis à jour", len(players))

        except Exception as exc:
            await db.rollback()
            logger.error("ranking_recalc erreur : %s", exc, exc_info=True)
