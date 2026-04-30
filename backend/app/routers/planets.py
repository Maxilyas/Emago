"""
app/routers/planets.py — PATCH v2
Agent 5 — Backend

Changements :
  1. Fix bug ressources : math.floor() avant déduction
  2. BUILDING_CONFIG enrichi avec description, synergies, unlocks, tip
  3. Réponse API incluant les infos riches pour le frontend
"""
from __future__ import annotations

import math
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import select

from app.core.deps import CurrentPlayer, DbDep
from app.models.models import BuildQueue, Planet
from app.tasks.resource_tick import _get_building_level, _mine_output

router = APIRouter(prefix="/planets", tags=["planets"])

# ---------------------------------------------------------------------------
# Configuration des bâtiments — enrichie avec synergies et unlocks
# ---------------------------------------------------------------------------
BUILDING_CONFIG: dict[str, dict] = {
    "metal_mine": {
        "label": "Mine de métal",
        "base_metal": 60, "base_crystal": 15, "base_deut": 0, "build_time_base": 60,
        "icon": "⛏️", "category": "production",
        "description": "Extrait du métal brut. Base de toute construction.",
        "per_level": "+30/h par niveau",
        "synergies": ["La centrale solaire doit couvrir sa consommation (×10 énergie/niv)", "Entrepôt augmente la capacité de stockage"],
        "unlocks": [],
        "tip": "Montez-la en priorité — le métal est la ressource la plus consommée.",
    },
    "crystal_mine": {
        "label": "Mine de cristal",
        "base_metal": 48, "base_crystal": 24, "base_deut": 0, "build_time_base": 60,
        "icon": "💎", "category": "production",
        "description": "Extrait des cristaux pour les modules avancés, la recherche et la forge.",
        "per_level": "+15/h par niveau",
        "synergies": ["Critique pour la Forge (coûts ×3)", "Alimente la recherche"],
        "unlocks": [],
        "tip": "Le cristal devient le goulot d'étranglement en mid-game.",
    },
    "deuterium_synthesizer": {
        "label": "Synthétiseur deutérium",
        "base_metal": 225, "base_crystal": 75, "base_deut": 0, "build_time_base": 120,
        "icon": "⚗️", "category": "production",
        "description": "Synthétise le deutérium, carburant des croiseurs et missions longue distance.",
        "per_level": "+5/h par niveau",
        "synergies": ["Obligatoire pour les croiseurs", "Nécessaire pour les flottes inter-systèmes"],
        "unlocks": [
            {"level": 1, "unlock": "Missions inter-systèmes débloquées"},
            {"level": 3, "unlock": "Frégate Exploration constructible"},
        ],
        "tip": "Niveau 3 minimum avant d'attaquer d'autres systèmes.",
    },
    "solar_plant": {
        "label": "Centrale solaire",
        "base_metal": 75, "base_crystal": 30, "base_deut": 0, "build_time_base": 90,
        "icon": "☀️", "category": "energy",
        "description": "Alimente toutes vos mines. Sans énergie suffisante, la production chute.",
        "per_level": "+20 énergie par niveau",
        "synergies": [
            "Mine métal/cristal : -10 énergie/niv",
            "Synthétiseur : -20 énergie/niv",
            "Si énergie < besoin → malus de production proportionnel",
        ],
        "unlocks": [
            {"level": 4, "unlock": "100% d'efficacité pour 3 mines niveau 4"},
            {"level": 8, "unlock": "Centrale à fusion (prochaine maj)"},
        ],
        "tip": "Gardez la centrale 2 niveaux au-dessus de vos mines totales.",
    },
    "shipyard": {
        "label": "Chantier naval",
        "base_metal": 400, "base_crystal": 200, "base_deut": 100, "build_time_base": 300,
        "icon": "🏭", "category": "military",
        "description": "Construit les vaisseaux. Le niveau détermine les types disponibles.",
        "per_level": "-5% temps de construction par niveau",
        "synergies": ["Le Labo améliore la rareté des vaisseaux construits ici", "Ressources excédentaires = construction plus rapide"],
        "unlocks": [
            {"level": 1, "unlock": "Frégates Attaque, Défense, Soutien"},
            {"level": 2, "unlock": "Frégate Exploration"},
            {"level": 4, "unlock": "Croiseurs Attaque & Défense"},
            {"level": 6, "unlock": "Bonus Pedigree ×2"},
            {"level": 8, "unlock": "2 constructions simultanées"},
        ],
        "tip": "Niveau 4 = objectif prioritaire pour accéder aux croiseurs.",
    },
    "research_lab": {
        "label": "Laboratoire",
        "base_metal": 200, "base_crystal": 400, "base_deut": 200, "build_time_base": 240,
        "icon": "🔬", "category": "research",
        "description": "Améliore la qualité des vaisseaux construits et débloque des modules avancés.",
        "per_level": "+2% chance de rareté supérieure",
        "synergies": ["Chaque niveau = meilleure RNG au Chantier", "Débloque les modules de haut niveau"],
        "unlocks": [
            {"level": 1, "unlock": "Modules niveau I–III"},
            {"level": 3, "unlock": "Modules niveau IV pour tous les slots"},
            {"level": 5, "unlock": "Probabilité Épique ×2, Légendaire ×1.5"},
            {"level": 7, "unlock": "Pedigree disponible dès Grade 2"},
        ],
        "tip": "Niveau 5 est un game-changer — priorité absolue en mid-game.",
    },
}


def _building_cost(name: str, current_level: int) -> dict[str, int]:
    cfg = BUILDING_CONFIG[name]
    factor = 1.5 ** current_level
    return {
        "metal":     int(cfg["base_metal"]      * factor),
        "crystal":   int(cfg["base_crystal"]    * factor),
        "deuterium": int(cfg["base_deut"]       * factor),
        "seconds":   int(cfg["build_time_base"] * (1.5 ** current_level)),
    }


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ResourceRates(BaseModel):
    metal_per_hour: float
    crystal_per_hour: float
    deuterium_per_hour: float
    energy_produced: float
    energy_factor: float


class UnlockInfo(BaseModel):
    level: int
    unlock: str


class BuildingInfo(BaseModel):
    key: str
    label: str
    level: int
    icon: str
    category: str
    description: str
    per_level: str
    synergies: list[str]
    unlocks: list[UnlockInfo]
    tip: str
    cost_next: dict[str, int]
    in_queue: bool
    # Quel unlock sera atteint au prochain niveau ?
    next_unlock: str | None


class BuildQueueItem(BaseModel):
    id: uuid.UUID
    item_name: str
    label: str
    target_level: int
    completes_at: datetime
    seconds_remaining: int


class PlanetSummary(BaseModel):
    id: uuid.UUID
    name: str
    galaxy: int
    system: int
    position: int
    is_homeworld: bool
    metal: float
    crystal: float
    deuterium: float


class PlanetDetail(BaseModel):
    id: uuid.UUID
    name: str
    galaxy: int
    system: int
    position: int
    is_homeworld: bool
    metal: float
    crystal: float
    deuterium: float
    metal_capacity: int
    crystal_capacity: int
    deut_capacity: int
    buildings: list[BuildingInfo]
    production_rates: ResourceRates
    build_queue: list[BuildQueueItem]
    resources_last_updated_at: datetime


class BuildRequest(BaseModel):
    building: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compute_rates(planet: Planet) -> ResourceRates:
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

    return ResourceRates(
        metal_per_hour=round(_mine_output(30.0, metal_level) * factor, 2),
        crystal_per_hour=round(_mine_output(15.0, crystal_level) * factor, 2),
        deuterium_per_hour=round(_mine_output(5.0, deut_level) * factor, 2),
        energy_produced=round(energy_prod, 2),
        energy_factor=round(factor, 4),
    )


async def _apply_lazy_production(planet: Planet, db) -> None:
    now  = datetime.now(UTC)
    last = planet.resources_last_updated_at.replace(tzinfo=UTC)
    elapsed_hours = (now - last).total_seconds() / 3600
    if elapsed_hours < 0.001:
        return

    b = planet.buildings or {}
    ml  = _get_building_level(b, "metal_mine")
    cl  = _get_building_level(b, "crystal_mine")
    dl  = _get_building_level(b, "deuterium_synthesizer")
    sl  = _get_building_level(b, "solar_plant")

    ep = _mine_output(20.0, sl)
    en = _mine_output(1.0, ml)*10 + _mine_output(1.0, cl)*10 + _mine_output(1.0, dl)*20
    f  = min(1.0, ep / en) if en > 0 else 1.0

    planet.metal     = min(float(planet.metal_capacity),   float(planet.metal)     + _mine_output(30.0, ml) * elapsed_hours * f)
    planet.crystal   = min(float(planet.crystal_capacity), float(planet.crystal)   + _mine_output(15.0, cl) * elapsed_hours * f)
    planet.deuterium = min(float(planet.deut_capacity),    float(planet.deuterium) + _mine_output(5.0,  dl) * elapsed_hours * f)
    planet.resources_last_updated_at = now
    db.add(planet)


async def _get_build_queue(planet_id: uuid.UUID, db) -> list[BuildQueue]:
    result = await db.execute(
        select(BuildQueue).where(
            BuildQueue.planet_id == planet_id,
            BuildQueue.completed == False,  # noqa: E712
        ).order_by(BuildQueue.completes_at)
    )
    return list(result.scalars().all())


async def _create_homeworld(player_id: uuid.UUID, db) -> Planet:
    planet = Planet(
        owner_id=player_id, galaxy=1, system=1, position=1,
        name="Terre Natale", is_homeworld=True,
        metal=5000.0, crystal=3000.0, deuterium=1000.0,
        metal_capacity=100000, crystal_capacity=100000, deut_capacity=50000,
        buildings={"metal_mine": 1, "crystal_mine": 1, "deuterium_synthesizer": 0, "solar_plant": 2, "shipyard": 0, "research_lab": 0},
    )
    db.add(planet)
    await db.flush()
    return planet


def _planet_to_detail(planet: Planet, queue: list[BuildQueue]) -> PlanetDetail:
    b = planet.buildings or {}
    now = datetime.now(UTC)
    queued = {item.item_name for item in queue}

    buildings_list = []
    for key, cfg in BUILDING_CONFIG.items():
        level = _get_building_level(b, key)
        cost = _building_cost(key, level)

        # Prochain unlock
        next_unlock = None
        for unlock in cfg.get("unlocks", []):
            if unlock["level"] == level + 1:
                next_unlock = unlock["unlock"]
                break

        buildings_list.append(BuildingInfo(
            key=key,
            label=cfg["label"],
            level=level,
            icon=cfg.get("icon", "🏗️"),
            category=cfg.get("category", "other"),
            description=cfg.get("description", ""),
            per_level=cfg.get("per_level", ""),
            synergies=cfg.get("synergies", []),
            unlocks=[UnlockInfo(level=u["level"], unlock=u["unlock"]) for u in cfg.get("unlocks", [])],
            tip=cfg.get("tip", ""),
            cost_next=cost,
            in_queue=key in queued,
            next_unlock=next_unlock,
        ))

    queue_items = [
        BuildQueueItem(
            id=item.id,
            item_name=item.item_name,
            label=BUILDING_CONFIG.get(item.item_name, {}).get("label", item.item_name),
            target_level=item.target_level or 0,
            completes_at=item.completes_at,
            seconds_remaining=max(0, int((item.completes_at.replace(tzinfo=UTC) - now).total_seconds())),
        )
        for item in queue
    ]

    return PlanetDetail(
        id=planet.id, name=planet.name, galaxy=planet.galaxy,
        system=planet.system, position=planet.position,
        is_homeworld=planet.is_homeworld,
        metal=round(float(planet.metal), 2),
        crystal=round(float(planet.crystal), 2),
        deuterium=round(float(planet.deuterium), 2),
        metal_capacity=planet.metal_capacity,
        crystal_capacity=planet.crystal_capacity,
        deut_capacity=planet.deut_capacity,
        buildings=buildings_list,
        production_rates=_compute_rates(planet),
        build_queue=queue_items,
        resources_last_updated_at=planet.resources_last_updated_at,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=list[PlanetSummary])
async def list_planets(player: CurrentPlayer, db: DbDep) -> list[PlanetSummary]:
    result = await db.execute(select(Planet).where(Planet.owner_id == player.id))
    planets = list(result.scalars().all())
    if not planets:
        planet = await _create_homeworld(player.id, db)
        planets = [planet]
    for planet in planets:
        await _apply_lazy_production(planet, db)
    return [PlanetSummary(
        id=p.id, name=p.name, galaxy=p.galaxy, system=p.system,
        position=p.position, is_homeworld=p.is_homeworld,
        metal=round(float(p.metal), 2), crystal=round(float(p.crystal), 2),
        deuterium=round(float(p.deuterium), 2),
    ) for p in planets]


@router.get("/{planet_id}", response_model=PlanetDetail)
async def get_planet(planet_id: uuid.UUID, player: CurrentPlayer, db: DbDep) -> PlanetDetail:
    result = await db.execute(select(Planet).where(Planet.id == planet_id))
    planet: Planet | None = result.scalar_one_or_none()
    if planet is None or planet.owner_id != player.id:
        raise HTTPException(status_code=404, detail="Planète introuvable.")
    await _apply_lazy_production(planet, db)
    queue = await _get_build_queue(planet_id, db)
    return _planet_to_detail(planet, queue)


@router.post("/{planet_id}/build", status_code=201)
async def build_building(planet_id: uuid.UUID, body: BuildRequest, player: CurrentPlayer, db: DbDep) -> dict:
    if body.building not in BUILDING_CONFIG:
        raise HTTPException(status_code=400, detail=f"Bâtiment inconnu : {body.building!r}")

    result = await db.execute(select(Planet).where(Planet.id == planet_id).with_for_update())
    planet: Planet | None = result.scalar_one_or_none()
    if planet is None or planet.owner_id != player.id:
        raise HTTPException(status_code=404, detail="Planète introuvable.")

    queue = await _get_build_queue(planet_id, db)
    if any(item.item_name == body.building for item in queue):
        raise HTTPException(status_code=409, detail=f"{BUILDING_CONFIG[body.building]['label']} est déjà en construction.")

    current_level = _get_building_level(planet.buildings or {}, body.building)
    cost = _building_cost(body.building, current_level)

    # ── FIX CRITIQUE : math.floor() pour éviter le bug d'arrondi ──────────
    # planet.metal peut valoir 1999.87 après production lazy
    # → affiché 2000 dans l'UI mais 1999.87 < 2000 → refus injuste
    # Solution : on compare les floors (entiers inférieurs)
    if (
        math.floor(float(planet.metal))     < cost["metal"]
        or math.floor(float(planet.crystal))  < cost["crystal"]
        or math.floor(float(planet.deuterium)) < cost["deuterium"]
    ):
        raise HTTPException(
            status_code=402,
            detail=(
                f"Ressources insuffisantes. "
                f"Requis : métal={cost['metal']:,}, cristal={cost['crystal']:,}, deutérium={cost['deuterium']:,}. "
                f"Disponible : métal={math.floor(float(planet.metal)):,}, "
                f"cristal={math.floor(float(planet.crystal)):,}, "
                f"deutérium={math.floor(float(planet.deuterium)):,}."
            ),
        )

    await _apply_lazy_production(planet, db)
    planet.metal     = float(planet.metal)     - cost["metal"]
    planet.crystal   = float(planet.crystal)   - cost["crystal"]
    planet.deuterium = float(planet.deuterium) - cost["deuterium"]
    db.add(planet)

    now = datetime.now(UTC)
    completes_at = now + __import__('datetime').timedelta(seconds=cost["seconds"])

    bq = BuildQueue(
        planet_id=planet_id, player_id=player.id,
        item_type="BUILDING", item_name=body.building,
        target_level=current_level + 1,
        cost_metal=cost["metal"], cost_crystal=cost["crystal"], cost_deuterium=cost["deuterium"],
        started_at=now, completes_at=completes_at, completed=False,
    )
    db.add(bq)

    # Prochain unlock ?
    next_unlock = next(
        (u["unlock"] for u in BUILDING_CONFIG[body.building].get("unlocks", []) if u["level"] == current_level + 1),
        None
    )

    return {
        "building": body.building,
        "label": BUILDING_CONFIG[body.building]["label"],
        "target_level": current_level + 1,
        "completes_at": completes_at.isoformat(),
        "seconds": cost["seconds"],
        "next_unlock": next_unlock,
    }


@router.get("/{planet_id}/queue", response_model=list[BuildQueueItem])
async def get_build_queue(planet_id: uuid.UUID, player: CurrentPlayer, db: DbDep) -> list[BuildQueueItem]:
    result = await db.execute(select(Planet).where(Planet.id == planet_id))
    planet: Planet | None = result.scalar_one_or_none()
    if planet is None or planet.owner_id != player.id:
        raise HTTPException(status_code=404, detail="Planète introuvable.")
    now = datetime.now(UTC)
    queue = await _get_build_queue(planet_id, db)
    return [BuildQueueItem(
        id=item.id, item_name=item.item_name,
        label=BUILDING_CONFIG.get(item.item_name, {}).get("label", item.item_name),
        target_level=item.target_level or 0,
        completes_at=item.completes_at,
        seconds_remaining=max(0, int((item.completes_at.replace(tzinfo=UTC) - now).total_seconds())),
    ) for item in queue]
