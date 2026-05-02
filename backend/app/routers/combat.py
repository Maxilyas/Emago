"""
app/routers/combat.py — v3
Agent 5 — Développeur Backend

Fix : route /history déclarée AVANT /{combat_id} pour éviter que FastAPI
ne tente de parser "history" comme un UUID (422 Unprocessable Entity).

GET /combat/history  — historique des combats du joueur (50 derniers)
GET /combat/{id}     — rapport complet d'un combat (Redis → BDD)
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import or_, select

from app.core.deps import CurrentPlayer, DbDep
from app.core.redis_client import get_redis
from app.models.models import CombatLog  # noqa: E402

router = APIRouter(prefix="/combat", tags=["combat"])

_COMBAT_CACHE_TTL = 600  # 10 minutes


# ─── Schemas ─────────────────────────────────────────────────────────────────

class CombatSummary(BaseModel):
    """Résumé léger pour la liste historique."""
    combat_id: uuid.UUID
    outcome: str
    fought_at: datetime
    attacker_power: float
    defender_power: float
    total_rounds: int


class CombatReportResponse(BaseModel):
    """Rapport complet avec snapshots et log des rounds."""
    combat_id: uuid.UUID
    outcome: str
    fought_at: datetime
    attacker_power: float
    defender_power: float
    pillaged_metal: float
    pillaged_crystal: float
    pillaged_deuterium: float
    total_rounds: int
    rounds_log: list[dict[str, Any]]
    attacker_ships_snapshot: list[dict[str, Any]]
    defender_ships_snapshot: list[dict[str, Any]]


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _is_participant(log: CombatLog, player_id: uuid.UUID) -> bool:
    """
    Vérifie que le joueur est attaquant ou défenseur dans ce combat.
    La participation est détectée via owner_id dans les snapshots de vaisseaux.
    """
    player_id_str = str(player_id)
    all_snaps = [
        *(log.attacker_ships_snapshot or []),
        *(log.defender_ships_snapshot or []),
    ]
    for snap in all_snaps:
        if isinstance(snap, dict) and str(snap.get("owner_id", "")) == player_id_str:
            return True
    return False


# ─── Endpoints ───────────────────────────────────────────────────────────────

# CRITIQUE : /history DOIT être déclaré avant /{combat_id}
# Sinon FastAPI tente de parser "history" comme un UUID → 422

@router.get("/history", response_model=list[CombatSummary])
async def get_combat_history(
    player: CurrentPlayer,
    db: DbDep,
    limit: int = 50,
) -> list[CombatSummary]:
    """
    Retourne les 50 derniers combats où le joueur a participé.

    Stratégie de participation : le player_id est cherché dans
    attacker_ships_snapshot et defender_ships_snapshot (JSONB).
    Utilise un filtre PostgreSQL JSONB pour efficacité.
    """
    # Filtre PostgreSQL JSONB @> : cherche {"owner_id": "..."} dans les snapshots.
    # Évite le chargement de tous les combats en mémoire + filtrage Python.
    result = await db.execute(
        select(CombatLog)
        .where(
            or_(
                CombatLog.attacker_ships_snapshot.contains([{"owner_id": str(player.id)}]),
                CombatLog.defender_ships_snapshot.contains([{"owner_id": str(player.id)}]),
            )
        )
        .order_by(CombatLog.fought_at.desc())
        .limit(min(limit, 100))
    )
    participant_logs = result.scalars().all()

    return [
        CombatSummary(
            combat_id=log.id,
            outcome=log.outcome,
            fought_at=log.fought_at,
            attacker_power=float(log.attacker_power),
            defender_power=float(log.defender_power),
            total_rounds=len(log.rounds_log) if log.rounds_log else 0,
        )
        for log in participant_logs
    ]


@router.get("/{combat_id}", response_model=CombatReportResponse)
async def get_combat_report(
    combat_id: uuid.UUID,
    player: CurrentPlayer,
    db: DbDep,
) -> CombatReportResponse:
    """
    Retourne le rapport complet d'un combat.
    Le joueur doit être participant (403 sinon).
    Retourne depuis Redis si le cache est chaud, sinon depuis PostgreSQL.
    """
    # 1. Cache Redis
    r = get_redis()
    cache_key = f"combat:{combat_id}:result"
    cached = await r.get(cache_key)
    if cached:
        data = json.loads(cached)
        # Vérifier participation même sur cache
        snaps = [
            *(data.get("attacker_ships_snapshot") or []),
            *(data.get("defender_ships_snapshot") or []),
        ]
        player_id_str = str(player.id)
        if not any(str(s.get("owner_id", "")) == player_id_str for s in snaps if isinstance(s, dict)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous n'êtes pas participant de ce combat.",
            )
        return CombatReportResponse(**data)

    # 2. BDD
    result = await db.execute(
        select(CombatLog).where(CombatLog.id == combat_id)
    )
    log: CombatLog | None = result.scalar_one_or_none()

    if log is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Combat introuvable.")

    # Vérification participation
    if not _is_participant(log, player.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'êtes pas participant de ce combat.",
        )

    total_rounds = len(log.rounds_log) if log.rounds_log else 0

    report = CombatReportResponse(
        combat_id=log.id,
        outcome=log.outcome,
        fought_at=log.fought_at,
        attacker_power=float(log.attacker_power),
        defender_power=float(log.defender_power),
        pillaged_metal=float(log.pillaged_metal),
        pillaged_crystal=float(log.pillaged_crystal),
        pillaged_deuterium=float(log.pillaged_deuterium),
        total_rounds=total_rounds,
        rounds_log=log.rounds_log or [],
        attacker_ships_snapshot=log.attacker_ships_snapshot or [],
        defender_ships_snapshot=log.defender_ships_snapshot or [],
    )

    # Mise en cache Redis
    await r.setex(cache_key, _COMBAT_CACHE_TTL, report.model_dump_json())

    return report
