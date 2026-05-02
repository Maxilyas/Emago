#!/usr/bin/env python3
"""
emago-balance-simulator / simulate_combat.py

Simule N combats Emago entre 2 compositions de flottes.
Reproduit fidèlement combat_engine.py — synergies, XP différentielle, cap +150%,
immunité Grade 4, max 50 rounds, cicatrices.

Usage :
    python scripts/simulate_combat.py \
        --attacker '[{"class":"ATTACK","rarity":"LEGENDARY","grade":5,"modules":[{"type":"CANNON","level":5}]*6}]' \
        --defender '[{"class":"ATTACK","rarity":"COMMON","grade":0,"modules":[]}]*50' \
        --iterations 1000 \
        --output report.md
"""
from __future__ import annotations

import argparse
import json
import random
import secrets
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ─── Constantes (à synchroniser avec le backend Emago) ────────────────────

_RARITY_MULT = {
    "COMMON": 1.00, "UNCOMMON": 1.25, "RARE": 1.55, "EPIC": 1.90, "LEGENDARY": 2.40,
}

_BASE_STATS = {
    "ATTACK":      {"hull": 100, "shield": 20, "dps": 80, "speed": 45, "cargo": 200, "stealth": 0,  "support_aura": 0},
    "DEFENSE":     {"hull": 350, "shield": 120,"dps": 15, "speed": 15, "cargo": 500, "stealth": 0,  "support_aura": 0},
    "SUPPORT":     {"hull": 150, "shield": 40, "dps": 8,  "speed": 30, "cargo": 1000,"stealth": 0,  "support_aura": 15},
    "EXPLORATION": {"hull": 80,  "shield": 15, "dps": 12, "speed": 90, "cargo": 3000,"stealth": 25, "support_aura": 0},
}

_GRADE_BONUS = {0: 0.00, 1: 0.05, 2: 0.10, 3: 0.15, 4: 0.22, 5: 0.30}
_GRADE_REGEN = {0: 0.00, 1: 0.00, 2: 0.00, 3: 0.02, 4: 0.02, 5: 0.02}

_MODULE_BOOST = {1: 0.08, 2: 0.14, 3: 0.22, 4: 0.32, 5: 0.44}
_AFFINITY_MULT = 1.15
_MODULE_EFFECT = {
    "PROPELLER": ("speed", "EXPLORATION"),
    "ARMOR":     ("hull",  "DEFENSE"),
    "CANNON":    ("dps",   "ATTACK"),
    "EMITTER":   ("support_aura", "SUPPORT"),
    "SHIELD":    ("shield", "DEFENSE"),
    "CARGO":     ("cargo",  "EXPLORATION"),
}

_STAT_CAP_RATIO = 1.50
MAX_ROUNDS = 50
GRADE_4_IMMUNITY_HP = 1

SCAR_HULL_LOSS_THRESHOLD = 0.75
SCAR_POWER_RATIO_THRESHOLD = 2.0

_BASE_XP = {
    "ATTACK_WIN": 100, "ATTACK_WIN_LOOT": 80, "DEFENSE_WIN": 150,
    "ALLIANCE": 60, "LOSS_SURVIVOR": 40,
}

_srng = secrets.SystemRandom()


# ─── Modèles ───────────────────────────────────────────────────────────────

@dataclass
class Ship:
    ship_class: str
    rarity: str
    grade: int = 0
    modules: list[dict] = field(default_factory=list)  # [{"type":"CANNON","level":5}, ...]

    # Computed
    hull: float = 0
    shield: float = 0
    dps: float = 0
    hull_max: float = 0
    shield_max: float = 0
    shield_regen: float = 0
    support_aura: float = 0

    # State
    alive: bool = True
    immunity_used: bool = False
    hull_start: float = 0
    xp_earned: int = 0
    cap_reached: list = field(default_factory=list)


def generate_base_stats(ship_class: str, rarity: str) -> dict:
    """Tirage stats avec variance ±10%."""
    base = _BASE_STATS[ship_class]
    mult = _RARITY_MULT[rarity]
    out = {}
    for stat, value in base.items():
        scaled = value * mult
        offset = scaled * (_srng.random() * 0.20 - 0.10)  # uniform(-10%, +10%)
        raw = scaled + offset
        if stat == "speed":
            out[stat] = round(raw, 1)
        elif stat in ("stealth", "support_aura"):
            out[stat] = round(raw, 2)
        else:
            out[stat] = max(0, round(raw))
    return out


def compute_current_stats(ship: Ship) -> dict:
    """Calcule current_stats avec grade + modules + cap +150 %."""
    base = generate_base_stats(ship.ship_class, ship.rarity)

    # Étape 1 : grade
    grade_mult = _GRADE_BONUS[ship.grade]
    after_grade = {k: v * (1 + grade_mult) for k, v in base.items()}
    if ship.grade == 5:
        after_grade["stealth"] = min(100, after_grade["stealth"] + 10)

    # Étape 2 : modules
    module_boost_ratio = {k: 0.0 for k in base}
    for mod in ship.modules:
        if mod["type"] not in _MODULE_EFFECT:
            continue
        stat, affinity_class = _MODULE_EFFECT[mod["type"]]
        boost = _MODULE_BOOST[mod["level"]]
        if affinity_class == ship.ship_class:
            boost *= _AFFINITY_MULT
        module_boost_ratio[stat] += boost

    # Étape 3 : application + cap
    final = {}
    cap_reached = []
    for stat in base:
        target = after_grade[stat] + base[stat] * module_boost_ratio[stat]
        cap_value = base[stat] * (1 + _STAT_CAP_RATIO)
        if target > cap_value:
            final[stat] = cap_value
            cap_reached.append(stat)
        else:
            final[stat] = target
        # Arrondi
        if stat == "speed":
            final[stat] = round(final[stat], 1)
        elif stat in ("stealth", "support_aura"):
            final[stat] = round(final[stat], 2)
        else:
            final[stat] = max(0, round(final[stat]))

    final["cap_reached"] = cap_reached
    final["shield_regen_per_round"] = _GRADE_REGEN[ship.grade]
    final["base"] = base
    return final


def init_ship(spec: dict) -> Ship:
    """Crée un Ship combat-ready à partir d'une spec."""
    ship = Ship(
        ship_class=spec["class"],
        rarity=spec["rarity"],
        grade=spec.get("grade", 0),
        modules=spec.get("modules", []),
    )
    stats = compute_current_stats(ship)
    ship.hull = stats["hull"]
    ship.shield = stats["shield"]
    ship.dps = stats["dps"]
    ship.hull_max = stats["hull"]
    ship.shield_max = stats["shield"]
    ship.shield_regen = stats["shield_regen_per_round"]
    ship.support_aura = stats["support_aura"]
    ship.cap_reached = stats["cap_reached"]
    ship.hull_start = ship.hull
    return ship


def fleet_power(ships: list[Ship]) -> float:
    return max(1.0, sum(
        s.dps * s.hull_max * (1 + s.shield_max / s.hull_max)
        for s in ships if s.hull_max > 0
    ))


def compute_synergy_bonuses(ships: list[Ship]) -> dict:
    bonuses = {"hull_regen": 0.0}
    n_attack = sum(1 for s in ships if s.ship_class == "ATTACK")
    n_defense = sum(1 for s in ships if s.ship_class == "DEFENSE")
    n_support = sum(1 for s in ships if s.ship_class == "SUPPORT")

    if n_attack > 0 and n_support > 0:
        for s in ships:
            if s.ship_class == "ATTACK":
                s.dps *= 1.20

    if n_defense >= 3:
        for s in ships:
            if s.ship_class == "DEFENSE":
                s.shield_max *= 1.15
                s.shield = s.shield_max

    if n_defense > 0 and n_support > 0:
        bonuses["hull_regen"] = 0.05

    return bonuses


def take_damage(ship: Ship, raw_dmg: float) -> dict:
    shield_absorbed = min(ship.shield, raw_dmg)
    ship.shield -= shield_absorbed
    hull_dmg = raw_dmg - shield_absorbed
    ship.hull = max(0, ship.hull - hull_dmg)

    destroyed = False
    if ship.hull == 0:
        if ship.grade >= 4 and not ship.immunity_used:
            ship.hull = GRADE_4_IMMUNITY_HP
            ship.immunity_used = True
        else:
            ship.alive = False
            destroyed = True

    return {"shield_absorbed": shield_absorbed, "hull_damage": hull_dmg, "destroyed": destroyed}


def resolve_round(attackers: list[Ship], defenders: list[Ship], rng: random.Random,
                  att_aura: float, def_aura: float, syn_a: dict, syn_d: dict):
    alive_a = [s for s in attackers if s.alive]
    alive_d = [s for s in defenders if s.alive]

    # Tirs simultanés
    a_attacks = []
    if alive_a and alive_d:
        for shooter in alive_a:
            target = rng.choice(alive_d)
            raw = shooter.dps * rng.uniform(0.90, 1.10)
            effective = int(raw * (1 + att_aura / 100))
            a_attacks.append((target, effective))

    d_attacks = []
    if alive_a and alive_d:
        for shooter in alive_d:
            target = rng.choice(alive_a)
            raw = shooter.dps * rng.uniform(0.90, 1.10)
            effective = int(raw * (1 + def_aura / 100))
            d_attacks.append((target, effective))

    for target, dmg in a_attacks:
        take_damage(target, dmg)
    for target, dmg in d_attacks:
        take_damage(target, dmg)

    # Régen post-round
    for s in alive_a + alive_d:
        if not s.alive:
            continue
        regen = int(s.shield_max * s.shield_regen)
        s.shield = min(s.shield_max, s.shield + regen)

    # Hull regen synergie DEFENSE+SUPPORT
    if syn_a.get("hull_regen", 0) > 0:
        for s in alive_a:
            if s.alive and s.ship_class == "DEFENSE":
                repair = int(s.hull_max * 0.05)
                s.hull = min(s.hull_max, s.hull + repair)
    if syn_d.get("hull_regen", 0) > 0:
        for s in alive_d:
            if s.alive and s.ship_class == "DEFENSE":
                repair = int(s.hull_max * 0.05)
                s.hull = min(s.hull_max, s.hull + repair)


def compute_differential_xp(base_xp: int, own_power: float, enemy_power: float) -> int:
    ratio = enemy_power / max(own_power, 1.0)
    diff_factor = max(0.0, ratio - 1.0) * 2.5
    return int(base_xp * (1 + diff_factor))


def should_earn_scar(ship: Ship, enemy_power: float, own_power: float) -> bool:
    if not ship.alive:
        return False
    hull_loss_ratio = (ship.hull_start - ship.hull) / max(ship.hull_start, 1)
    if hull_loss_ratio >= SCAR_HULL_LOSS_THRESHOLD:
        return True
    power_ratio = enemy_power / max(own_power, 1.0)
    if power_ratio >= SCAR_POWER_RATIO_THRESHOLD:
        return True
    return False


def simulate_one(att_specs: list[dict], def_specs: list[dict], seed: int | None = None) -> dict:
    """Simule UN combat. Retourne un rapport."""
    if seed is None:
        seed = _srng.randint(0, 2**32 - 1)
    rng = random.Random(seed)

    attackers = [init_ship(s) for s in att_specs]
    defenders = [init_ship(s) for s in def_specs]

    att_power = fleet_power(attackers)
    def_power = fleet_power(defenders)

    syn_a = compute_synergy_bonuses(attackers)
    syn_d = compute_synergy_bonuses(defenders)

    att_aura = sum(s.support_aura for s in attackers if s.ship_class == "SUPPORT") / 100.0
    def_aura = sum(s.support_aura for s in defenders if s.ship_class == "SUPPORT") / 100.0

    rounds_played = 0
    for r in range(MAX_ROUNDS):
        if not any(s.alive for s in attackers) or not any(s.alive for s in defenders):
            break
        resolve_round(attackers, defenders, rng, att_aura, def_aura, syn_a, syn_d)
        rounds_played = r + 1

    a_alive = sum(1 for s in attackers if s.alive)
    d_alive = sum(1 for s in defenders if s.alive)

    if a_alive > 0 and d_alive == 0:
        winner = "ATTACKER"
    elif d_alive > 0 and a_alive == 0:
        winner = "DEFENDER"
    else:
        winner = "DRAW"

    # XP
    if winner == "ATTACKER":
        att_base = _BASE_XP["ATTACK_WIN"]
        def_base = _BASE_XP["LOSS_SURVIVOR"]
    elif winner == "DEFENDER":
        att_base = _BASE_XP["LOSS_SURVIVOR"]
        def_base = _BASE_XP["DEFENSE_WIN"]
    else:
        att_base = def_base = _BASE_XP["LOSS_SURVIVOR"]

    for s in attackers:
        if s.alive:
            s.xp_earned = compute_differential_xp(att_base, att_power, def_power)
    for s in defenders:
        if s.alive:
            s.xp_earned = compute_differential_xp(def_base, def_power, att_power)

    # Cicatrices
    scars_attacker = sum(1 for s in attackers if should_earn_scar(s, def_power, att_power))
    scars_defender = sum(1 for s in defenders if should_earn_scar(s, att_power, def_power))

    return {
        "winner": winner,
        "rounds": rounds_played,
        "att_power": round(att_power, 2),
        "def_power": round(def_power, 2),
        "att_alive": a_alive,
        "att_total": len(attackers),
        "def_alive": d_alive,
        "def_total": len(defenders),
        "att_xp_total": sum(s.xp_earned for s in attackers),
        "def_xp_total": sum(s.xp_earned for s in defenders),
        "scars_attacker": scars_attacker,
        "scars_defender": scars_defender,
        "att_cap_reached": list(set(c for s in attackers for c in s.cap_reached)),
        "def_cap_reached": list(set(c for s in defenders for c in s.cap_reached)),
    }


def aggregate(reports: list[dict]) -> dict:
    n = len(reports)
    winners = [r["winner"] for r in reports]
    return {
        "iterations": n,
        "winrate_attacker": winners.count("ATTACKER") / n,
        "winrate_defender": winners.count("DEFENDER") / n,
        "winrate_draw": winners.count("DRAW") / n,
        "rounds_mean": round(statistics.mean(r["rounds"] for r in reports), 2),
        "rounds_stddev": round(statistics.stdev(r["rounds"] for r in reports) if n > 1 else 0, 2),
        "att_alive_mean": round(statistics.mean(r["att_alive"] for r in reports), 2),
        "def_alive_mean": round(statistics.mean(r["def_alive"] for r in reports), 2),
        "att_xp_mean": round(statistics.mean(r["att_xp_total"] for r in reports), 2),
        "def_xp_mean": round(statistics.mean(r["def_xp_total"] for r in reports), 2),
        "scars_attacker_total": sum(r["scars_attacker"] for r in reports),
        "scars_defender_total": sum(r["scars_defender"] for r in reports),
        "cap_reached_attacker": list({c for r in reports for c in r["att_cap_reached"]}),
        "cap_reached_defender": list({c for r in reports for c in r["def_cap_reached"]}),
    }


def render_markdown(agg: dict, att_specs: list[dict], def_specs: list[dict]) -> str:
    lines = [
        "# Simulation combat Emago",
        "",
        f"**Itérations** : {agg['iterations']}",
        "",
        "## Compositions",
        "",
        f"**Attaquants ({len(att_specs)})** :",
        "```json",
        json.dumps(att_specs[:5], indent=2, ensure_ascii=False) + ("..." if len(att_specs) > 5 else ""),
        "```",
        "",
        f"**Défenseurs ({len(def_specs)})** :",
        "```json",
        json.dumps(def_specs[:5], indent=2, ensure_ascii=False) + ("..." if len(def_specs) > 5 else ""),
        "```",
        "",
        "## Résultats agrégés",
        "",
        "| Indicateur | Valeur |",
        "|---|---:|",
        f"| Winrate ATTACKER | {agg['winrate_attacker']*100:.1f} % |",
        f"| Winrate DEFENDER | {agg['winrate_defender']*100:.1f} % |",
        f"| Winrate DRAW | {agg['winrate_draw']*100:.1f} % |",
        f"| Rounds moyens | {agg['rounds_mean']} ± {agg['rounds_stddev']} |",
        f"| Survivants attaquants moyens | {agg['att_alive_mean']} |",
        f"| Survivants défenseurs moyens | {agg['def_alive_mean']} |",
        f"| XP moyenne attaquants | {agg['att_xp_mean']} |",
        f"| XP moyenne défenseurs | {agg['def_xp_mean']} |",
        f"| Cicatrices attaquants total | {agg['scars_attacker_total']} |",
        f"| Cicatrices défenseurs total | {agg['scars_defender_total']} |",
        f"| Caps stat attaquants | {', '.join(agg['cap_reached_attacker']) or '(aucune)'} |",
        f"| Caps stat défenseurs | {', '.join(agg['cap_reached_defender']) or '(aucune)'} |",
        "",
        "## Verdict",
        "",
    ]

    wr_a = agg["winrate_attacker"]
    if 0.45 <= wr_a <= 0.55:
        lines.append("✅ **Équilibré** (winrate attacker dans [45, 55] %).")
    elif wr_a >= 0.75:
        lines.append("⚠️ **ATTACKER domine** (winrate ≥ 75 %).")
    elif wr_a <= 0.25:
        lines.append("⚠️ **DEFENDER domine** (winrate attacker ≤ 25 %).")
    else:
        lines.append("⚠️ **Marginal** — surveiller en prod.")

    if agg["rounds_mean"] >= 45:
        lines.append("⚠️ Combats trop longs (rounds moyens ≥ 45) — DPS trop bas ou hull trop élevé.")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Simule des combats Emago.")
    parser.add_argument("--attacker", required=True, help="JSON de la composition attaquante")
    parser.add_argument("--defender", required=True, help="JSON de la composition défenseur")
    parser.add_argument("--iterations", type=int, default=1000)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    att_specs = json.loads(args.attacker)
    def_specs = json.loads(args.defender)

    print(f"Simulating {args.iterations} combats…", file=sys.stderr)
    reports = [simulate_one(att_specs, def_specs) for _ in range(args.iterations)]
    agg = aggregate(reports)
    md = render_markdown(agg, att_specs, def_specs)

    if args.output:
        args.output.write_text(md, encoding="utf-8")
        print(f"✅ Rapport sauvegardé : {args.output}", file=sys.stderr)
    else:
        print(md)


if __name__ == "__main__":
    main()
