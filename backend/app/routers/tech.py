"""
app/routers/tech.py
Agent 5 — Backend

Arbre technologique par classe de vaisseau.
Chaque tech est spécifique à une classe (ATTACK, DEFENSE, SUPPORT, EXPLORATION).
Les bonus sont permanents et s'appliquent à tous les vaisseaux de cette classe.

GET  /tech/tree        — arbre complet avec état de recherche
POST /tech/research    — lancer une recherche
"""
from __future__ import annotations

import uuid
import math
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from app.core.deps import CurrentPlayer, DbDep
from app.models.models import Planet, Player, ResearchQueue

router = APIRouter(prefix="/tech", tags=["tech"])

# ---------------------------------------------------------------------------
# Arbre technologique — GDD Agent 2
# ---------------------------------------------------------------------------
# Chaque tech a : id, classe, nom, description, max_level, bonus par niveau,
#                prérequis (autre tech + niveau requis), coût de recherche
# ---------------------------------------------------------------------------

TECH_TREE: dict[str, dict] = {
    # ── ATTAQUE ──────────────────────────────────────────────────────────────
    "att_weapons_1": {
        "class": "ATTACK", "label": "Armement Tier I",
        "desc": "Améliore les systèmes d'armement des vaisseaux d'attaque.",
        "max_level": 5, "per_level_bonus": {"dps": 0.05},  # +5% DPS par niveau
        "requires": [],
        "costs": [
            {"metal": 2000,  "crystal": 1000, "deuterium": 0,   "hours": 0.5},
            {"metal": 4000,  "crystal": 2000, "deuterium": 500,  "hours": 1},
            {"metal": 8000,  "crystal": 4000, "deuterium": 1000, "hours": 2},
            {"metal": 16000, "crystal": 8000, "deuterium": 2000, "hours": 4},
            {"metal": 32000, "crystal": 16000,"deuterium": 4000, "hours": 8},
        ],
        "icon": "🗡️",
    },
    "att_weapons_2": {
        "class": "ATTACK", "label": "Armement Tier II",
        "desc": "Canons haute cadence — DPS accru et portée améliorée.",
        "max_level": 3, "per_level_bonus": {"dps": 0.10},  # +10% DPS
        "requires": [{"tech_id": "att_weapons_1", "level": 3}],
        "costs": [
            {"metal": 20000, "crystal": 10000, "deuterium": 3000, "hours": 4},
            {"metal": 40000, "crystal": 20000, "deuterium": 6000, "hours": 8},
            {"metal": 80000, "crystal": 40000, "deuterium": 12000,"hours": 16},
        ],
        "icon": "⚡",
    },
    "att_speed": {
        "class": "ATTACK", "label": "Propulsion Tactique",
        "desc": "Les frégates d'attaque gagnent en manœuvrabilité.",
        "max_level": 4, "per_level_bonus": {"speed": 0.08},
        "requires": [{"tech_id": "att_weapons_1", "level": 1}],
        "costs": [
            {"metal": 3000,  "crystal": 1500, "deuterium": 500,  "hours": 1},
            {"metal": 6000,  "crystal": 3000, "deuterium": 1000, "hours": 2},
            {"metal": 12000, "crystal": 6000, "deuterium": 2000, "hours": 4},
            {"metal": 24000, "crystal": 12000,"deuterium": 4000, "hours": 8},
        ],
        "icon": "🚀",
    },
    "att_rng_boost": {
        "class": "ATTACK", "label": "Protocoles de Fabrication Offensifs",
        "desc": "Les vaisseaux d'attaque sortent du chantier avec de meilleures stats RNG.",
        "max_level": 3, "per_level_bonus": {"rng_floor": 0.05},  # Plancher RNG +5%
        "requires": [{"tech_id": "att_weapons_2", "level": 1}],
        "costs": [
            {"metal": 30000, "crystal": 15000, "deuterium": 5000, "hours": 6},
            {"metal": 60000, "crystal": 30000, "deuterium": 10000,"hours": 12},
            {"metal": 120000,"crystal": 60000, "deuterium": 20000,"hours": 24},
        ],
        "icon": "🎯",
    },

    # ── DÉFENSE ──────────────────────────────────────────────────────────────
    "def_armor": {
        "class": "DEFENSE", "label": "Blindage Renforcé",
        "desc": "Les vaisseaux de défense absorbent plus de dommages.",
        "max_level": 5, "per_level_bonus": {"hull": 0.07},
        "requires": [],
        "costs": [
            {"metal": 3000,  "crystal": 500,  "deuterium": 0,   "hours": 0.5},
            {"metal": 6000,  "crystal": 1000, "deuterium": 0,   "hours": 1},
            {"metal": 12000, "crystal": 2000, "deuterium": 500, "hours": 2},
            {"metal": 24000, "crystal": 4000, "deuterium": 1000,"hours": 4},
            {"metal": 48000, "crystal": 8000, "deuterium": 2000,"hours": 8},
        ],
        "icon": "🛡️",
    },
    "def_shields": {
        "class": "DEFENSE", "label": "Générateurs de Boucliers",
        "desc": "Boucliers améliorés sur tous les vaisseaux de défense.",
        "max_level": 4, "per_level_bonus": {"shield": 0.10},
        "requires": [{"tech_id": "def_armor", "level": 2}],
        "costs": [
            {"metal": 5000,  "crystal": 3000, "deuterium": 500,  "hours": 1},
            {"metal": 10000, "crystal": 6000, "deuterium": 1000, "hours": 2},
            {"metal": 20000, "crystal": 12000,"deuterium": 2000, "hours": 4},
            {"metal": 40000, "crystal": 24000,"deuterium": 4000, "hours": 8},
        ],
        "icon": "🔋",
    },
    "def_regen": {
        "class": "DEFENSE", "label": "Systèmes d'Auto-Réparation",
        "desc": "Les vaisseaux de défense récupèrent de la coque entre les combats.",
        "max_level": 3, "per_level_bonus": {"shield_regen": 0.01},
        "requires": [{"tech_id": "def_shields", "level": 2}],
        "costs": [
            {"metal": 25000, "crystal": 15000, "deuterium": 5000, "hours": 6},
            {"metal": 50000, "crystal": 30000, "deuterium": 10000,"hours": 12},
            {"metal": 100000,"crystal": 60000, "deuterium": 20000,"hours": 24},
        ],
        "icon": "💊",
    },

    # ── SOUTIEN ──────────────────────────────────────────────────────────────
    "sup_aura": {
        "class": "SUPPORT", "label": "Amplificateurs d'Aura",
        "desc": "L'aura de soutien des vaisseaux est plus puissante.",
        "max_level": 5, "per_level_bonus": {"support_aura": 0.05},
        "requires": [],
        "costs": [
            {"metal": 1500,  "crystal": 2000, "deuterium": 0,    "hours": 0.5},
            {"metal": 3000,  "crystal": 4000, "deuterium": 500,  "hours": 1},
            {"metal": 6000,  "crystal": 8000, "deuterium": 1000, "hours": 2},
            {"metal": 12000, "crystal": 16000,"deuterium": 2000, "hours": 4},
            {"metal": 24000, "crystal": 32000,"deuterium": 4000, "hours": 8},
        ],
        "icon": "📡",
    },
    "sup_repair": {
        "class": "SUPPORT", "label": "Nanobots de Réparation",
        "desc": "Les vaisseaux de soutien peuvent réparer les alliés en combat.",
        "max_level": 3, "per_level_bonus": {"repair_rate": 0.02},
        "requires": [{"tech_id": "sup_aura", "level": 3}],
        "costs": [
            {"metal": 20000, "crystal": 30000, "deuterium": 8000, "hours": 6},
            {"metal": 40000, "crystal": 60000, "deuterium": 16000,"hours": 12},
            {"metal": 80000, "crystal": 120000,"deuterium": 32000,"hours": 24},
        ],
        "icon": "🔧",
    },

    # ── EXPLORATION ──────────────────────────────────────────────────────────
    "exp_speed": {
        "class": "EXPLORATION", "label": "Moteurs Quantiques",
        "desc": "Les vaisseaux d'exploration sont encore plus rapides.",
        "max_level": 5, "per_level_bonus": {"speed": 0.10},
        "requires": [],
        "costs": [
            {"metal": 1000,  "crystal": 1000, "deuterium": 500,  "hours": 0.5},
            {"metal": 2000,  "crystal": 2000, "deuterium": 1000, "hours": 1},
            {"metal": 4000,  "crystal": 4000, "deuterium": 2000, "hours": 2},
            {"metal": 8000,  "crystal": 8000, "deuterium": 4000, "hours": 4},
            {"metal": 16000, "crystal": 16000,"deuterium": 8000, "hours": 8},
        ],
        "icon": "⚡",
    },
    "exp_stealth": {
        "class": "EXPLORATION", "label": "Camouflage Stellaire",
        "desc": "Améliore la furtivité des vaisseaux d'exploration.",
        "max_level": 4, "per_level_bonus": {"stealth": 5.0},  # +5% furtivité
        "requires": [{"tech_id": "exp_speed", "level": 2}],
        "costs": [
            {"metal": 3000,  "crystal": 2000, "deuterium": 2000, "hours": 1},
            {"metal": 6000,  "crystal": 4000, "deuterium": 4000, "hours": 2},
            {"metal": 12000, "crystal": 8000, "deuterium": 8000, "hours": 4},
            {"metal": 24000, "crystal": 16000,"deuterium": 16000,"hours": 8},
        ],
        "icon": "👁️",
    },
    "exp_cargo": {
        "class": "EXPLORATION", "label": "Soutes Expandables",
        "desc": "Augmente la capacité cargo des vaisseaux d'exploration.",
        "max_level": 4, "per_level_bonus": {"cargo": 0.15},
        "requires": [{"tech_id": "exp_speed", "level": 1}],
        "costs": [
            {"metal": 2000,  "crystal": 1000, "deuterium": 1000, "hours": 0.5},
            {"metal": 4000,  "crystal": 2000, "deuterium": 2000, "hours": 1},
            {"metal": 8000,  "crystal": 4000, "deuterium": 4000, "hours": 2},
            {"metal": 16000, "crystal": 8000, "deuterium": 8000, "hours": 4},
        ],
        "icon": "📦",
    },
    "exp_expedition_bonus": {
        "class": "EXPLORATION", "label": "Protocoles d'Expédition",
        "desc": "Les vaisseaux d'exploration rapportent plus de ressources en expédition.",
        "max_level": 3, "per_level_bonus": {"expedition_bonus": 0.20},
        "requires": [{"tech_id": "exp_stealth", "level": 2}, {"tech_id": "exp_cargo", "level": 2}],
        "costs": [
            {"metal": 30000, "crystal": 20000, "deuterium": 15000,"hours": 8},
            {"metal": 60000, "crystal": 40000, "deuterium": 30000,"hours": 16},
            {"metal": 120000,"crystal": 80000, "deuterium": 60000,"hours": 24},
        ],
        "icon": "🔭",
    },
}

class ResearchRequest(BaseModel):
    tech_id: str


@router.get("/tree")
async def get_tech_tree(player: CurrentPlayer, db: DbDep) -> dict:
    """Retourne l'arbre tech complet avec l'état du joueur."""
    # Récupérer les niveaux actuels du joueur
    player_techs: dict[str, int] = {}
    if hasattr(player, 'tech_levels') and player.tech_levels:
        player_techs = player.tech_levels

    now = datetime.now(UTC)
    r_active = await db.execute(
        select(ResearchQueue)
        .where(ResearchQueue.player_id == player.id, ResearchQueue.is_completed == False)  # noqa: E712
        .limit(1)
    )
    active = r_active.scalar_one_or_none()
    active_tech_id = active.tech_id if active and active.completes_at > now else None

    result = {}
    for tech_id, tech in TECH_TREE.items():
        current_level = player_techs.get(tech_id, 0)
        max_reached = current_level >= tech["max_level"]

        # Vérifier les prérequis
        prereqs_met = all(
            player_techs.get(req["tech_id"], 0) >= req["level"]
            for req in tech["requires"]
        )

        # Coût du prochain niveau
        next_cost = None if max_reached else tech["costs"][current_level]

        result[tech_id] = {
            **tech,
            "current_level": current_level,
            "max_reached": max_reached,
            "prereqs_met": prereqs_met,
            "next_cost": next_cost,
            "is_researching": active_tech_id == tech_id,
            "bonus_summary": {
                stat: round(val * current_level * 100, 1) if "rng" not in stat else val * current_level
                for stat, val in tech["per_level_bonus"].items()
            },
        }

    return {
        "by_class": {
            cls: {k: v for k, v in result.items() if TECH_TREE[k]["class"] == cls}
            for cls in ["ATTACK", "DEFENSE", "SUPPORT", "EXPLORATION"]
        },
        "active_research": {
            "tech_id": active.tech_id,
            "tech_label": active.tech_label,
            "target_level": active.target_level,
            "started_at": active.started_at.isoformat(),
            "completes_at": active.completes_at.isoformat(),
            "eta_seconds": max(0, int((active.completes_at - now).total_seconds())),
        } if active_tech_id else None,
    }


@router.post("/research")
async def start_research(body: ResearchRequest, player: CurrentPlayer, db: DbDep) -> dict:
    """Lance une recherche technologique."""
    player_id = str(player.id)

    if body.tech_id not in TECH_TREE:
        raise HTTPException(status_code=400, detail="Technologie inconnue.")

    tech = TECH_TREE[body.tech_id]
    player_techs: dict[str, int] = {}
    if hasattr(player, 'tech_levels') and player.tech_levels:
        player_techs = dict(player.tech_levels)

    current_level = player_techs.get(body.tech_id, 0)

    if current_level >= tech["max_level"]:
        raise HTTPException(status_code=409, detail="Niveau maximum atteint.")

    # Vérifier les prérequis
    for req in tech["requires"]:
        if player_techs.get(req["tech_id"], 0) < req["level"]:
            req_tech = TECH_TREE.get(req["tech_id"], {})
            raise HTTPException(
                status_code=409,
                detail=f"Prérequis non rempli : {req_tech.get('label', req['tech_id'])} niveau {req['level']} requis."
            )

    now = datetime.now(UTC)

    # Vérifier pas de recherche en cours (avec lock pour éviter les double-soumissions)
    r_active = await db.execute(
        select(ResearchQueue)
        .where(ResearchQueue.player_id == player.id, ResearchQueue.is_completed == False)  # noqa: E712
        .with_for_update()
    )
    active = r_active.scalar_one_or_none()
    if active and active.completes_at > now:
        raise HTTPException(status_code=409, detail="Une recherche est déjà en cours.")

    # Vérifier et déduire les ressources
    cost = tech["costs"][current_level]
    r = await db.execute(
        select(Planet).where(Planet.owner_id == player.id, Planet.is_homeworld == True).with_for_update()  # noqa: E712
    )
    homeworld = r.scalar_one_or_none()
    if not homeworld:
        raise HTTPException(status_code=404, detail="Planète natale introuvable.")

    if (
        math.floor(float(homeworld.metal)) < cost["metal"]
        or math.floor(float(homeworld.crystal)) < cost["crystal"]
        or math.floor(float(homeworld.deuterium)) < cost["deuterium"]
    ):
        raise HTTPException(status_code=402, detail="Ressources insuffisantes pour cette recherche.")

    homeworld.metal     = float(homeworld.metal)     - cost["metal"]
    homeworld.crystal   = float(homeworld.crystal)   - cost["crystal"]
    homeworld.deuterium = float(homeworld.deuterium) - cost["deuterium"]
    db.add(homeworld)

    completes_at = now + timedelta(hours=cost["hours"])
    entry = ResearchQueue(
        player_id=player.id,
        tech_id=body.tech_id,
        tech_label=tech["label"],
        target_level=current_level + 1,
        started_at=now,
        completes_at=completes_at,
    )
    db.add(entry)

    return {
        "tech_id": body.tech_id,
        "label": tech["label"],
        "target_level": current_level + 1,
        "completes_at": completes_at.isoformat(),
        "eta_seconds": int(cost["hours"] * 3600),
    }


@router.post("/research/complete")
async def complete_research(player: CurrentPlayer, db: DbDep) -> dict:
    """Finalise une recherche terminée et applique le bonus."""
    now = datetime.now(UTC)

    r_active = await db.execute(
        select(ResearchQueue)
        .where(ResearchQueue.player_id == player.id, ResearchQueue.is_completed == False)  # noqa: E712
        .with_for_update()
    )
    active = r_active.scalar_one_or_none()

    if not active:
        raise HTTPException(status_code=404, detail="Aucune recherche en cours.")

    if active.completes_at > now:
        raise HTTPException(status_code=409, detail="Recherche pas encore terminée.")

    tech_id = active.tech_id
    player_techs = dict(getattr(player, 'tech_levels', None) or {})
    player_techs[tech_id] = active.target_level

    if hasattr(player, 'tech_levels'):
        player.tech_levels = player_techs
        db.add(player)

    active.is_completed = True
    db.add(active)

    return {
        "tech_id": tech_id,
        "new_level": player_techs[tech_id],
        "bonus": TECH_TREE[tech_id]["per_level_bonus"],
    }
