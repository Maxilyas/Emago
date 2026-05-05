"""
app/routers/daily.py
Agent 5 — Backend

Endpoints :
  POST /daily/login          — réclamer la récompense de connexion quotidienne
  GET  /daily/missions        — missions du jour (renouvelées à minuit UTC)
  POST /daily/missions/:id/claim — réclamer une mission accomplie
  GET  /daily/status          — streak + missions + ressources accumulées pendant l'absence

Logique :
  - Streak de connexion stocké dans Player.daily_streak (JSON)
  - Missions générées déterministement depuis la date UTC (seed = date + player_id)
  - Récompenses : métal/cristal/deutérium ajoutés directement sur la planète natale
"""
from __future__ import annotations

import hashlib
import math
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.core.deps import CurrentPlayer, DbDep
from app.models.models import Planet, Player

router = APIRouter(prefix="/daily", tags=["daily"])

# ---------------------------------------------------------------------------
# Récompenses de streak (jour → récompense)
# ---------------------------------------------------------------------------
STREAK_REWARDS: dict[int, dict] = {
    1:  {"metal": 2_000,   "crystal": 500,    "deuterium": 0,      "label": "Jour 1"},
    2:  {"metal": 3_000,   "crystal": 1_000,  "deuterium": 0,      "label": "Jour 2"},
    3:  {"metal": 5_000,   "crystal": 2_000,  "deuterium": 500,    "label": "Jour 3"},
    4:  {"metal": 8_000,   "crystal": 3_000,  "deuterium": 1_000,  "label": "Jour 4"},
    5:  {"metal": 12_000,  "crystal": 5_000,  "deuterium": 2_000,  "label": "Jour 5"},
    6:  {"metal": 20_000,  "crystal": 8_000,  "deuterium": 3_000,  "label": "Jour 6"},
    7:  {"metal": 30_000,  "crystal": 12_000, "deuterium": 5_000,  "label": "Semaine complète ! 🎉"},
}
MAX_STREAK_DAY = 7  # boucle sur 7 jours

# ---------------------------------------------------------------------------
# Pool de missions journalières
# ---------------------------------------------------------------------------
MISSION_POOL = [
    {"id": "build_ship",       "label": "Construire un vaisseau",          "desc": "Fabriquez n'importe quel vaisseau",                  "target": 1,  "reward": {"metal": 3_000,  "crystal": 1_000}},
    {"id": "collect_metal",    "label": "Collecter du métal",              "desc": "Avoir 10 000 métal sur une planète",                  "target": 1,  "reward": {"metal": 5_000}},
    {"id": "upgrade_building", "label": "Améliorer un bâtiment",          "desc": "Améliorez n'importe quel bâtiment",                   "target": 1,  "reward": {"crystal": 3_000}},
    {"id": "send_fleet",       "label": "Envoyer une flotte",              "desc": "Envoyez une flotte en mission",                       "target": 1,  "reward": {"metal": 2_000,  "deuterium": 1_000}},
    {"id": "install_module",   "label": "Installer un module",             "desc": "Installez un module sur un vaisseau",                 "target": 1,  "reward": {"crystal": 2_000}},
    {"id": "check_galaxy",     "label": "Explorer la galaxie",            "desc": "Visitez la carte galactique",                         "target": 1,  "reward": {"metal": 1_000,  "crystal": 500}},
    {"id": "have_3_ships",     "label": "Escadron de 3",                  "desc": "Avoir 3 vaisseaux dans votre hangar",                 "target": 3,  "reward": {"metal": 4_000}},
    {"id": "forge_active",     "label": "Lancer la forge",                "desc": "Démarrez une opération de forge",                     "target": 1,  "reward": {"crystal": 5_000, "deuterium": 2_000}},
]

def _get_daily_missions(player_id: uuid.UUID, today: date) -> list[dict]:
    """
    Génère 3 missions déterministes pour la journée.
    Seed = SHA256(player_id + date) → garantit que les missions sont
    les mêmes pour un joueur pendant toute la journée.
    """
    seed_str = f"{player_id}{today.isoformat()}"
    seed_hash = int(hashlib.sha256(seed_str.encode()).hexdigest(), 16)

    indices = []
    pool_size = len(MISSION_POOL)
    i = 0
    while len(indices) < 3:
        idx = (seed_hash + i * 7919) % pool_size  # 7919 = nombre premier
        if idx not in indices:
            indices.append(idx)
        i += 1

    return [MISSION_POOL[idx] for idx in indices]


# ---------------------------------------------------------------------------
# Helpers BDD
# ---------------------------------------------------------------------------

def _get_player_daily_data(player: Player) -> dict:
    """Lit les données daily depuis le champ JSON du joueur."""
    # On stocke dans un champ JSON qu'on ajoute au modèle Player
    # Si pas encore de champ, utiliser un dict vide par défaut
    return getattr(player, 'daily_data', None) or {}


def _today_str() -> str:
    return date.today().isoformat()


def _reward_resources(reward: dict) -> dict[str, int]:
    """Extrait uniquement les champs numériques (ressources) d'une entrée STREAK_REWARDS.
    Exclut 'label' et tout autre champ non-int pour satisfaire dict[str, int]."""
    return {k: v for k, v in reward.items() if isinstance(v, int)}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class DailyLoginResponse(BaseModel):
    streak: int
    streak_label: str                    # ex: "Jour 1", "Semaine complète ! 🎉"
    reward: dict[str, int]               # uniquement metal/crystal/deuterium
    next_reward: dict[str, int] | None
    already_claimed: bool
    message: str


class MissionOut(BaseModel):
    id: str
    label: str
    desc: str
    target: int
    progress: int
    completed: bool
    claimed: bool
    reward: dict[str, int]


class DailyStatusResponse(BaseModel):
    streak: int
    last_login: str | None
    can_claim_login: bool
    missions: list[MissionOut]
    offline_gains: dict[str, float] | None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/status", response_model=DailyStatusResponse)
async def get_daily_status(player: CurrentPlayer, db: DbDep) -> DailyStatusResponse:
    """Retourne le statut daily complet du joueur."""
    daily = _get_player_daily_data(player)
    today = _today_str()
    last_login = daily.get("last_login_date")
    streak = daily.get("streak", 0)
    can_claim = last_login != today

    # Missions du jour
    missions_raw = _get_daily_missions(player.id, date.today())
    claimed_missions = daily.get("claimed_missions", {})
    progress_data = daily.get("mission_progress", {})
    if daily.get("missions_date") != today:
        # Reset des missions si nouveau jour
        claimed_missions = {}
        progress_data = {}

    missions_out = []
    for m in missions_raw:
        prog = progress_data.get(m["id"], 0)
        completed = prog >= m["target"]
        missions_out.append(MissionOut(
            id=m["id"],
            label=m["label"],
            desc=m["desc"],
            target=m["target"],
            progress=min(prog, m["target"]),
            completed=completed,
            claimed=claimed_missions.get(m["id"], False),
            reward=m["reward"],
        ))

    # Gains hors-ligne
    offline_gains = None
    if last_login and last_login != today:
        offline_gains = daily.get("offline_preview")

    return DailyStatusResponse(
        streak=streak,
        last_login=last_login,
        can_claim_login=can_claim,
        missions=missions_out,
        offline_gains=offline_gains,
    )


@router.post("/login", response_model=DailyLoginResponse)
async def claim_daily_login(player: CurrentPlayer, db: DbDep) -> DailyLoginResponse:
    """Réclame la récompense de connexion quotidienne."""
    # Locker le joueur pour éviter le double-claim concurrent
    r_player = await db.execute(select(Player).where(Player.id == player.id).with_for_update())
    locked_player = r_player.scalar_one()

    daily = dict(_get_player_daily_data(locked_player))
    today = _today_str()
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    last_login = daily.get("last_login_date")

    # Déjà réclamé aujourd'hui
    if last_login == today:
        streak = daily.get("streak", 1)
        day = ((streak - 1) % MAX_STREAK_DAY) + 1
        next_day = (day % MAX_STREAK_DAY) + 1
        return DailyLoginResponse(
            streak=streak,
            streak_label=STREAK_REWARDS[day]["label"],
            reward=_reward_resources(STREAK_REWARDS[day]),
            next_reward=_reward_resources(STREAK_REWARDS[next_day]),
            already_claimed=True,
            message="Récompense déjà réclamée aujourd'hui.",
        )

    # Calculer le streak
    if last_login == yesterday:
        streak = daily.get("streak", 0) + 1
    else:
        streak = 1  # Reset si jour manqué

    day = ((streak - 1) % MAX_STREAK_DAY) + 1
    reward = STREAK_REWARDS[day]

    # Chercher la planète natale pour ajouter les ressources
    result = await db.execute(
        select(Planet).where(
            Planet.owner_id == locked_player.id,
            Planet.is_homeworld == True,  # noqa: E712
        ).with_for_update()
    )
    homeworld: Planet | None = result.scalar_one_or_none()
    if homeworld:
        homeworld.metal     = min(float(homeworld.metal_capacity),     float(homeworld.metal)     + reward.get("metal", 0))
        homeworld.crystal   = min(float(homeworld.crystal_capacity),   float(homeworld.crystal)   + reward.get("crystal", 0))
        homeworld.deuterium = min(float(homeworld.deut_capacity),      float(homeworld.deuterium) + reward.get("deuterium", 0))
        db.add(homeworld)

    # Mettre à jour daily_data du joueur
    daily["last_login_date"] = today
    daily["streak"] = streak
    # SQLAlchemy JSONB — on doit réaffecter l'attribut
    if hasattr(locked_player, 'daily_data'):
        locked_player.daily_data = daily
        db.add(locked_player)

    next_day = (day % MAX_STREAK_DAY) + 1
    return DailyLoginResponse(
        streak=streak,
        streak_label=reward["label"],
        reward=_reward_resources(reward),
        next_reward=_reward_resources(STREAK_REWARDS[next_day]),
        already_claimed=False,
        message=f"{'🎉 ' if day == 7 else ''}Récompense du jour {day} réclamée !",
    )


@router.post("/missions/{mission_id}/claim")
async def claim_mission(mission_id: str, player: CurrentPlayer, db: DbDep) -> dict:
    """Réclame la récompense d'une mission accomplie."""
    daily = dict(_get_player_daily_data(player))
    today = _today_str()

    missions_raw = _get_daily_missions(player.id, date.today())
    mission = next((m for m in missions_raw if m["id"] == mission_id), None)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission introuvable.")

    claimed_missions = daily.get("claimed_missions", {}) if daily.get("missions_date") == today else {}
    if claimed_missions.get(mission_id):
        raise HTTPException(status_code=409, detail="Mission déjà réclamée.")

    progress_data = daily.get("mission_progress", {}) if daily.get("missions_date") == today else {}
    progress = progress_data.get(mission_id, 0)
    if progress < mission["target"]:
        raise HTTPException(status_code=402, detail="Mission non complétée.")

    # Ajouter récompense sur planète natale
    reward = mission["reward"]
    result = await db.execute(
        select(Planet).where(Planet.owner_id == player.id, Planet.is_homeworld == True)  # noqa: E712
    )
    homeworld: Planet | None = result.scalar_one_or_none()
    if homeworld:
        homeworld.metal     = min(float(homeworld.metal_capacity),   float(homeworld.metal)     + reward.get("metal", 0))
        homeworld.crystal   = min(float(homeworld.crystal_capacity), float(homeworld.crystal)   + reward.get("crystal", 0))
        homeworld.deuterium = min(float(homeworld.deut_capacity),    float(homeworld.deuterium) + reward.get("deuterium", 0))
        db.add(homeworld)

    claimed_missions[mission_id] = True
    daily["claimed_missions"] = claimed_missions
    daily["missions_date"] = today
    if hasattr(player, 'daily_data'):
        player.daily_data = daily
        db.add(player)

    return {"claimed": True, "reward": reward, "message": f"Mission accomplie ! +{reward}"}


@router.post("/missions/{mission_id}/progress")
async def update_mission_progress(
    mission_id: str,
    increment: int = 1,
    player: CurrentPlayer = None,
    db: DbDep = None,
) -> dict:
    """Met à jour la progression d'une mission (appelé par les autres routers)."""
    daily = dict(_get_player_daily_data(player))
    today = _today_str()

    if daily.get("missions_date") != today:
        daily["mission_progress"] = {}
        daily["claimed_missions"] = {}
        daily["missions_date"] = today

    progress = daily.get("mission_progress", {})
    progress[mission_id] = progress.get(mission_id, 0) + increment
    daily["mission_progress"] = progress

    if hasattr(player, 'daily_data'):
        player.daily_data = daily
        db.add(player)

    return {"progress": progress[mission_id]}
