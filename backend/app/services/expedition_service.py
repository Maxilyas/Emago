"""
app/services/expedition_service.py
Agent 5 — Backend

Le Centre d'Expédition envoie des vaisseaux dans des missions autonomes
(pas contre d'autres joueurs). Résultats variés et narratifs.

Mécaniques :
  - Durée : 2h / 6h / 12h selon la distance choisie
  - 12 événements narratifs pondérés (bon → neutre → mauvais)
  - Résultats possibles : XP, ressources, modules, cicatrices, perte partielle
  - Le vaisseau le plus expérimenté de la flotte reçoit les gains
  - Risk/reward : plus long = meilleur potentiel mais risque plus élevé
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Planet, Ship, ShipScar
from app.services.module_inventory_service import create_loot_crate

# ---------------------------------------------------------------------------
# Durées d'expédition
# ---------------------------------------------------------------------------
class ExpeditionDuration(str, Enum):
    SHORT  = "SHORT"   # 2h  — risque faible, récompense modeste
    MEDIUM = "MEDIUM"  # 6h  — risque moyen, récompense correcte
    LONG   = "LONG"    # 12h — risque élevé, récompense élevée

DURATION_HOURS = {
    ExpeditionDuration.SHORT:  2,
    ExpeditionDuration.MEDIUM: 6,
    ExpeditionDuration.LONG:   12,
}

DURATION_COST = {
    ExpeditionDuration.SHORT:  {"deuterium": 500},
    ExpeditionDuration.MEDIUM: {"deuterium": 1_500},
    ExpeditionDuration.LONG:   {"deuterium": 4_000},
}

# ---------------------------------------------------------------------------
# Pool d'événements narratifs (pondérés)
# ---------------------------------------------------------------------------
# weight total = 100
EXPEDITION_EVENTS = [
    # ── Bons événements (total 45) ────────────────────────────────────────
    {
        "id": "debris_field",
        "title": "Champ de débris",
        "narrative": "Votre flotte découvre les restes d'une ancienne bataille. Les épaves contiennent encore de précieuses ressources.",
        "weight": 18,
        "outcomes": {
            "resources": {"metal": [2_000, 8_000], "crystal": [1_000, 4_000]},
            "xp_bonus": [20, 60],
        },
    },
    {
        "id": "alien_artifact",
        "title": "Artefact alien",
        "narrative": "Un signal étrange mène votre flotte vers un objet inconnu flottant dans le vide. Il renferme des données technologiques précieuses.",
        "weight": 12,
        "outcomes": {
            "module_drop": True,   # module aléatoire niveau 1–3
            "xp_bonus": [40, 80],
        },
    },
    {
        "id": "derelict_station",
        "title": "Station abandonnée",
        "narrative": "Une station désaffectée depuis des siècles. Vos ingénieurs récupèrent cristaux et composants rares.",
        "weight": 10,
        "outcomes": {
            "resources": {"crystal": [3_000, 10_000], "deuterium": [500, 2_000]},
            "xp_bonus": [30, 50],
        },
    },
    {
        "id": "rogue_freighter",
        "title": "Cargo pirate capturé",
        "narrative": "Un cargo sans équipage dérive sur votre route. Votre flotte l'intercepte et récupère sa cargaison.",
        "weight": 5,
        "outcomes": {
            "resources": {"metal": [5_000, 15_000], "crystal": [2_000, 6_000], "deuterium": [1_000, 3_000]},
            "xp_bonus": [50, 100],
        },
    },
    # ── Événements neutres (total 30) ─────────────────────────────────────
    {
        "id": "void_storm",
        "title": "Tempête du vide",
        "narrative": "Une perturbation gravitationnelle ralentit votre flotte. Rien de grave, mais le voyage prend plus de temps.",
        "weight": 15,
        "outcomes": {
            "resources": {},
            "xp_bonus": [10, 25],
            "scar": {"tag": "Survivant de la Tempête du Vide", "condition": "easy"},
        },
    },
    {
        "id": "strange_signal",
        "title": "Signal mystérieux",
        "narrative": "Votre flotte capte un signal non identifié. Après enquête, il s'agit d'une balise ancienne — sans valeur militaire.",
        "weight": 10,
        "outcomes": {
            "xp_bonus": [15, 40],
        },
    },
    {
        "id": "navigation_error",
        "title": "Erreur de navigation",
        "narrative": "Un calcul de saut mal exécuté envoie votre flotte dans le mauvais système. Le retour consomme plus de carburant.",
        "weight": 5,
        "outcomes": {
            "deuterium_loss": [200, 800],
            "xp_bonus": [5, 20],
        },
    },
    # ── Événements difficiles (total 20) ──────────────────────────────────
    {
        "id": "pirate_ambush",
        "title": "Embuscade pirate",
        "narrative": "Des pirates attaquent votre flotte en formation. Combat difficile — vos vaisseaux s'en sortent mais avec des dommages.",
        "weight": 10,
        "outcomes": {
            "xp_bonus": [80, 150],  # Beaucoup d'XP car combat difficile
            "scar": {"tag": "Rescapé de l'Embuscade des Pirates", "condition": "combat"},
            "hull_damage": True,   # Le vaisseau revient avec une cicatrice
        },
    },
    {
        "id": "radiation_zone",
        "title": "Zone de radiation",
        "narrative": "Votre flotte traverse accidentellement une zone de radiation intense. Les boucliers tiennent mais les systèmes sont endommagés.",
        "weight": 6,
        "outcomes": {
            "xp_bonus": [30, 60],
            "scar": {"tag": "Irradié par la Nébuleuse Kha", "condition": "hazard"},
        },
    },
    {
        "id": "patrol_encounter",
        "title": "Patrouille ennemie",
        "narrative": "Une patrouille territoriale hostile. Après un engagement serré, votre flotte se retire avec des réparations à effectuer.",
        "weight": 4,
        "outcomes": {
            "xp_bonus": [100, 200],
            "scar": {"tag": "Vétéran des Frontières Disputées", "condition": "combat"},
            "module_damage": True,  # Risque de perte d'un module
        },
    },
    # ── Événements exceptionnels (total 5) ────────────────────────────────
    {
        "id": "legendary_wreck",
        "title": "Épave légendaire",
        "narrative": "L'improbable ! Les capteurs détectent l'épave d'un vaisseau légendaire d'une guerre oubliée. Sa coque renferme encore des trésors.",
        "weight": 3,
        "outcomes": {
            "resources": {"metal": [10_000, 30_000], "crystal": [5_000, 15_000]},
            "module_drop": True,
            "module_rare_chance": 0.4,  # 40% de chance module niveau 4-5
            "xp_bonus": [150, 300],
        },
    },
    {
        "id": "first_contact",
        "title": "Premier contact",
        "narrative": "Une civilisation inconnue. L'échange est bref mais bouleversant — vos ingénieurs découvrent des schémas technologiques révolutionnaires.",
        "weight": 2,
        "outcomes": {
            "module_drop": True,
            "module_rare_chance": 0.7,  # 70% module niveau 4-5
            "xp_bonus": [200, 400],
            "scar": {"tag": "Envoyé du Premier Contact", "condition": "legendary"},
        },
    },
]

# Pool de tags de cicatrices d'expédition
EXPEDITION_SCAR_TAGS = [
    "Rescapé de la Tempête du Vide",
    "Irradié par la Nébuleuse Kha",
    "Vétéran des Frontières Disputées",
    "Survivant de l'Embuscade Pirate",
    "Envoyé du Premier Contact",
    "Explorateur des Confins",
    "Rescapé de l'Anomalie Sigma",
    "Porteur du Signal Ancien",
]

# Modules pouvant dropper en expédition
MODULE_DROP_POOL = [
    {"type": "PROPELLER", "level": 1}, {"type": "ARMOR",  "level": 1},
    {"type": "CANNON",    "level": 1}, {"type": "SHIELD", "level": 1},
    {"type": "CARGO",     "level": 2}, {"type": "PROPELLER", "level": 2},
    {"type": "CANNON",    "level": 2}, {"type": "ARMOR",  "level": 3},
    {"type": "CANNON",    "level": 3}, {"type": "EMITTER","level": 2},
    {"type": "ARMOR",     "level": 4}, {"type": "CANNON", "level": 4},  # rares
    {"type": "PROPELLER", "level": 5}, {"type": "CANNON", "level": 5},  # très rares
]

def _roll_event(seed: str) -> dict:
    """Sélectionne un événement via tirage pondéré déterministe."""
    h = int(hashlib.sha256(seed.encode()).hexdigest(), 16)
    total = sum(e["weight"] for e in EXPEDITION_EVENTS)
    roll = h % total
    cumul = 0
    for event in EXPEDITION_EVENTS:
        cumul += event["weight"]
        if roll < cumul:
            return event
    return EXPEDITION_EVENTS[0]

def _roll_range(seed: str, key: str, rng: list[int]) -> int:
    h = int(hashlib.sha256(f"{seed}{key}".encode()).hexdigest(), 16)
    return rng[0] + (h % (rng[1] - rng[0] + 1))

def _roll_module(seed: str, rare_chance: float = 0.0) -> dict:
    h = int(hashlib.sha256(f"{seed}module".encode()).hexdigest(), 16)
    if rare_chance > 0 and (h % 100) / 100 < rare_chance:
        pool = [m for m in MODULE_DROP_POOL if m["level"] >= 4]
    else:
        pool = [m for m in MODULE_DROP_POOL if m["level"] <= 3]
    return pool[h % len(pool)]

async def resolve_expedition(
    expedition_id: str,
    ship_ids: list[uuid.UUID],
    duration: ExpeditionDuration,
    db: AsyncSession,
) -> dict[str, Any]:
    """
    Résout une expédition terminée.
    Appelé par le scheduler quand completed_at <= now().
    Retourne le rapport complet.
    """
    seed = f"{expedition_id}{duration.value}"
    event = _roll_event(seed)
    outcomes = event["outcomes"]
    report: dict[str, Any] = {
        "expedition_id": expedition_id,
        "event_id": event["id"],
        "title": event["title"],
        "narrative": event["narrative"],
        "resources_gained": {},
        "xp_gained": {},
        "loot_crates_created": [],
        "scars_earned": [],
        "duration": duration.value,
    }

    # Charger les vaisseaux
    ships = []
    for sid in ship_ids:
        r = await db.execute(select(Ship).where(Ship.id == sid))
        s = r.scalar_one_or_none()
        if s:
            ships.append(s)

    if not ships:
        return report

    # Vaisseau principal (le plus gradé)
    lead_ship = max(ships, key=lambda s: (s.grade, s.combat_xp))

    # ── Ressources ───────────────────────────────────────────────────────
    res_gain: dict[str, int] = {}
    if "resources" in outcomes:
        for res_key, rng in outcomes["resources"].items():
            val = _roll_range(seed, res_key, rng)
            # Multiplier par durée
            multiplier = {ExpeditionDuration.SHORT: 0.6, ExpeditionDuration.MEDIUM: 1.0, ExpeditionDuration.LONG: 1.8}[duration]
            res_gain[res_key] = int(val * multiplier)
        report["resources_gained"] = res_gain

        # Chercher planète natale pour ajouter les ressources
        r = await db.execute(select(Planet).where(Planet.owner_id == lead_ship.owner_id, Planet.is_homeworld == True))  # noqa: E712
        homeworld = r.scalar_one_or_none()
        if homeworld:
            homeworld.metal     = min(float(homeworld.metal_capacity),   float(homeworld.metal)     + res_gain.get("metal", 0))
            homeworld.crystal   = min(float(homeworld.crystal_capacity), float(homeworld.crystal)   + res_gain.get("crystal", 0))
            homeworld.deuterium = min(float(homeworld.deut_capacity),    float(homeworld.deuterium) + res_gain.get("deuterium", 0))
            db.add(homeworld)

    # ── Perte deutérium ──────────────────────────────────────────────────
    if "deuterium_loss" in outcomes:
        loss = _roll_range(seed, "deut_loss", outcomes["deuterium_loss"])
        report["deuterium_lost"] = loss

    # ── XP ───────────────────────────────────────────────────────────────
    if "xp_bonus" in outcomes:
        xp = _roll_range(seed, "xp", outcomes["xp_bonus"])
        multiplier = {ExpeditionDuration.SHORT: 0.7, ExpeditionDuration.MEDIUM: 1.0, ExpeditionDuration.LONG: 1.5}[duration]
        xp = int(xp * multiplier)
        report["xp_gained"][str(lead_ship.id)] = xp
        lead_ship.combat_xp = (lead_ship.combat_xp or 0) + xp
        db.add(lead_ship)

    # ── Module drop → LootCrate ──────────────────────────────────────────
    if outcomes.get("module_drop"):
        rare_ch = outcomes.get("module_rare_chance", 0.0)
        # PREMIUM si event exceptionnel OU expédition longue
        crate_type = (
            "PREMIUM"
            if rare_ch >= 0.4 or duration == ExpeditionDuration.LONG
            else "STANDARD"
        )
        crate = await create_loot_crate(
            player_id=lead_ship.owner_id,
            crate_type=crate_type,
            source="EXPEDITION",
            source_ship_name=event["title"],  # titre de l'événement comme mémoire
            db=db,
        )
        report["loot_crates_created"].append({
            "crate_id":   str(crate.id),
            "crate_type": crate_type,
            "event":      event["id"],
        })

    # ── Cicatrices ───────────────────────────────────────────────────────
    if "scar" in outcomes:
        scar_data = outcomes["scar"]
        scar = ShipScar(ship_id=lead_ship.id, tag_id=1)  # tag_id simplifié
        db.add(scar)
        report["scars_earned"].append({
            "ship_id": str(lead_ship.id),
            "tag": scar_data["tag"],
        })

    return report
