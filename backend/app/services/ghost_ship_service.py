"""
Services pour les vaisseaux fantômes (NPC) dans la galaxie.
- Spawn automatique : 1-2 par système, généré à la première consultation
- Combat simplifié contre un ghost ship
- Respawn automatique 1h après défaite
"""
from __future__ import annotations

import random
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ghost_ship_model import GhostShip
from app.models.models import Ship

# ─── Tables de génération ────────────────────────────────────────────────────

_GHOST_NAMES = [
    "Spectre de la Dérive",  "L'Errant Silencieux",  "Ombre de l'Abysses",
    "Fantôme Maudit",        "L'Oublié",             "Ombre Errante",
    "Nébuleuse Morte",       "Écho du Vide",          "Le Condamné",
    "Voix du Néant",         "Vestige Sombre",        "L'Ancien",
    "Spectre Nomade",        "Cri de l'Espace",       "Dérive Éternelle",
    "Le Silencieux",         "Fracture du Temps",     "Ombre Glaciale",
]

_THREAT_RARITY = {1: "COMMON", 2: "RARE", 3: "LEGENDARY"}

_SHIP_TYPES_BY_THREAT = {
    1: ["FIGHTER", "SCOUT", "INTERCEPTOR"],
    2: ["DESTROYER", "CRUISER", "GUNSHIP"],
    3: ["BATTLESHIP", "DREADNOUGHT", "CARRIER"],
}

_BASE_HULL = {1: 800,  2: 2500,  3: 6000}
_BASE_DPS  = {1: 120,  2: 380,   3: 900}
_BASE_LOOT_METAL   = {1: 1500,  2: 5000,  3: 15000}
_BASE_LOOT_CRYSTAL = {1: 800,   2: 2500,  3: 8000}
_RESPAWN_HOURS     = {1: 1,     2: 2,     3: 4}


def _make_ghost(galaxy: int, system: int, threat: int) -> GhostShip:
    """Génère un ghost ship pour le système donné."""
    rng = random.Random(f"{galaxy}-{system}-{threat}-{uuid.uuid4()}")
    hull_var = rng.uniform(0.85, 1.15)
    hull = int(_BASE_HULL[threat] * hull_var)
    ship_type = rng.choice(_SHIP_TYPES_BY_THREAT[threat])
    name = rng.choice(_GHOST_NAMES)
    return GhostShip(
        galaxy=galaxy,
        system=system,
        name=name,
        ship_type=ship_type,
        rarity=_THREAT_RARITY[threat],
        threat_level=threat,
        current_hull=hull,
        max_hull=hull,
        base_stats={
            "hull": hull,
            "dps": int(_BASE_DPS[threat] * hull_var),
            "shield": int(hull * 0.2),
        },
        is_defeated=False,
    )


async def ensure_ghost_ships(galaxy: int, system: int, db: AsyncSession) -> None:
    """Génère 1-2 ghost ships si le système n'en a aucun (actif ou à respawn)."""
    count_r = await db.execute(
        select(func.count(GhostShip.id)).where(
            GhostShip.galaxy == galaxy,
            GhostShip.system == system,
        )
    )
    if (count_r.scalar() or 0) > 0:
        return  # déjà initialisé

    count = random.randint(1, 2)
    threats = random.sample([1, 1, 2, 2, 3], k=count)  # majorité niv 1-2
    for threat in threats:
        db.add(_make_ghost(galaxy, system, threat))
    await db.flush()


async def respawn_defeated(galaxy: int, system: int, db: AsyncSession) -> None:
    """Respawn les ghost ships dont l'heure de respawn est passée."""
    now = datetime.now(UTC)
    result = await db.execute(
        select(GhostShip).where(
            GhostShip.galaxy == galaxy,
            GhostShip.system == system,
            GhostShip.is_defeated == True,  # noqa: E712
            GhostShip.respawn_at <= now,
        )
    )
    for ghost in result.scalars():
        # Regénérer un nouveau ghost à la même menace
        new_ghost = _make_ghost(galaxy, system, ghost.threat_level)
        db.add(new_ghost)
        await db.delete(ghost)
    await db.flush()


async def attack_ghost(
    ghost_id: uuid.UUID,
    ship_ids: list[uuid.UUID],
    db: AsyncSession,
) -> dict:
    """
    Combat simplifié joueur vs ghost ship.
    Retourne : { won, loot, log, ghost_id }
    """
    ghost = await db.get(GhostShip, ghost_id)
    if not ghost:
        raise ValueError("Vaisseau fantôme introuvable.")
    if ghost.is_defeated:
        raise ValueError("Ce vaisseau fantôme est déjà vaincu.")
    if not ship_ids:
        raise ValueError("Sélectionnez au moins un vaisseau.")

    # Charger les vaisseaux du joueur
    ships_r = await db.execute(
        select(Ship).where(Ship.id.in_(ship_ids), Ship.status == "DOCKED")
    )
    ships = ships_r.scalars().all()
    if not ships:
        raise ValueError("Aucun vaisseau disponible (DOCKED).")

    # Agréger les stats
    player_hull  = sum(s.base_stats.get("hull",  500) for s in ships)
    player_dps   = sum(s.base_stats.get("dps",   100) for s in ships)
    ghost_hull   = ghost.current_hull
    ghost_dps    = ghost.base_stats.get("dps", _BASE_DPS[ghost.threat_level])

    log: list[str] = []
    log.append(f"⚔️ {len(ships)} vaisseau(x) vs {ghost.name} [{ghost.rarity}]")

    # Simulation par rounds (max 20)
    p_hull = float(player_hull)
    g_hull = float(ghost_hull)
    won = False
    for rnd in range(1, 21):
        p_hull -= ghost_dps * 0.9   # ghost frappe
        g_hull -= player_dps * 1.0  # joueur frappe
        if g_hull <= 0:
            won = True
            log.append(f"Round {rnd} : Victoire ! {ghost.name} est détruit.")
            break
        if p_hull <= 0:
            log.append(f"Round {rnd} : Défaite. Flotte détruite.")
            break

    loot = {"metal": 0, "crystal": 0}
    if won:
        var = random.uniform(0.8, 1.2)
        loot = {
            "metal":   int(_BASE_LOOT_METAL[ghost.threat_level]   * var),
            "crystal": int(_BASE_LOOT_CRYSTAL[ghost.threat_level] * var),
        }
        log.append(f"💰 Butin : {loot['metal']} métal, {loot['crystal']} cristal")
        ghost.is_defeated = True
        ghost.defeated_at = datetime.now(UTC)
        ghost.respawn_at  = datetime.now(UTC) + timedelta(hours=_RESPAWN_HOURS[ghost.threat_level])
        db.add(ghost)
    else:
        log.append("Revenez avec une flotte plus puissante.")

    await db.flush()
    return {"won": won, "loot": loot, "log": log, "ghost_id": str(ghost_id)}
