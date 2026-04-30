"""
app/services/ship_build_service.py
Agent 5 — Développeur Backend

Responsabilité : Fabrication de vaisseaux.
  - Tirage RNG pondéré de la rareté via secrets.SystemRandom (non prédictible)
  - Génération des base_stats dans la fourchette GDD §2
  - Application optionnelle du Pedigree (Grade ≥ 3, +5% meilleure stat du parent)
  - Écriture atomique en base (SELECT FOR UPDATE sur le joueur)
  - Invalidation du cache hangar Redis après INSERT

Règle absolue (Agent 3) : base_stats est généré UNE SEULE FOIS ici et jamais retouché.
Le trigger PostgreSQL BEFORE UPDATE garantit l'immuabilité côté BDD.
"""

from __future__ import annotations
import math
import secrets
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.tasks.resource_tick import _get_building_level
from app.models.models import ForgeQueue, Planet, Player, Ship
from app.services.ship_stats_service import invalidate_hangar_cache

# ---------------------------------------------------------------------------
# Tables de configuration — fidèles au GDD §1 et §2
# ---------------------------------------------------------------------------

# Distribution cumulative : r = SystemRandom().random(), on trouve le premier
# threshold ≥ r. Ordre croissant obligatoire.
_RARITY_THRESHOLDS: list[tuple[str, float]] = [
    ("COMMON",    0.55),
    ("UNCOMMON",  0.82),
    ("RARE",      0.94),
    ("EPIC",      0.99),
    ("LEGENDARY", 1.00),
]

# Multiplicateur de stats par rareté (GDD §2)
_RARITY_MULT: dict[str, float] = {
    "COMMON":    1.00,
    "UNCOMMON":  1.25,
    "RARE":      1.55,
    "EPIC":      1.90,
    "LEGENDARY": 2.40,
}

# (total_slots, premium_slots) par rareté (GDD §2)
_RARITY_SLOTS: dict[str, tuple[int, int]] = {
    "COMMON":    (2, 0),
    "UNCOMMON":  (3, 0),
    "RARE":      (4, 1),
    "EPIC":      (5, 2),
    "LEGENDARY": (6, 3),
}

# Stats de base normalisées : Commun / grade 0 / sans modules (GDD §1)
_BASE_STATS_BY_CLASS: dict[str, dict[str, float]] = {
    "ATTACK": {
        "hull":         100.0,
        "shield":        20.0,
        "dps":           80.0,
        "speed":         45.0,
        "cargo":        200.0,
        "stealth":        0.0,
        "support_aura":   0.0,
    },
    "DEFENSE": {
        "hull":         350.0,
        "shield":       120.0,
        "dps":           15.0,
        "speed":         15.0,
        "cargo":        500.0,
        "stealth":        0.0,
        "support_aura":   0.0,
    },
    "SUPPORT": {
        "hull":         150.0,
        "shield":        40.0,
        "dps":            8.0,
        "speed":         30.0,
        "cargo":       1000.0,
        "stealth":        0.0,
        "support_aura":  15.0,
    },
    "EXPLORATION": {
        "hull":          80.0,
        "shield":        15.0,
        "dps":           12.0,
        "speed":         90.0,
        "cargo":       3000.0,
        "stealth":       25.0,
        "support_aura":   0.0,
    },
}

# Coûts de construction par ship_type (métal, cristal, deutérium)
# Sert aussi à calculer le coût ×3 de la Forge (GDD §5b).
SHIP_TYPE_BUILD_COST: dict[str, dict[str, float]] = {
    "frigate_attack":      {"metal": 3_000,  "crystal": 1_000,  "deuterium":     0},
    "frigate_defense":     {"metal": 6_000,  "crystal": 2_000,  "deuterium":     0},
    "frigate_support":     {"metal": 2_000,  "crystal": 2_000,  "deuterium":   500},
    "frigate_exploration": {"metal": 2_000,  "crystal": 1_000,  "deuterium": 1_000},
    "cruiser_attack":      {"metal": 20_000, "crystal": 7_000,  "deuterium": 2_000},
    "cruiser_defense":     {"metal": 30_000, "crystal": 10_000, "deuterium": 2_000},
}

# Mapping ship_type → ship_class enum
SHIP_TYPE_CLASS: dict[str, str] = {
    "frigate_attack":      "ATTACK",
    "frigate_defense":     "DEFENSE",
    "frigate_support":     "SUPPORT",
    "frigate_exploration": "EXPLORATION",
    "cruiser_attack":      "ATTACK",
    "cruiser_defense":     "DEFENSE",
}

SHIP_SHIPYARD_REQUIREMENTS: dict[str, int] = {
    "frigate_attack":      1,   # Chantier Niv.1
    "frigate_defense":     1,   # Chantier Niv.1
    "frigate_support":     1,   # Chantier Niv.1
    "frigate_exploration": 2,   # Chantier Niv.2
    "cruiser_attack":      4,   # Chantier Niv.4
    "cruiser_defense":     4,   # Chantier Niv.4
}

# Singleton SystemRandom — entropie OS, non seedable de l'extérieur (Agent 3 §4)
_srng = secrets.SystemRandom()


# ---------------------------------------------------------------------------
# Logique RNG pure (testable sans BDD)
# ---------------------------------------------------------------------------

def roll_rarity() -> str:
    """
    Tire une rareté selon la distribution cumulative du GDD §2.

    Utilise secrets.SystemRandom() — non prédictible, non reproductible.
    Un attaquant qui connaît l'algorithme ne peut pas anticiper le résultat.

    Returns:
        "COMMON" | "UNCOMMON" | "RARE" | "EPIC" | "LEGENDARY"
    """
    r = _srng.random()
    for rarity, threshold in _RARITY_THRESHOLDS:
        if r < threshold:
            return rarity
    return "LEGENDARY"  # cas r == 1.0 exactement (probabilité nulle, garde-fou)


def generate_base_stats(ship_class: str, rarity: str) -> dict[str, float]:
    """
    Génère les stats de base selon la formule GDD §2 :
        stat_rng = base × rarity_mult + offset
        offset   ~ Uniform(−10 %, +10 %) de (base × rarity_mult)

    Chaque stat a son propre tirage offset → diversité intra-rareté.
    speed : 1 décimale. hull/shield/dps/cargo/stealth/support_aura : entier.

    Args:
        ship_class : "ATTACK" | "DEFENSE" | "SUPPORT" | "EXPLORATION"
        rarity     : "COMMON" | "UNCOMMON" | "RARE" | "EPIC" | "LEGENDARY"

    Returns:
        Dict prêt à être stocké dans ships.base_stats (JSONB).

    Raises:
        ValueError : classe ou rareté inconnue.
    """
    if ship_class not in _BASE_STATS_BY_CLASS:
        raise ValueError(f"Classe de vaisseau inconnue : {ship_class!r}")
    if rarity not in _RARITY_MULT:
        raise ValueError(f"Rareté inconnue : {rarity!r}")

    mult = _RARITY_MULT[rarity]
    result: dict[str, float] = {}

    for stat, base_val in _BASE_STATS_BY_CLASS[ship_class].items():
        after_mult = base_val * mult
        offset = _srng.uniform(-0.10, 0.10) * after_mult
        raw = after_mult + offset

        if stat == "speed":
            result[stat] = round(max(0.0, raw), 1)
        elif stat in ("stealth", "support_aura"):
            # Pourcentages — on garde 2 décimales
            result[stat] = round(max(0.0, raw), 2)
        else:
            result[stat] = int(max(0, round(raw)))

    return result


def apply_pedigree_bonus(
    base_stats: dict[str, float],
    parent_best_stat: str,
) -> dict[str, float]:
    """
    Applique le Pedigree : +5 % sur la meilleure stat du parent (GDD §5a).
    Retourne un nouveau dict — ne mute jamais base_stats.

    Args:
        base_stats       : Stats déjà générées du nouveau vaisseau.
        parent_best_stat : Clé de la stat à booster (ex : "dps").
    """
    boosted = dict(base_stats)
    if parent_best_stat in boosted:
        original = boosted[parent_best_stat]
        if parent_best_stat == "speed":
            boosted[parent_best_stat] = round(original * 1.05, 1)
        elif parent_best_stat in ("stealth", "support_aura"):
            boosted[parent_best_stat] = round(original * 1.05, 2)
        else:
            boosted[parent_best_stat] = int(round(original * 1.05))
    return boosted


def find_best_stat(stats: dict[str, float]) -> str:
    """
    Retourne la clé de la stat avec la valeur absolue la plus élevée.
    Exclut stealth et support_aura (valeurs faibles, non représentatives de la puissance).
    """
    candidates = {
        k: v for k, v in stats.items()
        if k not in ("stealth", "support_aura")
    }
    return max(candidates, key=lambda k: candidates[k])


# ---------------------------------------------------------------------------
# Point d'entrée principal — avec effets de bord BDD
# ---------------------------------------------------------------------------

async def build_ship(
    db: AsyncSession,
    player_id: uuid.UUID,
    ship_type: str,
    planet_id: uuid.UUID,
    parent_ship_id: uuid.UUID | None = None,
) -> Ship:
    """
    Construit un vaisseau et le persiste en base dans la transaction courante.

    Flux :
      1. Validation ship_type
      2. SELECT FOR UPDATE sur le joueur → verrou anti double-spend
      3. Vérification et déduction des ressources
      4. Tirage rareté + génération base_stats (SystemRandom)
      5. Application Pedigree si parent_ship_id fourni
      6. INSERT Ship en statut DOCKED
      7. Invalidation cache Redis hangar

    ⚠ Ne commit PAS — le commit est délégué au router FastAPI.
    Toute exception rollback la transaction (gestion dans get_db_dep).

    Args:
        db             : Session async SQLAlchemy (transaction ouverte).
        player_id      : UUID du joueur qui commande la construction.
        ship_type      : Ex : "frigate_attack".
        planet_id      : Planète chantier (pour futures vérifications shipyard level).
        parent_ship_id : Vaisseau parent pour Pedigree (optionnel).

    Returns:
        Instance Ship (non committée).

    Raises:
        HTTPException 400 : ship_type inconnu.
        HTTPException 402 : ressources insuffisantes.
        HTTPException 403 : parent appartient à un autre joueur.
        HTTPException 404 : joueur introuvable.
        HTTPException 409 : conditions Pedigree non remplies.
    """
    if ship_type not in SHIP_TYPE_CLASS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Type de vaisseau inconnu : {ship_type!r}.",
        )

    ship_class = SHIP_TYPE_CLASS[ship_type]
    build_cost = SHIP_TYPE_BUILD_COST[ship_type]

    # 1. Vérifier que le joueur existe
    player_result = await db.execute(
        select(Player).where(Player.id == player_id)
    )
    player: Player | None = player_result.scalar_one_or_none()
    if player is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Joueur introuvable.")

    # 2. Verrou sur la planète + déduction des ressources
    planet_result = await db.execute(
        select(Planet).where(Planet.id == planet_id).with_for_update()
    )
    planet: Planet | None = planet_result.scalar_one_or_none()
    if planet is None or planet.owner_id != player_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Planète introuvable.")

    _check_and_deduct_resources(planet, build_cost, db)

    from app.services.ship_build_service import SHIP_SHIPYARD_REQUIREMENTS
    shipyard_level = _get_building_level(planet.buildings or {}, "shipyard")
    required_level = SHIP_SHIPYARD_REQUIREMENTS.get(ship_type, 1)
    if shipyard_level < required_level:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Chantier Naval insuffisant pour construire {ship_type!r}. "
                f"Requis : Niveau {required_level}, actuel : Niveau {shipyard_level}. "
                f"Améliorez votre Chantier Naval dans la page Bâtiments."
            ),
        )


    # 3. RNG
    rarity = roll_rarity()
    base_stats = generate_base_stats(ship_class, rarity)

    # 4. Pedigree optionnel
    parent_id_to_store: uuid.UUID | None = None
    if parent_ship_id is not None:
        parent = await _validate_pedigree_parent(db, parent_ship_id, player_id, ship_type)
        best_stat = find_best_stat(parent.base_stats)
        base_stats = apply_pedigree_bonus(base_stats, best_stat)
        parent_id_to_store = parent_ship_id

    # 5. Slots
    total_slots, premium_slots = _RARITY_SLOTS[rarity]

    # 6. INSERT — noms de champs exacts du modèle Ship
    from app.models.models import ShipClass, ShipRarity, ShipStatus
    ship = Ship(
        owner_id=player_id,
        planet_id=planet_id,
        ship_type=ship_type,
        class_=ShipClass(ship_class),
        rarity=ShipRarity(rarity),
        grade=0,
        combat_xp=0,
        base_stats=base_stats,
        parent_ship_id=parent_id_to_store,
        status=ShipStatus.DOCKED,
    )
    db.add(ship)

    # 7. Cache
    await invalidate_hangar_cache(player_id)

    return ship


# ---------------------------------------------------------------------------
# Helpers privés
# ---------------------------------------------------------------------------

def _check_and_deduct_resources(
    planet: Planet,
    cost: dict[str, float],
    db: AsyncSession,
) -> None:
    needed = {
        "metal":     cost.get("metal", 0),
        "crystal":   cost.get("crystal", 0),
        "deuterium": cost.get("deuterium", 0),
    }


    if (
        math.floor(float(planet.metal))     < needed["metal"]
        or math.floor(float(planet.crystal))  < needed["crystal"]
        or math.floor(float(planet.deuterium)) < needed["deuterium"]
    ):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                f"Ressources insuffisantes. "
                f"Requis : métal={needed['metal']:.0f}, cristal={needed['crystal']:.0f}, "
                f"deutérium={needed['deuterium']:.0f}. "
                f"Disponible : métal={float(planet.metal):.0f}, cristal={float(planet.crystal):.0f}, "
                f"deutérium={float(planet.deuterium):.0f}."
            ),
        )

    planet.metal     = float(planet.metal)     - needed["metal"]
    planet.crystal   = float(planet.crystal)   - needed["crystal"]
    planet.deuterium = float(planet.deuterium) - needed["deuterium"]
    db.add(planet)


async def _validate_pedigree_parent(
    db: AsyncSession,
    parent_ship_id: uuid.UUID,
    player_id: uuid.UUID,
    ship_type: str,
) -> Ship:
    """
    Valide les conditions de transmission Pedigree (GDD §5a) :
      - Appartient au joueur demandeur
      - Même ship_type que le vaisseau à construire
      - Grade ≥ 3
      - Statut DOCKED (pas en flotte ni en forge)

    Raises:
        HTTPException 403/404/409 selon la condition non remplie.
    """
    result = await db.execute(select(Ship).where(Ship.id == parent_ship_id))
    parent: Ship | None = result.scalar_one_or_none()

    if parent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vaisseau parent introuvable.",
        )
    if parent.owner_id != player_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce vaisseau ne vous appartient pas.",
        )
    if parent.ship_type != ship_type:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Pedigree impossible : le parent est de type {parent.ship_type!r}, "
                f"attendu {ship_type!r}."
            ),
        )
    if parent.grade < 3:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Pedigree impossible : Grade {parent.grade} insuffisant "
                f"(Grade 3 minimum requis)."
            ),
        )
    if parent.status != "DOCKED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Le vaisseau parent doit être amarré (DOCKED) "
                f"pour transmettre un Pedigree. Statut actuel : {parent.status}."
            ),
        )
    return parent
