"""
app/services/module_inventory_service.py
Phase 1 — Inventaire de modules, artisanat, boîtes de butin.

Responsabilités :
  - Créer / lister les modules dans l'inventaire joueur
  - Installer depuis l'inventaire → ShipModule
  - Désinstaller → retour inventaire avec décrémentation des charges
  - Artisanat 3:1 avec coût en ressources
  - Créer / ouvrir les LootCrates
"""
from __future__ import annotations

import random
import uuid
from datetime import datetime, UTC
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    LootCrate,
    LootCrateType,
    ModuleObtainedFrom,
    Planet,
    Player,
    PlayerModule,
    Ship,
    ShipModule,
    ShipStatus,
)
from app.services.ship_stats_service import (
    compute_and_store_stats,
    invalidate_ship_cache,
    validate_module_slot,
    _load_ship_with_modules,
)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

# Charges initiales par niveau
_INITIAL_CHARGES: dict[int, int] = {1: 5, 2: 4, 3: 4, 4: 3, 5: 2}

# Ressource principale par type de module
_MODULE_PRIMARY_RESOURCE: dict[str, str] = {
    "CANNON":    "crystal",
    "SHIELD":    "crystal",
    "ARMOR":     "metal",
    "PROPELLER": "metal",
    "EMITTER":   "deuterium",
    "CARGO":     "deuterium",
}

# Ressource secondaire (l'autre grande ressource)
_MODULE_SECONDARY_RESOURCE: dict[str, str] = {
    "CANNON":    "metal",
    "SHIELD":    "metal",
    "ARMOR":     "crystal",
    "PROPELLER": "crystal",
    "EMITTER":   "metal",
    "CARGO":     "crystal",
}

# Coût d'artisanat (result_level) → (primary, secondary, deuterium)
_CRAFT_COST: dict[int, tuple[int, int, int]] = {
    2: (500,    150,     0),
    3: (1_500,  500,     0),
    4: (4_500,  1_500,  500),
    5: (12_000, 4_000, 1_500),
}

# Définitions des traits
_TRAITS: dict[str, dict[str, Any]] = {
    "battle_hardened": {"boost_multiplier": 1.10, "min_level": 1},
    "overclocked":     {"boost_multiplier": 1.15, "charge_penalty": 1, "min_level": 1},
    "pristine":        {"charge_bonus": 2,         "min_level": 1},
    "resonant":        {"second_affinity": True,   "min_level": 1},
    "lightweight":     {"boost_multiplier": 1.05, "speed_bonus_abs": 0.03, "min_level": 1},
    "military_grade":  {"boost_multiplier": 1.12, "min_level": 3},
}

# Pools de traits par source
_TRAIT_POOL: dict[str, list[str]] = {
    "COMBAT_LOOT": ["battle_hardened", "military_grade"],
    "EXPEDITION":  ["pristine", "resonant", "lightweight", "overclocked"],
    "CRAFTED":     ["overclocked", "resonant", "military_grade"],
}

# Stats de malus possibles pour les modules corrompus
_CORRUPTION_MALUS_STATS = ["speed", "shield", "cargo", "stealth"]
_CORRUPTION_MALUS_RANGE  = (0.10, 0.25)  # -10% à -25% de la stat

# Tables de loot par type de caisse
_LOOT_TABLE: dict[str, dict[str, Any]] = {
    "STANDARD": {
        "module_chance": 0.70,
        "corrupted_chance": 0.10,   # parmi les modules tirés
        "level_range": (1, 2),
        "trait_chance": 0.05,
        "shard_range": (3, 6),
        "empty_chance": 0.05,
    },
    "PREMIUM": {
        "module_chance": 0.85,
        "corrupted_chance": 0.08,
        "level_range": (2, 3),
        "trait_chance": 0.15,
        "shard_range": (5, 10),
        "empty_chance": 0.00,
    },
    "ADMIRAL": {
        "module_chance": 1.00,
        "corrupted_chance": 0.05,
        "level_range": (4, 5),
        "trait_chance": 0.30,
        "shard_range": (15, 25),
        "empty_chance": 0.00,
    },
}

# Seuil de shards pour obtenir un Trait Crystal
SHARDS_PER_TRAIT_CRYSTAL = 15


# ---------------------------------------------------------------------------
# Helpers internes
# ---------------------------------------------------------------------------

def _base_charges(level: int, trait: str | None) -> int:
    charges = _INITIAL_CHARGES[level]
    if trait == "pristine":
        charges += 2
    elif trait == "overclocked":
        charges = max(1, charges - 1)
    return charges


def _roll_trait(source: str, module_level: int) -> str | None:
    pool = [
        t for t in _TRAIT_POOL.get(source, [])
        if _TRAITS[t].get("min_level", 1) <= module_level
    ]
    return random.choice(pool) if pool else None


def _trait_value(trait: str) -> float | None:
    t = _TRAITS.get(trait, {})
    return t.get("boost_multiplier") or t.get("charge_bonus") or t.get("speed_bonus_abs")


def _roll_corruption() -> tuple[str, float]:
    stat  = random.choice(_CORRUPTION_MALUS_STATS)
    value = round(random.uniform(*_CORRUPTION_MALUS_RANGE), 2)
    return stat, value


# ---------------------------------------------------------------------------
# API publique — inventaire
# ---------------------------------------------------------------------------

async def get_inventory(player_id: UUID, db: AsyncSession) -> list[PlayerModule]:
    """Retourne tous les modules du joueur (y compris détruits pour historique)."""
    result = await db.execute(
        select(PlayerModule)
        .where(PlayerModule.player_id == player_id)
        .order_by(PlayerModule.obtained_at.desc())
    )
    return list(result.scalars().all())


async def create_module(
    player_id: UUID,
    module_type: str,
    level: int,
    obtained_from: str,
    *,
    trait: str | None = None,
    is_corrupted: bool = False,
    corruption_malus_stat: str | None = None,
    corruption_malus_value: float | None = None,
    memory_ship_name: str | None = None,
    memory_battle_ref: str | None = None,
    db: AsyncSession,
) -> PlayerModule:
    """Crée un module dans l'inventaire du joueur avec les charges initiales calculées."""
    charges = _base_charges(level, trait)
    t_value = _trait_value(trait) if trait else None

    mod = PlayerModule(
        id=uuid.uuid4(),
        player_id=player_id,
        module_type=module_type,
        level=level,
        trait=trait,
        trait_value=t_value,
        trait_slots_used=1 if trait else 0,
        is_corrupted=is_corrupted,
        corruption_malus_stat=corruption_malus_stat,
        corruption_malus_value=corruption_malus_value,
        reinstall_charges=charges,
        is_destroyed=False,
        obtained_from=obtained_from,
        memory_ship_name=memory_ship_name,
        memory_battle_ref=memory_battle_ref,
        obtained_at=datetime.now(UTC),
    )
    db.add(mod)
    return mod


# ---------------------------------------------------------------------------
# API publique — installation / désinstallation
# ---------------------------------------------------------------------------

async def install_module(
    player_id: UUID,
    module_id: UUID,
    ship_id: UUID,
    slot_index: int,
    db: AsyncSession,
) -> dict[str, Any]:
    """
    Installe un module depuis l'inventaire sur un slot de vaisseau.
    Si le slot est déjà occupé, l'ancien module est renvoyé dans l'inventaire (-1 charge).
    Retourne current_stats recalculées.
    """
    # Charger le module d'inventaire
    pm_result = await db.execute(
        select(PlayerModule).where(
            PlayerModule.id == module_id,
            PlayerModule.player_id == player_id,
        )
    )
    pm: PlayerModule | None = pm_result.scalar_one_or_none()
    if pm is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Module introuvable dans votre inventaire.")
    if pm.is_destroyed:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Ce module est détruit et ne peut plus être installé.")

    # Charger le vaisseau
    ship_result = await db.execute(select(Ship).where(Ship.id == ship_id))
    ship: Ship | None = ship_result.scalar_one_or_none()
    if ship is None or ship.owner_id != player_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Vaisseau introuvable.")
    if ship.status == ShipStatus.IN_FORGE:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Impossible de modifier un vaisseau en cours de forge.")

    # Valider le slot
    is_valid, err = validate_module_slot(ship, slot_index, pm.level)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=err)

    # Si slot occupé → désinstaller l'ancien d'abord
    existing = await db.execute(
        select(ShipModule).where(
            ShipModule.ship_id == ship_id,
            ShipModule.slot_index == slot_index,
        )
    )
    old_sm: ShipModule | None = existing.scalar_one_or_none()
    if old_sm is not None:
        await _return_to_inventory(old_sm, db)

    # Créer le nouveau ShipModule
    sm = ShipModule(
        id=uuid.uuid4(),
        ship_id=ship_id,
        slot_index=slot_index,
        module_type=pm.module_type,
        level=pm.level,
        affinity_bonus=False,  # recalculé dans compute_and_store_stats
        player_module_id=pm.id,
    )
    db.add(sm)

    # Flush explicite pour que le SELECT suivant voie le nouveau ShipModule
    await db.flush()

    await invalidate_ship_cache(ship_id)
    _, modules = await _load_ship_with_modules(ship_id, db)
    current_stats = await compute_and_store_stats(ship, modules)
    return current_stats


async def uninstall_module(
    player_id: UUID,
    ship_id: UUID,
    slot_index: int,
    db: AsyncSession,
) -> tuple[bool, bool]:
    """
    Retire un module d'un slot → retour inventaire avec -1 charge.
    Retourne (found: bool, destroyed: bool).
    destroyed=True si les charges tombent à 0 (module détruit mais gardé en historique).
    """
    ship_result = await db.execute(select(Ship).where(Ship.id == ship_id))
    ship: Ship | None = ship_result.scalar_one_or_none()
    if ship is None or ship.owner_id != player_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Vaisseau introuvable.")

    sm_result = await db.execute(
        select(ShipModule).where(
            ShipModule.ship_id == ship_id,
            ShipModule.slot_index == slot_index,
        )
    )
    sm: ShipModule | None = sm_result.scalar_one_or_none()
    if sm is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Aucun module dans le slot {slot_index}.")

    destroyed = await _return_to_inventory(sm, db)
    await invalidate_ship_cache(ship_id)
    return True, destroyed


async def _return_to_inventory(sm: ShipModule, db: AsyncSession) -> bool:
    """
    Supprime le ShipModule et décrémente les charges du PlayerModule associé.
    Retourne True si le module a été détruit (charges → 0).
    """
    destroyed = False
    if sm.player_module_id is not None:
        pm_result = await db.execute(
            select(PlayerModule).where(PlayerModule.id == sm.player_module_id)
        )
        pm: PlayerModule | None = pm_result.scalar_one_or_none()
        if pm is not None:
            pm.reinstall_charges = max(0, pm.reinstall_charges - 1)
            if pm.reinstall_charges == 0:
                pm.is_destroyed = True
                destroyed = True
            db.add(pm)

    await db.delete(sm)
    return destroyed


# ---------------------------------------------------------------------------
# API publique — artisanat
# ---------------------------------------------------------------------------

async def craft_module(
    player_id: UUID,
    source_ids: list[UUID],
    planet_id: UUID,
    db: AsyncSession,
) -> PlayerModule:
    """
    Fusionne 3 modules identiques (même type + même niveau) → 1 module niveau+1.
    Déduit les ressources de la planète spécifiée.
    Règle : au plus 1 trait hérité (celui du "meilleur" des 3 sources, 30% de chance).
    """
    if len(source_ids) != 3:
        raise HTTPException(status_code=422, detail="Il faut exactement 3 modules.")
    if len(set(source_ids)) != 3:
        raise HTTPException(status_code=422, detail="Les 3 modules doivent être distincts.")

    # Charger les 3 modules
    mods_result = await db.execute(
        select(PlayerModule).where(
            PlayerModule.id.in_(source_ids),
            PlayerModule.player_id == player_id,
        )
    )
    mods: list[PlayerModule] = list(mods_result.scalars().all())
    if len(mods) != 3:
        raise HTTPException(status_code=404,
                            detail="Un ou plusieurs modules sont introuvables dans votre inventaire.")

    # Vérifier qu'aucun n'est détruit ou équipé
    for m in mods:
        if m.is_destroyed:
            raise HTTPException(status_code=409,
                                detail=f"Le module {m.id} est détruit.")

    # Vérifier type + niveau identiques
    types  = {m.module_type for m in mods}
    levels = {m.level      for m in mods}
    if len(types) > 1:
        raise HTTPException(status_code=422, detail="Les 3 modules doivent être du même type.")
    if len(levels) > 1:
        raise HTTPException(status_code=422, detail="Les 3 modules doivent être du même niveau.")

    module_type  = mods[0].module_type
    source_level = mods[0].level
    result_level = source_level + 1

    if result_level > 5:
        raise HTTPException(status_code=422,
                            detail="Les modules de niveau V ne peuvent pas être améliorés.")

    # Vérifier et déduire les ressources sur la planète
    planet_result = await db.execute(
        select(Planet).where(
            Planet.id == planet_id,
            Planet.owner_id == player_id,
        )
    )
    planet: Planet | None = planet_result.scalar_one_or_none()
    if planet is None:
        raise HTTPException(status_code=404, detail="Planète introuvable.")

    cost_primary, cost_secondary, cost_deut = _CRAFT_COST[result_level]
    primary_res   = _MODULE_PRIMARY_RESOURCE[module_type]
    secondary_res = _MODULE_SECONDARY_RESOURCE[module_type]

    def _has_enough(res: str, cost: int) -> bool:
        return float(getattr(planet, res if res != "deuterium" else "deuterium")) >= cost

    if cost_primary   > 0 and not _has_enough(primary_res,   cost_primary):
        raise HTTPException(status_code=402,
                            detail=f"Ressources insuffisantes ({primary_res}).")
    if cost_secondary > 0 and not _has_enough(secondary_res, cost_secondary):
        raise HTTPException(status_code=402,
                            detail=f"Ressources insuffisantes ({secondary_res}).")
    if cost_deut > 0 and float(planet.deuterium) < cost_deut:
        raise HTTPException(status_code=402,
                            detail="Ressources insuffisantes (deutérium).")

    # Déduire
    def _deduct(res: str, amount: int) -> None:
        if amount <= 0:
            return
        attr = res  # "metal" / "crystal" / "deuterium"
        setattr(planet, attr, float(getattr(planet, attr)) - amount)

    _deduct(primary_res,   cost_primary)
    _deduct(secondary_res, cost_secondary)
    if cost_deut > 0:
        _deduct("deuterium", cost_deut)
    db.add(planet)

    # Héritage de trait (30% — on prend le module avec le trait le plus rare)
    inherited_trait: str | None = None
    if random.random() < 0.30:
        candidates = [m for m in mods if m.trait is not None]
        if candidates:
            inherited_trait = random.choice(candidates).trait

    # Marquer les 3 sources comme détruits (elles sont consommées)
    for m in mods:
        m.is_destroyed = True
        m.reinstall_charges = 0
        db.add(m)

    # Créer le module résultant
    result_mod = await create_module(
        player_id=player_id,
        module_type=module_type,
        level=result_level,
        obtained_from=ModuleObtainedFrom.CRAFTED.value,
        trait=inherited_trait,
        db=db,
    )
    return result_mod


# ---------------------------------------------------------------------------
# API publique — loot crates
# ---------------------------------------------------------------------------

async def create_loot_crate(
    player_id: UUID,
    crate_type: str,
    source: str,
    *,
    source_ship_name: str | None = None,
    source_battle_id: str | None = None,
    db: AsyncSession,
) -> LootCrate:
    """Crée une boîte de butin fermée dans l'inventaire du joueur."""
    crate = LootCrate(
        id=uuid.uuid4(),
        player_id=player_id,
        crate_type=crate_type,
        source=source,
        source_ship_name=source_ship_name,
        source_battle_id=source_battle_id,
    )
    db.add(crate)
    return crate


async def open_loot_crate(
    player_id: UUID,
    crate_id: UUID,
    db: AsyncSession,
) -> dict[str, Any]:
    """
    Ouvre une caisse de butin.
    Calcule le loot, crée le PlayerModule si nécessaire, met à jour les shards joueur.
    Retourne {"module": PlayerModule | None, "shards": int, "empty": bool}
    """
    crate_result = await db.execute(
        select(LootCrate).where(
            LootCrate.id == crate_id,
            LootCrate.player_id == player_id,
        )
    )
    crate: LootCrate | None = crate_result.scalar_one_or_none()
    if crate is None:
        raise HTTPException(status_code=404, detail="Caisse introuvable.")
    if crate.opened:
        raise HTTPException(status_code=409, detail="Cette caisse a déjà été ouverte.")

    table = _LOOT_TABLE.get(crate.crate_type, _LOOT_TABLE["STANDARD"])
    roll  = random.random()
    result_module: PlayerModule | None = None
    shards = 0
    empty  = False

    # Shards toujours donnés (indépendamment du module)
    shards = random.randint(*table["shard_range"])

    if table["empty_chance"] > 0 and roll < table["empty_chance"]:
        empty  = True
        shards = max(1, shards // 2)   # moitié de shards si caisse vide
    elif roll < table["module_chance"]:
        # Tirer un module
        lvl_min, lvl_max = table["level_range"]
        level       = random.randint(lvl_min, lvl_max)
        module_type = random.choice(list(_MODULE_PRIMARY_RESOURCE.keys()))

        is_corrupted  = False
        malus_stat:  str | None = None
        malus_value: float | None = None

        if random.random() < table["corrupted_chance"]:
            is_corrupted = True
            malus_stat, malus_value = _roll_corruption()

        trait: str | None = None
        if random.random() < table["trait_chance"]:
            src  = crate.source if crate.source in _TRAIT_POOL else "EXPEDITION"
            if crate.source == "COMBAT":
                src = "COMBAT_LOOT"
            trait = _roll_trait(src, level)

        result_module = await create_module(
            player_id=player_id,
            module_type=module_type,
            level=level,
            obtained_from=(
                ModuleObtainedFrom.COMBAT_LOOT.value
                if crate.source == "COMBAT"
                else ModuleObtainedFrom.EXPEDITION.value
            ),
            trait=trait,
            is_corrupted=is_corrupted,
            corruption_malus_stat=malus_stat,
            corruption_malus_value=malus_value,
            memory_ship_name=crate.source_ship_name,
            memory_battle_ref=crate.source_battle_id,
            db=db,
        )

    # Ajouter les shards au joueur
    player_result = await db.execute(select(Player).where(Player.id == player_id))
    player: Player = player_result.scalar_one()
    shards_dict: dict[str, int] = dict(player.module_shards or {})
    if result_module:
        key = result_module.module_type
    else:
        key = random.choice(list(_MODULE_PRIMARY_RESOURCE.keys()))
    shards_dict[key] = shards_dict.get(key, 0) + shards
    player.module_shards = shards_dict
    db.add(player)

    # Marquer la caisse comme ouverte
    crate.opened = True
    crate.opened_at = datetime.now(UTC)
    if result_module:
        crate.result_module_id = result_module.id
    crate.shards_awarded = shards
    db.add(crate)

    # Retourner les shards gagnés sous forme de dict {type: quantité}
    shards_gained: dict[str, int] = {key: shards}
    return {"module": result_module, "shards": shards_gained, "empty": empty}


async def get_shard_counts(player_id: UUID, db: AsyncSession) -> dict[str, int]:
    """Retourne le nombre de shards par type de module pour le joueur."""
    player_result = await db.execute(select(Player).where(Player.id == player_id))
    player: Player = player_result.scalar_one()
    base = {t: 0 for t in _MODULE_PRIMARY_RESOURCE}
    base.update(player.module_shards or {})
    return base
