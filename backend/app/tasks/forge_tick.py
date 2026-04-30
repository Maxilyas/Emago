"""
app/tasks/forge_tick.py
Job APScheduler : vérifie les forges terminées et les finalise.
Fréquence : toutes les 60 secondes (configuré dans main.py).
"""
from __future__ import annotations

import logging

from app.core.database import AsyncSessionLocal
from app.services.forge_service import run_forge_tick

logger = logging.getLogger(__name__)


async def run_forge_tick_job() -> None:
    """
    Point d'entrée du job APScheduler.
    Ouvre une session BDD et délègue à forge_service.run_forge_tick().
    """
    async with AsyncSessionLocal() as db:
        try:
            await run_forge_tick(db)
        except Exception as exc:
            logger.error("forge_tick erreur globale : %s", exc, exc_info=True)
