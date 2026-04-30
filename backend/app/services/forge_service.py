"""
app/services/forge_service.py
Agent 5 — Développeur Backend

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
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import redis.asyncio as aioredis
from fastapi import HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_client import get_redis, publish_event
from app.models.models import ForgeQueue, Player, Ship
from app.services.ship_build_service import (
    SHIP_TYPE_BUILD_COST,
    generate_base_stats,
    _RARITY_SLOTS,
)
from app.services.ship_stats_service import (
    invalidate_hangar_cache,
    invalidate_ship_cache,
)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

FORGE_DURATION_HOURS = 8

# Rareté résultante (rareté supérieure d'un cran, GDD §5b)
_RARITY_UPGRADE: dict[str, str] = {
    "COMMON":    "UNCOMMON",
    "UNCOMMON":  "RARE",
    "RARE":      "EPIC",
    "EPIC":      "LEGENDARY",
    # LEGENDARY ne peut pas être forgé (pas de rareté supérieure)
}

# Fraction d'XP transférée du vaisseau le plus expérimenté (GDD §5b)
_XP_TRANSFER_RATIO = 0.30

# TTL Redis pour le statut de forge (en secondes — légèrement au-dessus de 8h)
_FORGE_STATUS_TTL = FORGE_DURATION_HOURS * 3600 + 600


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
      - Ressources suffisantes (3× coût de construction)

    Atomicité : SELECT FOR UPDATE sur les deux vaisseaux dans la même transaction.

    Returns:
        {"forge_id": str, "completed_at": ISO, "progress_pct": 0}
    """
    if ship_a_id == ship_b_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible de forger un vaisseau avec lui-même.",
        )

    # --- Verrou sur les deux vaisseaux (anti double-soumission) ---
    # ORDER BY id pour éviter les deadlocks (toujours verrouiller dans le même ordre)
    ordered_ids = sorted([ship_a_id, ship_b_id])
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

    ship_a = next((s for s in ships if s.id == ship_a_id), None)
    ship_b = next((s for s in ships if s.id == ship_b_id), None)

    # --- Validations propriété ---
    for ship in (ship_a, ship_b):
        if ship.owner_id != player_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Le vaisseau {ship.id} ne vous appartient pas.",
            )

    # --- Validations compatibilité ---
    if ship_a.ship_type != ship_b.ship_type:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Types incompatibles : {ship_a.ship_type!r} ≠ {ship_b.ship_type!r}. "
                f"La Forge exige le même type strict."
            ),
        )

    if ship_a.rarity != ship_b.rarity:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Raretés incompatibles : {ship_a.rarity} ≠ {ship_b.rarity}. "
                f"La Forge exige la même rareté."
            ),
        )

    if ship_a.rarity not in _RARITY_UPGRADE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Les vaisseaux Légendaires ne peuvent pas être forgés (rareté maximale).",
        )

    # --- Validation statuts ---
    for ship in (ship_a, ship_b):
        if ship.status != "DOCKED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Le vaisseau {ship.id} n'est pas amarré "
                    f"(statut actuel : {ship.status}). "
                    f"Seuls les vaisseaux DOCKED peuvent être forgés."
                ),
            )

    # --- Ressources (3× coût de construction, GDD §5b) ---
    base_cost = SHIP_TYPE_BUILD_COST.get(ship_a.ship_type, {})
    forge_cost = {k: v * 3 for k, v in base_cost.items()}

    player_result = await db.execute(
        select(Player).where(Player.id == player_id).with_for_update()
    )
    player: Player | None = player_result.scalar_one_or_none()
    if player is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Joueur introuvable.")

    _check_forge_resources(player, forge_cost, db)

    # --- Passage des vaisseaux en IN_FORGE ---
    ship_a.status = "IN_FORGE"
    ship_b.status = "IN_FORGE"
    db.add(ship_a)
    db.add(ship_b)

    # --- Création de l'entrée ForgeQueue ---
    now = datetime.now(UTC)
    completed_at = now + timedelta(hours=FORGE_DURATION_HOURS)

    forge_entry = ForgeQueue(
        id=uuid.uuid4(),
        ship_a_id=ship_a_id,
        ship_b_id=ship_b_id,
        player_id=player_id,
        started_at=now,
        completed_at=completed_at,
        result_ship_id=None,   # rempli par le scheduler à la finalisation
    )
    db.add(forge_entry)

    # --- Cache Redis : statut initial pour polling ---
    await _store_forge_status(forge_entry.id, completed_at, progress_pct=0)

    # --- Invalidation cache hangar ---
    await invalidate_hangar_cache(player_id)

    return {
        "forge_id":    str(forge_entry.id),
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
      2. Calcule les stats du vaisseau résultant :
           - rarity : +1 cran
           - base_stats : max() de chaque stat des deux parents
           - combat_xp : 30 % du parent le plus expérimenté
      3. Crée le nouveau Ship en DOCKED
      4. Marque les parents comme consommés (soft-delete : status = "SCRAPPED")
      5. Met à jour forge_queue.result_ship_id
      6. Met à jour Redis (progression 100 %)
      7. Broadcast WS forge.complete

    Returns:
        Le nouveau vaisseau forgé (non committé).
    """
    # Recharge avec verrou pour éviter qu'un autre processus ne touche ces vaisseaux
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

    # --- Calcul des stats du vaisseau résultant ---
    result_rarity = _RARITY_UPGRADE[ship_a.rarity]

    # Meilleures stats des deux parents stat par stat (GDD §5b)
    forged_stats = _merge_best_stats(ship_a.base_stats, ship_b.base_stats)

    # XP transférée : 30 % du plus expérimenté (GDD §5b)
    max_parent_xp = max(ship_a.combat_xp, ship_b.combat_xp)
    transferred_xp = int(max_parent_xp * _XP_TRANSFER_RATIO)

    # Slots selon la nouvelle rareté
    total_slots, premium_slots = _RARITY_SLOTS[result_rarity]

    # --- Création du vaisseau résultant ---
    now = datetime.now(UTC)
    new_ship = Ship(
        id=uuid.uuid4(),
        owner_id=forge_entry.player_id,
        ship_type=ship_a.ship_type,
        ship_class=ship_a.ship_class,
        rarity=result_rarity,
        grade=0,                     # le grade repart de zéro
        combat_xp=transferred_xp,
        base_stats=forged_stats,     # IMMUABLE après INSERT
        parent_ship_id=None,
        status="DOCKED",
        total_slots=total_slots,
        premium_slots=premium_slots,
        created_at=now,
    )
    db.add(new_ship)

    # --- Marquage des parents (SCRAPPED = consommés) ---
    ship_a.status = "SCRAPPED"
    ship_b.status = "SCRAPPED"
    db.add(ship_a)
    db.add(ship_b)

    # --- Mise à jour forge_queue ---
    forge_entry.result_ship_id = new_ship.id
    db.add(forge_entry)

    # --- Redis : progression 100 % ---
    await _store_forge_status(
        forge_entry.id,
        forge_entry.completed_at,
        progress_pct=100,
        result_ship_id=new_ship.id,
    )

    # --- Invalidation cache hangar du joueur ---
    await invalidate_hangar_cache(forge_entry.player_id)

    # --- Broadcast WS ---
    await publish_event(
        channel=f"player:{forge_entry.player_id}",
        event={
            "type": "forge.complete",
            "data": {
                "forge_id":     str(forge_entry.id),
                "new_ship_id":  str(new_ship.id),
                "rarity":       result_rarity,
                "base_stats":   forged_stats,
                "combat_xp":    transferred_xp,
                "slots_total":  total_slots,
                "slots_premium":premium_slots,
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
    import json
    raw = await r.get(f"forge:{forge_id}:status")
    return json.loads(raw) if raw else None


async def compute_live_progress(forge_id: uuid.UUID, completed_at: datetime) -> dict[str, Any]:
    """
    Calcule la progression en temps réel d'une forge active.
    Utilisé pour mettre à jour le cache Redis toutes les 60 s.
    """
    now = datetime.now(UTC)
    total_duration = FORGE_DURATION_HOURS * 3600
    elapsed = (now - (completed_at - timedelta(hours=FORGE_DURATION_HOURS))).total_seconds()
    progress_pct = min(100, int((elapsed / total_duration) * 100))
    eta_seconds = max(0, int((completed_at.replace(tzinfo=UTC) - now).total_seconds()))

    return {
        "forge_id":    str(forge_id),
        "progress_pct": progress_pct,
        "eta_seconds":  eta_seconds,
        "completed_at": completed_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Job APScheduler — appelé depuis app/tasks/forge_tick.py
# ---------------------------------------------------------------------------

async def run_forge_tick(db: AsyncSession) -> None:
    """
    Tâche périodique (toutes les 60 s via APScheduler).

    Trouve toutes les forges dont completed_at <= now() et les finalise.
    Chaque finalisation est dans sa propre transaction pour isoler les erreurs.

    Appelé depuis :
        app/tasks/forge_tick.py → scheduler.add_job(run_forge_tick, "interval", seconds=60)
    """
    now = datetime.now(UTC)

    result = await db.execute(
        select(ForgeQueue).where(
            and_(
                ForgeQueue.completed_at <= now,
                ForgeQueue.result_ship_id.is_(None),   # pas encore finalisé
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
            # Log l'erreur sans crasher les autres forges
            import logging
            logging.getLogger(__name__).error(
                "Erreur finalisation forge %s : %s", forge_entry.id, exc, exc_info=True
            )


# ---------------------------------------------------------------------------
# Helpers privés
# ---------------------------------------------------------------------------

def _merge_best_stats(
    stats_a: dict[str, float],
    stats_b: dict[str, float],
) -> dict[str, float]:
    """
    Prend le maximum de chaque stat entre les deux vaisseaux parents (GDD §5b).
    Les clés doivent être identiques (même ship_class garantit la structure).
    """
    merged: dict[str, float] = {}
    all_keys = set(stats_a) | set(stats_b)
    for key in all_keys:
        merged[key] = max(stats_a.get(key, 0), stats_b.get(key, 0))
    return merged


def _check_forge_resources(
    player: Player,
    cost: dict[str, float],
    db: AsyncSession,
) -> None:
    """
    Vérifie et déduit les ressources de forge (3× coût de construction).

    Raises:
        HTTPException 402 : ressources insuffisantes.
    """
    needed_metal    = cost.get("metal", 0)
    needed_crystal  = cost.get("crystal", 0)
    needed_deut     = cost.get("deuterium", 0)

    if (
        player.metal    < needed_metal
        or player.crystal < needed_crystal
        or player.deuterium < needed_deut
    ):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                f"Ressources insuffisantes pour la Forge. "
                f"Requis : métal={needed_metal:.0f}, cristal={needed_crystal:.0f}, "
                f"deutérium={needed_deut:.0f}. "
                f"Disponible : métal={player.metal:.0f}, cristal={player.crystal:.0f}, "
                f"deutérium={player.deuterium:.0f}."
            ),
        )

    player.metal     -= needed_metal
    player.crystal   -= needed_crystal
    player.deuterium -= needed_deut
    db.add(player)


async def _store_forge_status(
    forge_id: uuid.UUID,
    completed_at: datetime,
    progress_pct: int,
    result_ship_id: uuid.UUID | None = None,
) -> None:
    """Écrit le statut de forge dans Redis."""
    import json
    r: aioredis.Redis = get_redis()
    payload: dict[str, Any] = {
        "forge_id":      str(forge_id),
        "completed_at":  completed_at.isoformat(),
        "progress_pct":  progress_pct,
        "eta_seconds":   max(0, int((completed_at.replace(tzinfo=UTC) - datetime.now(UTC)).total_seconds())),
    }
    if result_ship_id is not None:
        payload["result_ship_id"] = str(result_ship_id)

    await r.setex(f"forge:{forge_id}:status", _FORGE_STATUS_TTL, json.dumps(payload))
