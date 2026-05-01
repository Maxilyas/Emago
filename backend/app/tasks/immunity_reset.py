"""
app/tasks/immunity_reset.py
Agent 5 — Développeur Backend

Responsabilité : Réinitialisation de l'immunité Grade 4 toutes les 48h.

GDD §4 — Grade 4 : "Immunité à la première destruction. Elle se réinitialise
après 48h de non-combat." Le champ grade4_immunity_active passe à False
quand grade4_immunity_reset_at <= now().

Ce job est enregistré dans main.py au lifespan avec interval=minutes=5.
Vérification fréquente légère (requête indexée sur timestamp).

Dépendance critique :
  - Ship.grade4_immunity_active   : bool — drapeau lu par combat_engine
  - Ship.grade4_immunity_reset_at : timestamptz — heure de réactivation
  - Ces deux champs doivent être updatés par combat_engine quand l'immunité
    est consommée (hull == 0 → survie à 1 HP → immunity_used = True).
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import and_, select

from app.core.database import AsyncSessionLocal
from app.models.models import Ship
from app.services.ship_stats_service import invalidate_ship_cache

logger = logging.getLogger(__name__)


async def run_immunity_reset() -> None:
    """
    Réactive l'immunité Grade 4 pour tous les vaisseaux dont
    grade4_immunity_reset_at est passé et grade4_immunity_active == False.

    Fréquence recommandée : toutes les 5 minutes (suffisant pour une
    précision de ±5min sur une fenêtre de 48h).
    """
    now = datetime.now(UTC)

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(Ship).where(
                    and_(
                        Ship.grade4_immunity_active == False,   # noqa: E712
                        Ship.grade == 4,
                        Ship.grade4_immunity_reset_at != None,   # noqa: E711
                        Ship.grade4_immunity_reset_at <= now,
                    )
                )
            )
            ships_to_reset = result.scalars().all()

            if not ships_to_reset:
                return

            for ship in ships_to_reset:
                ship.grade4_immunity_active = True
                ship.grade4_immunity_reset_at = None
                db.add(ship)
                # Invalider le cache Redis — current_stats inclut l'état de l'immunité
                await invalidate_ship_cache(ship.id)

            await db.commit()
            logger.info(
                "Immunité Grade 4 réactivée : %d vaisseau(x)", len(ships_to_reset)
            )

        except Exception as exc:
            await db.rollback()
            logger.error("Erreur immunity_reset : %s", exc, exc_info=True)


# ---------------------------------------------------------------------------
# Enregistrement dans main.py — ajouter dans _register_jobs() :
#
#   from app.tasks.immunity_reset import run_immunity_reset
#   scheduler.add_job(
#       run_immunity_reset,
#       "interval",
#       minutes=5,
#       id="immunity_reset",
#       max_instances=1,
#       coalesce=True,
#   )
# ---------------------------------------------------------------------------
