"""
app/services/ship_stats_service.py
Agent 5 — Développeur Backend

Responsabilité : Calcul et mise en cache de current_stats.

current_stats = base_stats
              + bonus modules (affinité de classe incluse)
              + bonus grade passif
              → plafonné à +150 % par stat (cap GDD §3)

C'est la SEULE fonction qui produit current_stats. Elle n'est jamais
appelée côté client — le client reçoit le résultat sérialisé.

Stratégie Redis (Agent 3) :
  clé   : ship:{ship_id}:stats
  TTL   : 300 s (5 min)
  invalidation : PUT /modules, grade_up, fin de forge, démolition
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_client import get_redis
from app.models.models import Ship, ShipModule


# Slots par rareté — copie locale pour éviter l'import circulaire
_RARITY_SLOTS: dict[str, tuple[int, int]] = {
    "COMMON":    (2, 0),
    "UNCOMMON":  (3, 0),
    "RARE":      (4, 1),
    "EPIC":      (5, 2),
    "LEGENDARY": (6, 3),
}

def _enum_val(v) -> str:
    return v.value if hasattr(v, 'value') else str(v)

# ---------------------------------------------------------------------------
# Constantes GDD
# ---------------------------------------------------------------------------

# Cap absolu par stat : +150 % de la base_stat (GDD §3)
_STAT_CAP_RATIO = 1.50

# Bonus passif par grade (GDD §4) — multiplicateur appliqué à toutes les stats
_GRADE_BONUS: dict[int, float] = {
    0: 0.00,
    1: 0.05,   # +5 %
    2: 0.10,   # +10 %
    3: 0.15,   # +15 %
    4: 0.22,   # +22 %
    5: 0.30,   # +30 %
}

# Régénération de bouclier par round accordée par les grades (combat only)
GRADE_SHIELD_REGEN: dict[int, float] = {
    0: 0.00,
    1: 0.00,
    2: 0.00,
    3: 0.02,   # +2 % bouclier/round (GDD §4 Grade 3)
    4: 0.02,
    5: 0.02,
}

# Bonus furtivité Grade 5 (GDD §4)
GRADE_5_STEALTH_BONUS = 10.0   # +10 % absolu

# Boost de module par niveau, sans affinité (GDD §3)
_MODULE_BOOST: dict[int, float] = {
    1: 0.08,
    2: 0.14,
    3: 0.22,
    4: 0.32,
    5: 0.44,
}

# Bonus d'affinité : le boost est multiplié par ce facteur quand la classe correspond
_AFFINITY_MULT = 1.15   # 0.08 × 1.15 = 0.092 → +9.2 % (GDD §3)

# Mapping module_type → stat boostée + classe d'affinité (GDD §3)
_MODULE_EFFECT: dict[str, dict[str, str]] = {
    "PROPELLER": {"stat": "speed",        "affinity_class": "EXPLORATION"},
    "ARMOR":     {"stat": "hull",         "affinity_class": "DEFENSE"},
    "CANNON":    {"stat": "dps",          "affinity_class": "ATTACK"},
    "EMITTER":   {"stat": "support_aura", "affinity_class": "SUPPORT"},
    "SHIELD":    {"stat": "shield",       "affinity_class": "DEFENSE"},
    "CARGO":     {"stat": "cargo",        "affinity_class": "EXPLORATION"},
}

# Niveaux requis pour les slots premium (GDD §3)
_PREMIUM_REQUIRED_LEVELS = {4, 5}

# TTL Redis pour current_stats
_STATS_TTL = 300        # secondes
_HANGAR_TTL = 120       # secondes pour la liste hangar


# ---------------------------------------------------------------------------
# Clés Redis
# ---------------------------------------------------------------------------

def _stats_key(ship_id: uuid.UUID) -> str:
    return f"ship:{ship_id}:stats"

def _hangar_key(player_id: uuid.UUID) -> str:
    return f"player:{player_id}:hangar"


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

async def get_current_stats(
    ship_id: uuid.UUID,
    db: AsyncSession,
) -> dict[str, Any]:
    """
    Retourne current_stats pour un vaisseau.

    Flux :
      1. Lecture Redis → retour immédiat si présent (cache hit)
      2. Sinon : charge Ship + ShipModules depuis PostgreSQL
      3. Calcule current_stats
      4. Stocke dans Redis (TTL 5 min)
      5. Retourne le résultat

    C'est le seul endroit où current_stats est calculé (Agent 3, décision 2).

    Returns:
        Dict avec les clés : hull, shield, dps, speed, cargo, stealth,
        support_aura, grade_bonus_pct, shield_regen_per_round,
        cap_reached (liste des stats plafonnées), slots_total, slots_premium.

    Raises:
        ValueError : vaisseau introuvable.
    """
    r: aioredis.Redis = get_redis()
    key = _stats_key(ship_id)

    # --- Cache hit ---
    cached = await r.get(key)
    if cached:
        return json.loads(cached)

    # --- Cache miss : calcul complet ---
    ship, modules = await _load_ship_with_modules(ship_id, db)
    stats = _compute_current_stats(ship, modules)

    # Écriture Redis
    await r.setex(key, _STATS_TTL, json.dumps(stats))

    return stats


async def invalidate_ship_cache(ship_id: uuid.UUID) -> None:
    """
    Invalide le cache current_stats d'un vaisseau.
    À appeler après : PUT /modules, grade_up, fin de forge.
    """
    r: aioredis.Redis = get_redis()
    await r.delete(_stats_key(ship_id))


async def invalidate_hangar_cache(player_id: uuid.UUID) -> None:
    """
    Invalide le cache liste-hangar d'un joueur.
    À appeler après : build, demolish, forge start/complete.
    """
    r: aioredis.Redis = get_redis()
    await r.delete(_hangar_key(player_id))


async def compute_and_store_stats(
    ship: Ship,
    modules: list[ShipModule],
) -> dict[str, Any]:
    """
    Calcule et stocke directement dans Redis (sans passer par get_current_stats).
    Utilisé après une mutation (PUT /modules, grade_up) pour s'assurer
    que le cache est frais avant de retourner la réponse au client.

    Returns:
        current_stats calculé (identique à ce qui est mis en cache).
    """
    r: aioredis.Redis = get_redis()
    stats = _compute_current_stats(ship, modules)
    await r.setex(_stats_key(ship.id), _STATS_TTL, json.dumps(stats))
    return stats


def validate_module_slot(
    ship: Ship,
    slot_index: int,
    module_level: int,
) -> tuple[bool, str]:
    """
    Valide qu'un module peut être installé dans un slot donné.
    Retourne (is_valid, error_message).

    Règles (GDD §3 + Agent 3 validation serveur) :
      - slot_index doit exister (< total_slots)
      - Les modules level IV/V ne vont que dans des slots premium
        (index ≥ total_slots - premium_slots)
    """
    if slot_index < 0 or slot_index >= ship.total_slots:
        return False, (
            f"Slot {slot_index} invalide pour ce vaisseau "
            f"({ship.total_slots} slots disponibles)."
        )

    premium_start = ship.total_slots - ship.premium_slots
    is_premium_slot = slot_index >= premium_start

    if module_level in _PREMIUM_REQUIRED_LEVELS and not is_premium_slot:
        return False, (
            f"Les modules de niveau {module_level} nécessitent un slot premium. "
            f"Les slots premium commencent à l'index {premium_start} "
            f"pour ce vaisseau ({ship.rarity})."
        )

    return True, ""


# ---------------------------------------------------------------------------
# Calcul interne
# ---------------------------------------------------------------------------

def _compute_current_stats(
    ship: Ship,
    modules: list[ShipModule],
) -> dict[str, Any]:
    """
    Calcule current_stats à partir de base_stats + modules + grade.

    Algorithme :
      1. Partir de base_stats (immuable)
      2. Appliquer bonus grade (% uniforme sur toutes stats numériques)
      3. Pour chaque module : calculer le boost (avec affinité éventuelle)
         accumuler par stat
      4. Plafonner chaque stat à base × (1 + 1.50)
      5. Ajouter les champs métadonnées (cap_reached, grade_bonus_pct…)

    Note : le cap +150 % est calculé par rapport à la base_stat brute,
    pas par rapport à la stat après grade. Le grade s'applique en premier
    puis les modules s'ajoutent dessus — mais le cap est absolu sur la base.
    """
    base: dict[str, float] = ship.base_stats
    grade = ship.grade

    # --- Étape 1 : bonus grade (appliqué à toutes les stats numériques) ---
    grade_mult = _GRADE_BONUS.get(grade, 0.0)
    # Stats après grade (avant modules)
    after_grade: dict[str, float] = {}
    for stat, val in base.items():
        after_grade[stat] = val * (1.0 + grade_mult)

    # Bonus spécial Grade 5 — furtivité +10 % absolu (GDD §4)
    if grade == 5:
        after_grade["stealth"] = min(100.0, after_grade.get("stealth", 0.0) + GRADE_5_STEALTH_BONUS)

    # --- Étape 2 : accumulation des boosts de modules par stat ---
    # On accumule les ratios de boost (pas les valeurs absolues) avant de plafonner
    module_boost_ratio: dict[str, float] = {s: 0.0 for s in base}
    modules_detail: list[dict] = []

    for mod in modules:
        if mod.module_type not in _MODULE_EFFECT:
            continue   # module_type inconnu — on ignore (defensive)

        effect = _MODULE_EFFECT[mod.module_type]
        stat_name = effect["stat"]
        affinity_class = effect["affinity_class"]

        base_boost = _MODULE_BOOST.get(mod.level, 0.0)
        has_affinity = (_enum_val(ship.class_) == affinity_class)
        effective_boost = base_boost * (_AFFINITY_MULT if has_affinity else 1.0)

        module_boost_ratio[stat_name] = module_boost_ratio.get(stat_name, 0.0) + effective_boost

        modules_detail.append({
            "slot":           mod.slot_index,
            "type":           mod.module_type,
            "level":          mod.level,
            "affinity_bonus": has_affinity,
            "boost_applied":  round(effective_boost * 100, 2),  # en %
        })

    # --- Étape 3 : application des boosts + plafonnement ---
    final: dict[str, float] = {}
    cap_reached: list[str] = []

    for stat, base_val in base.items():
        after_grade_val = after_grade[stat]
        boost_ratio = module_boost_ratio.get(stat, 0.0)

        # Valeur cible = après_grade + boost_modules (appliqué sur la base pour cohérence)
        # Formule : base × grade_mult + base × boost_ratio
        # → on ajoute les deux contributions au-dessus de base
        module_add = base_val * boost_ratio
        target = after_grade_val + module_add

        # Cap absolu : ne peut pas dépasser base × (1 + 150 %)
        cap_value = base_val * (1.0 + _STAT_CAP_RATIO)
        if target > cap_value:
            target = cap_value
            cap_reached.append(stat)

        # Arrondi cohérent avec generate_base_stats
        if stat == "speed":
            final[stat] = round(max(0.0, target), 1)
        elif stat in ("stealth", "support_aura"):
            final[stat] = round(max(0.0, target), 2)
        else:
            final[stat] = int(max(0, round(target)))

    # --- Résultat enrichi ---
    return {
        # Stats de jeu
        "hull":           final.get("hull", 0),
        "shield":         final.get("shield", 0),
        "dps":            final.get("dps", 0),
        "speed":          final.get("speed", 0.0),
        "cargo":          final.get("cargo", 0),
        "stealth":        final.get("stealth", 0.0),
        "support_aura":   final.get("support_aura", 0.0),
        # Métadonnées utiles pour le combat engine et l'UI
        "grade":                   grade,
        "grade_bonus_pct":         round(grade_mult * 100, 1),
        "shield_regen_per_round":  GRADE_SHIELD_REGEN.get(grade, 0.0),
        "cap_reached":             cap_reached,
        "modules":                 modules_detail,
        # Slots disponibles (total et premium, pour l'UI du hangar)
        "slots_total":             _RARITY_SLOTS.get(_enum_val(ship.rarity), (2, 0))[0],
        "slots_premium":           _RARITY_SLOTS.get(_enum_val(ship.rarity), (2, 0))[1],
    }


# ---------------------------------------------------------------------------
# Helpers BDD
# ---------------------------------------------------------------------------

async def _load_ship_with_modules(
    ship_id: uuid.UUID,
    db: AsyncSession,
) -> tuple[Ship, list[ShipModule]]:
    """
    Charge le vaisseau et ses modules depuis PostgreSQL.

    Raises:
        ValueError : vaisseau introuvable.
    """
    ship_result = await db.execute(select(Ship).where(Ship.id == ship_id))
    ship: Ship | None = ship_result.scalar_one_or_none()
    if ship is None:
        raise ValueError(f"Vaisseau {ship_id} introuvable.")

    mods_result = await db.execute(
        select(ShipModule)
        .where(ShipModule.ship_id == ship_id)
        .order_by(ShipModule.slot_index)
    )
    modules: list[ShipModule] = list(mods_result.scalars().all())

    return ship, modules
