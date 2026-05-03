"""
app/services/combat_engine.py
Agent 5 — Développeur Backend

Responsabilité : Résolution complète d'un combat PvP.

Flux d'un combat :
  1. Chargement des flottes (vaisseaux + current_stats depuis ship_stats_service)
  2. Calcul de la puissance de chaque côté (pour XP différentielle)
  3. Application des synergies de classe (côté serveur uniquement, GDD §1)
  4. Résolution round par round (max 50 rounds, déterministe avec seed)
  5. Calcul XP différentielle par vaisseau survivant (GDD §4)
  6. Détection grade_up → invalidation cache + event WS ship.grade_up
  7. Détection cicatrices (GDD §5d) → INSERT ship_scars + event WS ship.scar_earned
  8. Persistance combat_log en base (JSONB replay)
  9. Broadcast WS combat.result vers les deux joueurs
  10. Retour du rapport de combat

Décisions techniques (Agent 3) :
  - Seed déterministe pour le replay : stocké dans combat_log
  - Le calcul XP est loggé avec ses paramètres pour auditabilité
  - Transaction unique pour toutes les écritures (grade, scars, xp, log)
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import CombatLog, ScarTag, Ship, ShipScar, ShipStatus
from app.services.module_inventory_service import create_loot_crate
from app.services.ship_stats_service import (
    GRADE_SHIELD_REGEN,
    get_current_stats,
    invalidate_ship_cache,
)
from app.core.redis_client import publish_event

# ---------------------------------------------------------------------------
# Constantes GDD
# ---------------------------------------------------------------------------

MAX_ROUNDS = 50   # plafond anti-boucle infinie (GDD note développeurs)

# XP de base par résultat de combat (GDD §4)
_BASE_XP: dict[str, int] = {
    "ATTACK_WIN":        100,
    "ATTACK_WIN_LOOT":    80,
    "DEFENSE_WIN":       150,
    "ALLIANCE":           60,
    "LOSS_SURVIVOR":      40,
}

# Seuils XP pour monter de grade (GDD §4)
_GRADE_THRESHOLDS: list[tuple[int, int]] = [
    (5, 40_000),
    (4, 15_000),
    (3,  6_000),
    (2,  2_000),
    (1,    500),
]  # ordre décroissant pour trouver le grade le plus haut en premier

# Grade 4 — immunité première destruction (GDD §4)
# Le vaisseau survit à 1 HP si c'est sa première mort dans ce combat.
GRADE_4_IMMUNITY_HP = 1

# Seuil de cicatrice : perte de 75 %+ de la coque (GDD §5d)
SCAR_HULL_LOSS_THRESHOLD = 0.75

# Seuil de cicatrice : combat contre une flotte ≥ 2× plus puissante (GDD §5d)
SCAR_POWER_RATIO_THRESHOLD = 2.0

_srng_combat = random.SystemRandom()   # pour les tirages in-combat non-reproductibles


# ---------------------------------------------------------------------------
# Structures de données internes au moteur
# ---------------------------------------------------------------------------

@dataclass
class CombatShip:
    """
    Vue mutable d'un vaisseau pendant la résolution d'un round.
    Contient les stats effectives (après grade + modules + synergies).
    """
    ship_id:           uuid.UUID
    owner_id:          uuid.UUID
    ship_class:        str
    rarity:            str
    grade:             int
    base_hull:         int          # hull de base (pour calcul cicatrice)
    hull:              int          # HP actuels
    hull_max:          int          # HP max effectives (avec grade/modules)
    shield:            int
    shield_max:        int
    dps:               int
    shield_regen:      float        # ratio par round (Grade 3+)
    support_aura:      float
    evasion_chance:    float = 0.0   # Doctrine FANTOME
    damage_reduction:  float = 0.0   # Doctrine FORTERESSE
    riposte_chance:    float = 0.0   # Résonance RIPOSTE (CANNON+SHIELD)
    immunity_used:     bool = False  # Grade 4 : immunité première mort

    # Comptabilité post-combat
    xp_earned:         int = 0
    hull_start:        int = 0      # Hull au début du combat (pour cicatrice)
    alive:             bool = True

    def __post_init__(self) -> None:
        self.hull_start = self.hull

    def take_damage(self, raw_dmg: int) -> dict[str, Any]:
        """
        Applique des dégâts : bouclier absorbe en premier, puis coque.
        Grade 4 : immunité première destruction → survie à 1 HP.

        Returns:
            Détail du hit pour le log de round.
        """
        shield_absorbed = min(self.shield, raw_dmg)
        self.shield -= shield_absorbed
        hull_dmg = raw_dmg - shield_absorbed
        self.hull = max(0, self.hull - hull_dmg)

        destroyed = False
        if self.hull == 0:
            # Grade 4 : immunité première mort (GDD §4)
            if self.grade >= 4 and not self.immunity_used:
                self.hull = GRADE_4_IMMUNITY_HP
                self.immunity_used = True
            else:
                self.alive = False
                destroyed = True

        return {
            "shield_absorbed": shield_absorbed,
            "hull_damage":     hull_dmg,
            "hull_remaining":  self.hull,
            "shield_remaining":self.shield,
            "destroyed":       destroyed,
            "immunity_trigger":self.immunity_used and hull_dmg > 0 and self.hull == GRADE_4_IMMUNITY_HP,
        }

    def regenerate_shield(self) -> None:
        """Régénération de bouclier en fin de round (Grade 3+, GDD §4)."""
        if self.shield_regen > 0 and self.shield < self.shield_max:
            regen = int(self.shield_max * self.shield_regen)
            self.shield = min(self.shield_max, self.shield + regen)

    def snapshot(self) -> dict[str, Any]:
        return {
            "ship_id":   str(self.ship_id),
            "class":     self.ship_class,
            "rarity":    self.rarity,
            "grade":     self.grade,
            "hull":      self.hull,
            "hull_max":  self.hull_max,
            "shield":    self.shield,
            "shield_max":self.shield_max,
            "dps":       self.dps,
            "alive":     self.alive,
        }


@dataclass
class RoundResult:
    round_number:      int
    attackers_before:  list[dict]
    defenders_before:  list[dict]
    synergies_applied: list[str]
    hits:              list[dict] = field(default_factory=list)
    attackers_after:   list[dict] = field(default_factory=list)
    defenders_after:   list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "round":             self.round_number,
            "synergies":         self.synergies_applied,
            "attackers_before":  self.attackers_before,
            "defenders_before":  self.defenders_before,
            "hits":              self.hits,
            "attackers_after":   self.attackers_after,
            "defenders_after":   self.defenders_after,
        }


# ---------------------------------------------------------------------------
# Calcul de la puissance de flotte (pour XP différentielle)
# ---------------------------------------------------------------------------

def _fleet_power(ships: list[CombatShip]) -> float:
    """
    Indicateur de puissance agrégé d'une flotte.
    Formule simple : Σ (dps × hull_max × (1 + shield_max / hull_max))
    Suffit pour la comparaison relative nécessaire à l'XP différentielle.
    """
    total = 0.0
    for s in ships:
        if s.hull_max > 0:
            shield_ratio = s.shield_max / s.hull_max
            total += s.dps * s.hull_max * (1.0 + shield_ratio)
    return max(total, 1.0)   # évite division par zéro


# ---------------------------------------------------------------------------
# Synergies de classes (GDD §1)
# ---------------------------------------------------------------------------

def _compute_synergy_bonuses(
    ships: list[CombatShip],
    label: str,
) -> tuple[dict[str, float], list[str]]:
    """
    Calcule les bonus de synergie pour une liste de vaisseaux.
    Les modifications sont appliquées directement sur les objets CombatShip.

    Returns:
        (dict stat→bonus_ratio, liste de descriptions pour le log)
    """
    classes = [s.ship_class for s in ships]
    count = len(classes)
    applied: list[str] = []
    bonus: dict[str, float] = {}

    if count == 0:
        return bonus, applied

    n_attack  = classes.count("ATTACK")
    n_defense = classes.count("DEFENSE")
    n_support = classes.count("SUPPORT")
    n_explore = classes.count("EXPLORATION")

    # Attaque + Soutien → +20 % DPS pour les Attaque (GDD §1)
    if n_attack > 0 and n_support >= 1:
        for s in ships:
            if s.ship_class == "ATTACK":
                s.dps = int(s.dps * 1.20)
        bonus["dps"] = bonus.get("dps", 0.0) + 0.20
        applied.append(f"ATTACK+SUPPORT: +20% DPS ({label})")

    # Défense + Soutien → réparation de coque en combat (+5 %/round)
    # Ce bonus est géré dans la boucle de round (pas sur les stats initiales)
    if n_defense > 0 and n_support >= 1:
        applied.append(f"DEFENSE+SUPPORT: +5% hull regen/round ({label})")
        bonus["hull_regen"] = 0.05

    # Attaque + Exploration → +10 % vitesse (non pertinent en combat, mais loggé)
    explore_ratio = n_explore / count if count > 0 else 0
    if n_attack > 0 and explore_ratio >= 0.20:
        applied.append(f"ATTACK+EXPLORATION: +10% speed ({label})")

    # Défense + Défense → bouclier collectif +15 % (GDD §1)
    if n_defense >= 3:
        for s in ships:
            if s.ship_class == "DEFENSE":
                s.shield_max = int(s.shield_max * 1.15)
                s.shield = min(s.shield, s.shield_max)
        bonus["shield"] = bonus.get("shield", 0.0) + 0.15
        applied.append(f"DEFENSE×3+: +15% bouclier collectif ({label})")

    return bonus, applied


# ---------------------------------------------------------------------------
# Résolution d'un round
# ---------------------------------------------------------------------------

def _resolve_round(
    round_num: int,
    attackers: list[CombatShip],
    defenders: list[CombatShip],
    rng: random.Random,
    attacker_support_bonus: float,
    defender_support_bonus: float,
) -> RoundResult:
    """
    Résout un round de combat.

    - Tirs simultanés (tous les vaisseaux tirent avant de retirer les morts)
    - Support aura : les Soutien alliés amplifient le DPS des Attaque
    - Régénération de bouclier en fin de round (Grade 3+)
    - Réparation de coque si synergie Défense+Soutien active
    """
    alive_att = [s for s in attackers if s.alive]
    alive_def = [s for s in defenders if s.alive]

    result = RoundResult(
        round_number=round_num,
        attackers_before=[s.snapshot() for s in alive_att],
        defenders_before=[s.snapshot() for s in alive_def],
        synergies_applied=[],
    )

    if not alive_att or not alive_def:
        return result

    hits: list[dict] = []

    # --- Tirs des attaquants sur les défenseurs ---
    for shooter in alive_att:
        if not [d for d in defenders if d.alive]:
            break
        target = rng.choice([d for d in defenders if d.alive])

        # Doctrine FANTOME : évasion — le défenseur esquive le tir
        if target.evasion_chance > 0 and rng.random() < target.evasion_chance:
            hits.append({
                "shooter_id":    str(shooter.ship_id),
                "target_id":     str(target.ship_id),
                "side":          "attacker",
                "raw_dps":       0,
                "effective_dps": 0,
                "evaded":        True,
            })
            continue

        # DPS de base + variance ±10 %
        raw_dps = shooter.dps * rng.uniform(0.90, 1.10)
        # Support aura alliée (si synergie Attaque+Soutien active)
        effective_dps = int(raw_dps * (1.0 + attacker_support_bonus))
        # Doctrine FORTERESSE : réduction de dégâts
        if target.damage_reduction > 0:
            effective_dps = int(effective_dps * (1.0 - target.damage_reduction))

        hit = target.take_damage(effective_dps)
        hit.update({
            "shooter_id":    str(shooter.ship_id),
            "target_id":     str(target.ship_id),
            "side":          "attacker",
            "raw_dps":       int(raw_dps),
            "effective_dps": effective_dps,
        })
        hits.append(hit)

        # Résonance RIPOSTE : contre-tir immédiat si la cible survit
        if target.alive and target.riposte_chance > 0 and rng.random() < target.riposte_chance:
            riposte_dps = int(target.dps * rng.uniform(0.50, 0.80))
            riposte_hit = shooter.take_damage(riposte_dps)
            riposte_hit.update({
                "shooter_id":    str(target.ship_id),
                "target_id":     str(shooter.ship_id),
                "side":          "attacker_riposte",
                "raw_dps":       riposte_dps,
                "effective_dps": riposte_dps,
                "riposte":       True,
            })
            hits.append(riposte_hit)

    # --- Tirs des défenseurs sur les attaquants ---
    for shooter in alive_def:
        if not [a for a in attackers if a.alive]:
            break
        target = rng.choice([a for a in attackers if a.alive])

        # Doctrine FANTOME : évasion
        if target.evasion_chance > 0 and rng.random() < target.evasion_chance:
            hits.append({
                "shooter_id":    str(shooter.ship_id),
                "target_id":     str(target.ship_id),
                "side":          "defender",
                "raw_dps":       0,
                "effective_dps": 0,
                "evaded":        True,
            })
            continue

        raw_dps = shooter.dps * rng.uniform(0.90, 1.10)
        effective_dps = int(raw_dps * (1.0 + defender_support_bonus))
        # Doctrine FORTERESSE : réduction de dégâts
        if target.damage_reduction > 0:
            effective_dps = int(effective_dps * (1.0 - target.damage_reduction))

        hit = target.take_damage(effective_dps)
        hit.update({
            "shooter_id":    str(shooter.ship_id),
            "target_id":     str(target.ship_id),
            "side":          "defender",
            "raw_dps":       int(raw_dps),
            "effective_dps": effective_dps,
        })
        hits.append(hit)

        # Résonance RIPOSTE : contre-tir immédiat si la cible survit
        if target.alive and target.riposte_chance > 0 and rng.random() < target.riposte_chance:
            riposte_dps = int(target.dps * rng.uniform(0.50, 0.80))
            riposte_hit = shooter.take_damage(riposte_dps)
            riposte_hit.update({
                "shooter_id":    str(target.ship_id),
                "target_id":     str(shooter.ship_id),
                "side":          "defender_riposte",
                "raw_dps":       riposte_dps,
                "effective_dps": riposte_dps,
                "riposte":       True,
            })
            hits.append(riposte_hit)

    # --- Régénérations fin de round ---
    for s in attackers + defenders:
        if s.alive:
            s.regenerate_shield()

    # --- Réparation coque synergie Défense+Soutien ---
    if attacker_support_bonus > 0:
        for s in alive_att:
            if s.ship_class == "DEFENSE" and s.alive:
                repair = int(s.hull_max * 0.05)
                s.hull = min(s.hull_max, s.hull + repair)
    if defender_support_bonus > 0:
        for s in alive_def:
            if s.ship_class == "DEFENSE" and s.alive:
                repair = int(s.hull_max * 0.05)
                s.hull = min(s.hull_max, s.hull + repair)

    result.hits = hits
    result.attackers_after = [s.snapshot() for s in alive_att]
    result.defenders_after = [s.snapshot() for s in alive_def]
    return result


# ---------------------------------------------------------------------------
# XP différentielle (GDD §4)
# ---------------------------------------------------------------------------

def _compute_differential_xp(
    base_xp: int,
    own_power: float,
    enemy_power: float,
) -> tuple[int, dict[str, float]]:
    """
    Applique la formule GDD §4 :
        XP = base_XP × (1 + max(0, enemy_power / own_power − 1) × 2.5)

    Retourne (xp_final, params_pour_audit).
    Les params sont loggés dans combat_log pour auditabilité (Agent 3).
    """
    ratio = enemy_power / own_power if own_power > 0 else 1.0
    diff_factor = max(0.0, ratio - 1.0) * 2.5
    xp_final = int(base_xp * (1.0 + diff_factor))

    audit_params = {
        "base_xp":      base_xp,
        "own_power":    round(own_power, 2),
        "enemy_power":  round(enemy_power, 2),
        "ratio":        round(ratio, 4),
        "diff_factor":  round(diff_factor, 4),
        "xp_final":     xp_final,
    }
    return xp_final, audit_params


# ---------------------------------------------------------------------------
# Détection et création des cicatrices (GDD §5d)
# ---------------------------------------------------------------------------

def _should_earn_scar(
    ship: CombatShip,
    enemy_power: float,
    own_power: float,
) -> bool:
    """
    Conditions de cicatrice (GDD §5d) :
      - A survécu (alive == True)
      - Perdu ≥ 75 % de sa coque au cours du combat
      OU
      - Combat contre une flotte ≥ 2× plus puissante
    """
    if not ship.alive:
        return False

    hull_loss_ratio = (ship.hull_start - ship.hull) / max(ship.hull_start, 1)
    if hull_loss_ratio >= SCAR_HULL_LOSS_THRESHOLD:
        return True

    power_ratio = enemy_power / max(own_power, 1.0)
    if power_ratio >= SCAR_POWER_RATIO_THRESHOLD:
        return True

    return False


# ---------------------------------------------------------------------------
# Point d'entrée principal
# ---------------------------------------------------------------------------

async def resolve_combat(
    db: AsyncSession,
    attacker_fleet_id: uuid.UUID,
    defender_planet_id: uuid.UUID,
    attacker_ship_ids: list[uuid.UUID],
    defender_ship_ids: list[uuid.UUID],
    loot: dict[str, float] | None = None,
) -> dict[str, Any]:
    """
    Résout un combat complet entre deux flottes et persiste tous les effets.

    Effets persistés dans une unique transaction :
      - combat_xp et grade mis à jour sur chaque vaisseau survivant
      - ShipScar insérés pour les vaisseaux éligibles
      - CombatLog inséré avec tous les rounds (replay possible)

    Events WebSocket émis (hors transaction) :
      - combat.result vers les deux joueurs
      - ship.grade_up pour chaque montée de grade
      - ship.scar_earned pour chaque cicatrice

    Args:
        db:                  Session async SQLAlchemy (dans une transaction).
        attacker_fleet_id:   UUID de la flotte attaquante (pour le log).
        defender_planet_id:  UUID de la planète défendue (pour le log).
        attacker_ship_ids:   Liste d'UUIDs des vaisseaux attaquants.
        defender_ship_ids:   Liste d'UUIDs des vaisseaux défenseurs.
        loot:                Ressources pillées si l'attaquant gagne (optionnel).

    Returns:
        Rapport de combat structuré (identique au payload WS combat.result).

    Raises:
        HTTPException 400 : flotte vide.
        HTTPException 404 : vaisseau introuvable.
    """
    if not attacker_ship_ids or not defender_ship_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Une flotte ne peut pas être vide au début du combat.",
        )

    # --- Chargement des vaisseaux ---
    att_ships_db = await _load_ships(db, attacker_ship_ids)
    def_ships_db = await _load_ships(db, defender_ship_ids)

    # --- Construction des CombatShip avec current_stats ---
    att_combatants = await _build_combatants(db, att_ships_db)
    def_combatants = await _build_combatants(db, def_ships_db)

    # --- Puissance initiale (pour XP différentielle) ---
    att_power = _fleet_power(att_combatants)
    def_power = _fleet_power(def_combatants)

    # --- Synergies (calculées une seule fois avant le combat) ---
    att_bonuses, att_synergie_log = _compute_synergy_bonuses(att_combatants, "attacker")
    def_bonuses, def_synergie_log = _compute_synergy_bonuses(def_combatants, "defender")

    # Support aura : moyenne des auras de soutien dans la flotte
    att_support_aura = sum(
        s.support_aura for s in att_combatants if s.ship_class == "SUPPORT"
    ) / 100.0
    def_support_aura = sum(
        s.support_aura for s in def_combatants if s.ship_class == "SUPPORT"
    ) / 100.0

    # --- Seed déterministe pour le replay ---
    combat_seed = _srng_combat.randint(0, 2**32 - 1)
    rng = random.Random(combat_seed)

    # --- Résolution des rounds ---
    rounds: list[RoundResult] = []

    for round_num in range(1, MAX_ROUNDS + 1):
        alive_att = [s for s in att_combatants if s.alive]
        alive_def = [s for s in def_combatants if s.alive]

        if not alive_att or not alive_def:
            break

        round_result = _resolve_round(
            round_num,
            att_combatants,
            def_combatants,
            rng,
            att_support_aura,
            def_support_aura,
        )
        rounds.append(round_result)

    # --- Détermination du vainqueur ---
    att_survivors = [s for s in att_combatants if s.alive]
    def_survivors = [s for s in def_combatants if s.alive]

    if att_survivors and not def_survivors:
        winner = "ATTACKER"
    elif def_survivors and not att_survivors:
        winner = "DEFENDER"
    else:
        winner = "DRAW"

    # --- XP différentielle et montées de grade ---
    grade_up_events: list[dict] = []
    scar_events:     list[dict] = []

    # XP pour les attaquants survivants
    if winner == "ATTACKER":
        base_xp_key = "ATTACK_WIN_LOOT" if loot else "ATTACK_WIN"
    else:
        base_xp_key = "LOSS_SURVIVOR"

    att_xp_audit: list[dict] = []
    for cs in att_survivors:
        base_xp = _BASE_XP[base_xp_key]
        xp_final, audit = _compute_differential_xp(base_xp, att_power, def_power)
        cs.xp_earned = xp_final
        att_xp_audit.append({"ship_id": str(cs.ship_id), **audit})

    # XP pour les défenseurs survivants
    def_xp_key = "DEFENSE_WIN" if winner == "DEFENDER" else "LOSS_SURVIVOR"
    def_xp_audit: list[dict] = []
    for cs in def_survivors:
        base_xp = _BASE_XP[def_xp_key]
        xp_final, audit = _compute_differential_xp(base_xp, def_power, att_power)
        cs.xp_earned = xp_final
        def_xp_audit.append({"ship_id": str(cs.ship_id), **audit})

    # --- Préchargement des tags de cicatrices depuis la BDD ---
    all_scar_tags = (await db.execute(select(ScarTag))).scalars().all()

    # --- Identifiants combat + propriétaires (nécessaires dans la boucle) ---
    combat_id = uuid.uuid4()
    attacker_owner_id = att_ships_db[0].owner_id if att_ships_db else None
    defender_owner_id = def_ships_db[0].owner_id if def_ships_db else None

    # --- Persistance des effets sur les Ship DB ---
    all_combatants = att_combatants + def_combatants
    cs_by_id = {cs.ship_id: cs for cs in all_combatants}
    loot_crates_events: list[dict] = []

    for ship_db in att_ships_db + def_ships_db:
        cs = cs_by_id.get(ship_db.id)
        if cs is None:
            continue

        if not cs.alive:
            # ── Loot crate pour le vainqueur ──────────────────────────────
            is_attacker_ship = (ship_db.owner_id == attacker_owner_id)
            recipient_id  = defender_owner_id if is_attacker_ship else attacker_owner_id
            loot_chance   = 0.20 if is_attacker_ship else 0.30
            if recipient_id and _srng_combat.random() < loot_chance:
                ship_display = ship_db.name or ship_db.ship_type
                await create_loot_crate(
                    player_id=recipient_id,
                    crate_type="STANDARD",
                    source="COMBAT",
                    source_ship_name=ship_display,
                    source_battle_id=str(combat_id),
                    db=db,
                )
                loot_crates_events.append({
                    "recipient": str(recipient_id),
                    "source_ship": ship_display,
                })

            # Vaisseau détruit — supprimé de la base (GDD §4 : perd toute son XP)
            await db.delete(ship_db)
            continue

        # Vaisseau survivant — remettre à DOCKED (il rentre au hangar)
        ship_db.status = ShipStatus.DOCKED

        # Ajout XP
        old_grade = ship_db.grade
        ship_db.combat_xp += cs.xp_earned

        # Calcul du nouveau grade
        new_grade = _compute_grade(ship_db.combat_xp)
        if new_grade != old_grade:
            ship_db.grade = new_grade
            db.add(ship_db)
            # Invalider le cache Redis du vaisseau (grade change les stats effectives)
            await invalidate_ship_cache(ship_db.id)
            grade_up_events.append({
                "ship_id":      str(ship_db.id),
                "owner_id":     str(ship_db.owner_id),
                "old_grade":    old_grade,
                "new_grade":    new_grade,
                "combat_xp":    ship_db.combat_xp,
            })
        else:
            db.add(ship_db)

        # Cicatrices
        if all_scar_tags and _should_earn_scar(
            cs,
            def_power if cs.owner_id == att_ships_db[0].owner_id else att_power,
            att_power if cs.owner_id == att_ships_db[0].owner_id else def_power,
        ):
            scar_tag = _srng_combat.choice(all_scar_tags)
            scar = ShipScar(
                id=uuid.uuid4(),
                ship_id=ship_db.id,
                tag_id=scar_tag.id,
                earned_at=datetime.now(UTC),
            )
            db.add(scar)
            scar_events.append({
                "ship_id":  str(ship_db.id),
                "owner_id": str(ship_db.owner_id),
                "tag":      scar_tag.narrative,
            })

    # --- CombatLog (replay complet) ---
    # Snapshots des vaisseaux pour le rapport (colonnes réelles du modèle CombatLog)
    att_snapshot = [
        {
            "ship_id":       str(cs.ship_id),
            "owner_id":      str(cs.owner_id),
            "ship_type":     next((s.ship_type for s in att_ships_db if s.id == cs.ship_id), ""),
            "rarity":        cs.rarity.value if hasattr(cs.rarity, "value") else cs.rarity,
            "grade":         cs.grade,
            "class":         cs.ship_class,
            "hull_at_start": cs.hull_max,
            "hull_at_end":   max(0, cs.hull),
            "destroyed":     not cs.alive,
            "xp_earned":     cs.xp_earned,
        }
        for cs in att_combatants
    ]
    def_snapshot = [
        {
            "ship_id":       str(cs.ship_id),
            "owner_id":      str(cs.owner_id),
            "ship_type":     next((s.ship_type for s in def_ships_db if s.id == cs.ship_id), ""),
            "rarity":        cs.rarity.value if hasattr(cs.rarity, "value") else cs.rarity,
            "grade":         cs.grade,
            "class":         cs.ship_class,
            "hull_at_start": cs.hull_max,
            "hull_at_end":   max(0, cs.hull),
            "destroyed":     not cs.alive,
            "xp_earned":     cs.xp_earned,
        }
        for cs in def_combatants
    ]

    # Outcome → colonne réelle du modèle (ATTACKER_WIN / DEFENDER_WIN / DRAW)
    outcome_map = {"ATTACKER": "ATTACKER_WIN", "DEFENDER": "DEFENDER_WIN", "DRAW": "DRAW"}
    outcome = outcome_map.get(winner, "DRAW")

    combat_log = CombatLog(
        id=combat_id,
        fleet_attacker_id=attacker_fleet_id,
        defender_planet_id=defender_planet_id,
        outcome=outcome,
        pillaged_metal=float(loot.get("metal", 0)) if loot else 0.0,
        pillaged_crystal=float(loot.get("crystal", 0)) if loot else 0.0,
        pillaged_deuterium=float(loot.get("deuterium", 0)) if loot else 0.0,
        rounds_log=[r.to_dict() for r in rounds],
        attacker_ships_snapshot=att_snapshot,
        defender_ships_snapshot=def_snapshot,
        attacker_power=round(att_power, 2),
        defender_power=round(def_power, 2),
        fought_at=datetime.now(UTC),
    )
    db.add(combat_log)

    # --- Rapport de combat (payload WS + réponse API) ---
    ships_lost_att = [str(s.ship_id) for s in att_combatants if not s.alive]
    ships_lost_def = [str(s.ship_id) for s in def_combatants if not s.alive]
    xp_diff = {
        str(cs.ship_id): cs.xp_earned
        for cs in att_survivors + def_survivors
        if cs.xp_earned > 0
    }

    report = {
        "combat_id":      str(combat_id),
        "winner":         winner,
        "total_rounds":   len(rounds),
        "attacker_power": round(att_power, 2),
        "defender_power": round(def_power, 2),
        "ships_lost":     {"attacker": ships_lost_att, "defender": ships_lost_def},
        "xp_diff":        xp_diff,
        "loot":           loot or {},
        "grade_ups":      grade_up_events,
        "scars":          scar_events,
        "synergies":      {"attacker": att_synergie_log, "defender": def_synergie_log},
        "loot_crates":    loot_crates_events,
    }

    # --- Broadcast WebSocket (hors transaction) ---
    await _broadcast_combat_events(
        report,
        grade_up_events,
        scar_events,
        str(attacker_owner_id) if attacker_owner_id else None,
        str(defender_owner_id) if defender_owner_id else None,
    )

    return report


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compute_grade(combat_xp: int) -> int:
    """
    Calcule le grade correspondant à un niveau d'XP (GDD §4).
    Parcourt les seuils par ordre décroissant.
    """
    for grade, threshold in _GRADE_THRESHOLDS:
        if combat_xp >= threshold:
            return grade
    return 0


async def _load_ships(
    db: AsyncSession,
    ship_ids: list[uuid.UUID],
) -> list[Ship]:
    """Charge les Ships depuis PostgreSQL. Lève 404 si un vaisseau est introuvable."""
    result = await db.execute(
        select(Ship).where(Ship.id.in_(ship_ids))
    )
    ships = list(result.scalars().all())

    found_ids = {s.id for s in ships}
    missing = set(ship_ids) - found_ids
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vaisseaux introuvables : {[str(m) for m in missing]}",
        )
    return ships


async def _build_combatants(
    db: AsyncSession,
    ships: list[Ship],
) -> list[CombatShip]:
    """
    Construit les CombatShip en récupérant current_stats depuis ship_stats_service.
    C'est la source de vérité pour les stats effectives en combat.
    """
    combatants = []
    for ship in ships:
        stats = await get_current_stats(ship.id, db)
        cs = CombatShip(
            ship_id=ship.id,
            owner_id=ship.owner_id,
            ship_class=ship.class_.value if hasattr(ship.class_, 'value') else ship.class_,
            rarity=ship.rarity,
            grade=ship.grade,
            base_hull=ship.base_stats.get("hull", 0),
            hull=stats["hull"],
            hull_max=stats["hull"],
            shield=stats["shield"],
            shield_max=stats["shield"],
            dps=stats["dps"],
            shield_regen=stats.get("shield_regen_per_round", 0.0),
            support_aura=stats.get("support_aura", 0.0),
            evasion_chance=stats.get("evasion_chance", 0.0),
            damage_reduction=stats.get("damage_reduction", 0.0),
            riposte_chance=stats.get("riposte_chance", 0.0),
        )
        combatants.append(cs)
    return combatants


async def _broadcast_combat_events(
    report: dict,
    grade_up_events: list[dict],
    scar_events: list[dict],
    attacker_owner_id: str | None,
    defender_owner_id: str | None,
) -> None:
    """
    Émet les événements WebSocket post-combat via Redis pub/sub.
    Appelé APRÈS le commit de la transaction (les données sont durables).
    """
    # combat.result → les deux joueurs
    for owner_id in filter(None, [attacker_owner_id, defender_owner_id]):
        await publish_event(
            channel=f"player:{owner_id}",
            event={"type": "combat.result", "data": report},
        )

    # ship.grade_up → propriétaire du vaisseau
    for event in grade_up_events:
        await publish_event(
            channel=f"player:{event['owner_id']}",
            event={"type": "ship.grade_up", "data": event},
        )

    # ship.scar_earned → propriétaire du vaisseau
    for event in scar_events:
        await publish_event(
            channel=f"player:{event['owner_id']}",
            event={"type": "ship.scar_earned", "data": event},
        )
