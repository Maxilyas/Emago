"""
app/routers/ranking.py
GET /ranking — classement global des joueurs
GET /ranking/me — position du joueur courant dans le classement
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import func, select

from app.core.deps import CurrentPlayer, DbDep
from app.models.models import Player

router = APIRouter(prefix="/ranking", tags=["ranking"])


class RankingEntry(BaseModel):
    rank: int
    player_id: str
    username: str
    score: int
    alliance_tag: str | None


class PlayerRankResponse(BaseModel):
    rank: int
    player_id: str
    username: str
    score: int


@router.get("", response_model=list[RankingEntry])
async def get_ranking(db: DbDep, limit: int = 100) -> list[RankingEntry]:
    """
    Retourne le top {limit} des joueurs triés par score décroissant.
    Le score est recalculé périodiquement par le scheduler (toutes les 10 min).
    Endpoint public — pas d'authentification requise.
    """
    result = await db.execute(
        select(Player)
        .order_by(Player.score.desc())
        .limit(min(limit, 500))
    )
    players = result.scalars().all()

    return [
        RankingEntry(
            rank=i + 1,
            player_id=str(p.id),
            username=p.username,
            score=p.score,
            alliance_tag=None,  # TODO : charger depuis alliance relation
        )
        for i, p in enumerate(players)
    ]


@router.get("/me", response_model=PlayerRankResponse)
async def get_my_rank(player: CurrentPlayer, db: DbDep) -> PlayerRankResponse:
    """Retourne le rang du joueur courant dans le classement global."""
    # Compte les joueurs avec un score supérieur
    count_result = await db.execute(
        select(func.count(Player.id)).where(Player.score > player.score)
    )
    players_above = count_result.scalar() or 0
    rank = players_above + 1

    return PlayerRankResponse(
        rank=rank,
        player_id=str(player.id),
        username=player.username,
        score=player.score,
    )
