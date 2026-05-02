"""
app/services/forge_service.py
Agent 5 — Développeur Backend — v1.1

Responsabilité : La Forge (GDD §5b).

La Forge permet de fusionner deux vaisseaux de même type et même rareté
pour obtenir un vaisseau de rareté supérieure, avec les meilleures stats
des deux parents et 30 % de l'XP du plus expérimenté transférée.

Durée : 8 heures (configurable via settings).
Coût  : équivalent à construire 3 vaisseaux du même type.

Architecture (Agent 3, décision 5) :
  - APScheduler vérifie forge_queue toutes les 60 secondes
  - Redis stocke la progression pour polling client (GET /forge/{id})
  - WebSocket event forge.complete à la finalisation
  - SELECT FOR UPDATE sur les deux vaisseaux pour éviter la double soumission

Race condition mitigée :
  Les deux vaisseaux sont sélectionnés avec FOR UPDATE dans la même transaction.
  La vérification du statut IN_FORGE est faite à l'intérieur du verrou.

Corrections v1.1 (7 bugs) :
  [1] _enum_val() défini localement — extrait .value des enums SQLAlchemy
  [2] transferred_xp calculé avant l'INSERT Ship
  [3] ShipRarity + ShipStatus importés depuis models
  [4] forged_stats → new_base_stats dans le broadcast WS
  [5] total_slots + premium_slots calculés avant le broadcast
  [6] _merge_best_stats reçoit .base_stats (dict), pas les Ship objects
  [7] Cicatrice Dérive filtrée par tag_code='born_in_drift' (robuste)
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import redis.asyncio as aioredis
import secrets
from fastapi import HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_client import get_redis, publish_event
from app.models.models import (          # [3] FIX : ShipRarity + ShipStatus ajoutés
    ForgeQueue, Planet, Ship,
    ShipRarity, ShipStatus, ShipScar, ScarTag,
)
from app.services.ship_build_service import (
    SHIP_TYPE_BUILD_COST,
    _RARITY_SLOTS,
)
from app.services.ship_stats_service import invalidate_hangar_cache, invalidate_ship_cache
from app.services.naming_service import generate_ship_name
from app.services.ship_trait_service import roll_trait

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _enum_val(v: Any) -> str:                    # [1] FIX : défini ici
    """Extrait la valeur string d'un enum SQLAlchemy ou retourne str() en fallback."""
    return v.value if hasattr(v, "value") else str(v)


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_srng_forge = secrets.SystemRandom()

_DRIFT_PROBABILITY    = 0.05
_DRIFT_ELIGIBLE_STATS = ["hull", "shield", "dps", "speed"]
DRIFT_SCAR_TAG_CODE   = "born_in_drift"          # [7] FIX : filtrer par tag_code (unique)

FORGE_DURATION_HOURS = 8

_RARITY_UPGRADE: dict[str, str] = {
    "COMMON":    "UNCOMMON",
    "UNCOMMON":  "RARE",
    "RARE":      "EPIC",
    "EPIC":      "LEGENDARY",
}

_XP_TRANSFER_RATIO = 0.30

_FORGE_STATUS_TTL = FORGE_DURATION_HOURS * 3600 + 600


# ---------------------------------------------------------------------------
# Fonctions Dérive
# ---------------------------------------------------------------------------

def should_produce_drift() -> bool:
    """5 % de chance que la Forge produise une Dérive (GDD créatif §5b)."""
    return _srng_forge.random() < _DRIFT_PROBABILITY


def apply_drift(merged_stats: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """
    Réduit une stat aléatoire éligible de 20 %.
    Retourne (stats_modifiées, clé_de_la_stat_réduite).
    """
    result   = dict(merged_stats)
    eligible = [s for s in _DRIFT_ELIGIBLE_STATS if s in result]
    if not eligible:
        return result, "hull"

    drifted_stat = _srng_forge.choice(eligible)
    original     = result[drifted_stat]

    if drifted_stat == "speed":
        result[drifted_stat] = round(original * 0.80, 1)
    else:
        result[drifted_stat] = int(round(original * 0.80))

    return result, drifted_stat


# ---------------------------------------------------------------------------
# Démarrage de la Forge
# ---------------------------------------------------------------------------

async def start_forge(
    db: AsyncSession,
    player_id: uuid.UUID,
    ship_a_id: uuid.UUID,
    ship_b_id: uuid.UUID,
) -> dict[str, Any]:
    """
    Lance une opération de Forge.

    Validations (Agent 3, spec /forge) :
      - ship_a et ship_b appartiennent au joueur
      - Même ship_type strict
      - Même rarity
      - Les deux sont DOCKED (pas IN_FLEET ni déjà IN_FORGE)
      - Rareté améliorable (pas LEGENDARY)
      - Ressources suffisantes sur la planète (3× coût de construction)

    Returns:
        {"forge_id": str, "completed_at": ISO, "progress_pct": 0, "eta_seconds": int}
    """
    if ship_a_id == ship_b_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible de forger un vaisseau avec lui-même.",
        )

    # Verrou anti double-soumission — ORDER BY id pour éviter les deadlocks
    ordered_ids  = sorted([ship_a_id, ship_b_id])
    ships_result = await db.execute(
        select(Ship)
        .where(Ship.id.in_(ordered_ids))
        .order_by(Ship.id)
        .with_for_update()
    )
    ships: list[Ship] = list(ships_result.scalars().all())

    if len(ships) != 2:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Un ou plusieurs vaisseaux introuvables.",
        )

    ship_a = next(s for s in ships if s.id == ship_a_id)
    ship_b = next(s for s in ships if s.id == ship_b_id)

    for ship in (ship_a, ship_b):
        if ship.owner_id != player_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Le vaisseau {ship.id} ne vous appartient pas.",
            )

    if _enum_val(ship_a.ship_type) != _enum_val(ship_b.ship_type):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Types incompatibles : {ship_a.ship_type!r} ≠ {ship_b.ship_type!r}. "
                "La Forge exige le même type strict."
            ),
        )

    rarity_a = _enum_val(ship_a.rarity)
    rarity_b = _enum_val(ship_b.rarity)

    if rarity_a != rarity_b:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Raretés incompatibles : {rarity_a} ≠ {rarity_b}.",
        )

    if rarity_a not in _RARITY_UPGRADE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Les vaisseaux Légendaires ne peuvent pas être forgés.",
        )

    for ship in (ship_a, ship_b):
        if _enum_val(ship.status) != "DOCKED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Le vaisseau {ship.id} n'est pas amarré "
                    f"(statut : {_enum_val(ship.status)}). "
                    "Seuls les vaisseaux DOCKED peuvent être forgés."
                ),
            )

    # Planète source pour les ressources
    planet_id = ship_a.planet_id or ship_b.planet_id
    if planet_id is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Aucun des vaisseaux n'est assigné à une planète.",
        )

    planet_result = await db.execute(
        select(Planet).where(Planet.id == planet_id).with_for_update()
    )
    planet: Planet | None = planet_result.scalar_one_or_none()
    if planet is None or planet.owner_id != player_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Planète source introuvable ou non possédée.",
        )

    base_cost  = SHIP_TYPE_BUILD_COST.get(ship_a.ship_type, {})
    forge_cost = {k: v * 3 for k, v in base_cost.items()}
    _check_forge_resources(planet, forge_cost, db)

    ship_a.status = ShipStatus.IN_FORGE
    ship_b.status = ShipStatus.IN_FORGE
    db.add(ship_a)
    db.add(ship_b)

    now          = datetime.now(UTC)
    completed_at = now + timedelta(hours=FORGE_DURATION_HOURS)

    forge_entry = ForgeQueue(
        id=uuid.uuid4(),
        ship_a_id=ship_a_id,
        ship_b_id=ship_b_id,
        player_id=player_id,
        started_at=now,
        completed_at=completed_at,
        result_ship_id=None,
    )
    db.add(forge_entry)

    await _store_forge_status(forge_entry.id, completed_at, progress_pct=0, player_id=player_id)
    await invalidate_hangar_cache(player_id)

    return {
        "forge_id":     str(forge_entry.id),
        "completed_at": completed_at.isoformat(),
        "progress_pct": 0,
        "eta_seconds":  int(FORGE_DURATION_HOURS * 3600),
    }


# ---------------------------------------------------------------------------
# Finalisation de la Forge (appelée par le scheduler APScheduler)
# ---------------------------------------------------------------------------

async def finalize_forge(
    db: AsyncSession,
    forge_entry: ForgeQueue,
) -> Ship:
    """
    Finalise une entrée de forge dont `completed_at` est passé.

    Flux :
      1. Recharge les deux vaisseaux parents (avec FOR UPDATE)
      2. Fusionne les stats (max de chaque stat)
      3. Applique éventuellement la Dérive (5%)
      4. Génère nom procédural + trait narratif
      5. Calcule l'XP transférée (30% du parent le plus expérimenté)
      6. Crée le nouveau Ship en DOCKED
      7. Ajoute la cicatrice "Né dans la Dérive" si applicable
      8. Marque les parents SCRAPPED
      9. Met à jour forge_queue + Redis + broadcast WS

    Returns:
        Le nouveau vaisseau forgé (non committé — le commit est délégué à run_forge_tick).
    """
    ships_result = await db.execute(
        select(Ship)
        .where(Ship.id.in_([forge_entry.ship_a_id, forge_entry.ship_b_id]))
        .with_for_update()
    )
    parents: list[Ship] = list(ships_result.scalars().all())

    if len(parents) != 2:
        raise RuntimeError(
            f"Forge {forge_entry.id} : vaisseaux parents introuvables à la finalisation."
        )

    ship_a = next(s for s in parents if s.id == forge_entry.ship_a_id)
    ship_b = next(s for s in parents if s.id == forge_entry.ship_b_id)

    # --- Rareté et classe résultantes ---
    rarity_str = _enum_val(ship_a.rarity)
    class_str  = _enum_val(ship_a.class_)
    new_rarity_str = _RARITY_UPGRADE[rarity_str]

    # --- [6] FIX : passer .base_stats (dict), pas les Ship objects ---
    new_base_stats = _merge_best_stats(ship_a.base_stats, ship_b.base_stats)

    # --- Dérive (5% chance) ---
    is_drift   = should_produce_drift()
    drift_stat: str | None = None
    if is_drift:
        new_base_stats, drift_stat = apply_drift(new_base_stats)

    # --- Nom procédural + trait narratif ---
    new_name  = generate_ship_name(class_str, new_rarity_str)
    new_trait = roll_trait()

    # --- [2] FIX : calculer transferred_xp avant le Ship() INSERT ---
    max_xp        = max(ship_a.combat_xp, ship_b.combat_xp)
    transferred_xp = int(max_xp * _XP_TRANSFER_RATIO)

    # --- [5] FIX : calculer slots avant le broadcast ---
    total_slots, premium_slots = _RARITY_SLOTS[new_rarity_str]

    # --- INSERT nouveau vaisseau ---
    new_ship = Ship(
        owner_id   = forge_entry.player_id,
        planet_id  = ship_a.planet_id,
        ship_type  = ship_a.ship_type,
        class_     = ship_a.class_,
        rarity     = ShipRarity(new_rarity_str),      # [3] FIX : ShipRarity importé
        grade      = 0,
        combat_xp  = transferred_xp,                  # [2] FIX : variable définie
        base_stats = new_base_stats,
        status     = ShipStatus.DOCKED,               # [3] FIX : ShipStatus importé
        trait      = new_trait,
        name       = new_name,
        is_drift   = is_drift,
    )
    db.add(new_ship)
    await db.flush()  # obtenir new_ship.id avant les opérations suivantes

    # --- Cicatrice Dérive ---
    if is_drift:
        # [7] FIX : filtrer par tag_code (champ unique) plutôt que narrative
        tag_result = await db.execute(
            select(ScarTag).where(ScarTag.tag_code == DRIFT_SCAR_TAG_CODE).limit(1)
        )
        scar_tag = tag_result.scalar_one_or_none()
        if scar_tag:
            db.add(ShipScar(ship_id=new_ship.id, tag_id=scar_tag.id))
        else:
            logger.warning(
                "Tag cicatrice '%s' introuvable — cicatrice Dérive non assignée "
                "pour le vaisseau %s. Vérifier migration 0006.",
                DRIFT_SCAR_TAG_CODE, new_ship.id,
            )

    # --- Parents consommés ---
    ship_a.status = ShipStatus("SCRAPPED") if hasattr(ShipStatus, "SCRAPPED") \
        else "SCRAPPED"
    ship_b.status = ship_a.status
    db.add(ship_a)
    db.add(ship_b)

    # Invalider le cache Redis des deux parents — leur ship:{id}:stats
    # resterait chaud sinon et pointerait vers un vaisseau scrappé.
    await invalidate_ship_cache(ship_a.id)
    await invalidate_ship_cache(ship_b.id)

    # --- Mise à jour forge_queue ---
    forge_entry.result_ship_id = new_ship.id
    forge_entry.is_completed   = True
    db.add(forge_entry)

    # --- Redis 100 % ---
    await _store_forge_status(
        forge_entry.id,
        forge_entry.completed_at,
        progress_pct=100,
        result_ship_id=new_ship.id,
        player_id=forge_entry.player_id,
    )

    await invalidate_hangar_cache(forge_entry.player_id)

    # --- [4] FIX : new_base_stats (pas forged_stats) + champs RPG ---
    await publish_event(
        channel=f"player:{forge_entry.player_id}",
        event={
            "type": "forge.complete",
            "data": {
                "forge_id":      str(forge_entry.id),
                "new_ship_id":   str(new_ship.id),
                "rarity":        new_rarity_str,
                "base_stats":    new_base_stats,          # [4] FIX
                "combat_xp":     transferred_xp,
                "slots_total":   total_slots,             # [5] FIX
                "slots_premium": premium_slots,           # [5] FIX
                "trait":         new_trait,
                "name":          new_name,
                "is_drift":      is_drift,
            },
        },
    )

    return new_ship


# ---------------------------------------------------------------------------
# Statut de forge (pour GET /forge/{id})
# ---------------------------------------------------------------------------

async def get_forge_status(forge_id: uuid.UUID) -> dict[str, Any] | None:
    """
    Retourne le statut actuel d'une forge depuis Redis.
    Retourne None si la clé n'existe plus (forge expirée ou jamais créée).
    """
    r: aioredis.Redis = get_redis()
    raw = await r.get(f"forge:{forge_id}:status")
    return json.loads(raw) if raw else None


# ---------------------------------------------------------------------------
# Job APScheduler
# ---------------------------------------------------------------------------

async def run_forge_tick(db: AsyncSession) -> None:
    """
    Tâche périodique (toutes les 60 s).
    Finalise les forges dont completed_at <= now().
    """
    now = datetime.now(UTC)

    result = await db.execute(
        select(ForgeQueue).where(
            and_(
                ForgeQueue.completed_at <= now,
                ForgeQueue.result_ship_id.is_(None),
            )
        )
    )
    pending: list[ForgeQueue] = list(result.scalars().all())

    for forge_entry in pending:
        try:
            await finalize_forge(db, forge_entry)
            await db.commit()
        except Exception as exc:
            await db.rollback()
            logger.error(
                "Erreur finalisation forge %s : %s",
                forge_entry.id, exc, exc_info=True,
            )


# ---------------------------------------------------------------------------
# Helpers privés
# ---------------------------------------------------------------------------

def _merge_best_stats(
    stats_a: dict[str, float],
    stats_b: dict[str, float],
) -> dict[str, float]:
    """
    Prend le maximum de chaque stat entre les deux parents (GDD §5b).
    Attend deux dicts (base_stats), pas des objets Ship.
    """
    all_keys = set(stats_a) | set(stats_b)
    return {k: max(stats_a.get(k, 0), stats_b.get(k, 0)) for k in all_keys}


def _check_forge_resources(
    planet: Planet,
    cost: dict[str, float],
    db: AsyncSession,
) -> None:
    """
    Vérifie et déduit les ressources de forge depuis la planète.
    Raises HTTPException 402 si ressources insuffisantes.
    """
    needed_metal   = cost.get("metal",     0)
    needed_crystal = cost.get("crystal",   0)
    needed_deut    = cost.get("deuterium", 0)

    if (
        float(planet.metal)     < needed_metal
        or float(planet.crystal)  < needed_crystal
        or float(planet.deuterium) < needed_deut
    ):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                f"Ressources insuffisantes pour la Forge. "
                f"Requis : métal={needed_metal:.0f}, cristal={needed_crystal:.0f}, "
                f"deutérium={needed_deut:.0f}. "
                f"Disponible sur {planet.name} : "
                f"métal={float(planet.metal):.0f}, "
                f"cristal={float(planet.crystal):.0f}, "
                f"deutérium={float(planet.deuterium):.0f}."
            ),
        )

    planet.metal     = float(planet.metal)     - needed_metal
    planet.crystal   = float(planet.crystal)   - needed_crystal
    planet.deuterium = float(planet.deuterium) - needed_deut
    db.add(planet)


async def _store_forge_status(
    forge_id: uuid.UUID,
    completed_at: datetime,
    progress_pct: int,
    player_id: uuid.UUID | None = None,
    result_ship_id: uuid.UUID | None = None,
) -> None:
    """Écrit le statut de forge dans Redis (TTL = durée forge + 10 min)."""
    r: aioredis.Redis = get_redis()
    payload: dict[str, Any] = {
        "forge_id":     str(forge_id),
        "completed_at": completed_at.isoformat(),
        "progress_pct": progress_pct,
        "eta_seconds":  max(
            0,
            int((completed_at.replace(tzinfo=UTC) - datetime.now(UTC)).total_seconds()),
        ),
    }
    if player_id is not None:
        payload["player_id"] = str(player_id)
    if result_ship_id is not None:
        payload["result_ship_id"] = str(result_ship_id)

    await r.setex(f"forge:{forge_id}:status", _FORGE_STATUS_TTL, json.dumps(payload))