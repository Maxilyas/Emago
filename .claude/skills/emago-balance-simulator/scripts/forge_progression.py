#!/usr/bin/env python3
"""
emago-balance-simulator / forge_progression.py

Calcule la probabilité d'obtenir un LEGENDARY au bout de N builds + forges,
ainsi que la distribution des Drift sur N forges.

Usage :
    python scripts/forge_progression.py --iterations 1000 [--output forge.md]
"""
from __future__ import annotations

import argparse
import random
import secrets
import sys
from collections import Counter
from pathlib import Path


_RARITY_THRESHOLDS = [
    ("COMMON",    0.55),
    ("UNCOMMON",  0.82),
    ("RARE",      0.94),
    ("EPIC",      0.99),
    ("LEGENDARY", 1.00),
]

_RARITY_UPGRADE = {
    "COMMON":   "UNCOMMON",
    "UNCOMMON": "RARE",
    "RARE":     "EPIC",
    "EPIC":     "LEGENDARY",
}

_DRIFT_PROBABILITY = 0.05

_srng = secrets.SystemRandom()


def roll_rarity() -> str:
    r = _srng.random()
    for rarity, threshold in _RARITY_THRESHOLDS:
        if r < threshold:
            return rarity
    return "LEGENDARY"


def simulate_legendary_probability(builds_count: int, iterations: int = 10000) -> dict:
    """Probabilité d'avoir au moins 1 LEGENDARY au bout de N builds (sans forge)."""
    counts_at_least_one = 0
    for _ in range(iterations):
        for _ in range(builds_count):
            if roll_rarity() == "LEGENDARY":
                counts_at_least_one += 1
                break
    p = counts_at_least_one / iterations
    return {"builds": builds_count, "p_at_least_one": p}


def simulate_drift_distribution(forges_count: int) -> dict:
    drift_count = sum(1 for _ in range(forges_count) if _srng.random() < _DRIFT_PROBABILITY)
    return {
        "forges": forges_count,
        "drift_count": drift_count,
        "drift_pct": drift_count / forges_count,
    }


def simulate_forge_strategy(target_rarity: str, max_cycles: int = 1000) -> dict:
    """
    Combien de cycles (build + éventuellement forge) faut-il en moyenne
    pour atteindre target_rarity ?
    """
    iterations = 1000
    cycles_to_target = []

    for _ in range(iterations):
        # Tier d'inventaire par rareté
        inventory = Counter()
        cycles = 0
        target_reached = False

        while cycles < max_cycles:
            cycles += 1
            # Build un ship
            r = roll_rarity()
            inventory[r] += 1

            # Vérifier si target atteint
            if r == target_rarity:
                target_reached = True
                break

            # Sinon, vérifier si on peut forger un de meilleur rareté
            for rar in ["COMMON", "UNCOMMON", "RARE", "EPIC"]:
                if inventory[rar] >= 2 and rar in _RARITY_UPGRADE:
                    # Forge !
                    inventory[rar] -= 2
                    new_rarity = _RARITY_UPGRADE[rar]
                    inventory[new_rarity] += 1
                    if new_rarity == target_rarity:
                        target_reached = True
                        break
            if target_reached:
                break

        if target_reached:
            cycles_to_target.append(cycles)

    if not cycles_to_target:
        return {"reached_in": iterations, "cycles_min": None, "cycles_mean": None, "cycles_p50": None, "cycles_p95": None}

    cycles_to_target.sort()
    return {
        "reached_in": len(cycles_to_target),
        "cycles_min": cycles_to_target[0],
        "cycles_mean": sum(cycles_to_target) / len(cycles_to_target),
        "cycles_p50": cycles_to_target[len(cycles_to_target) // 2],
        "cycles_p95": cycles_to_target[int(len(cycles_to_target) * 0.95)],
    }


def main():
    parser = argparse.ArgumentParser(description="Forge progression simulator.")
    parser.add_argument("--iterations", type=int, default=1000)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    print("Simulation forge progression…", file=sys.stderr)

    # 1. Probabilité LEGENDARY au build seul
    builds_thresholds = [50, 100, 200, 500]
    direct_probs = [simulate_legendary_probability(n, iterations=2000) for n in builds_thresholds]

    # 2. Drift sur 1000 forges
    drift_runs = [simulate_drift_distribution(1000) for _ in range(20)]
    drift_pcts = [d["drift_pct"] for d in drift_runs]
    drift_mean = sum(drift_pcts) / len(drift_pcts)
    drift_min = min(drift_pcts)
    drift_max = max(drift_pcts)

    # 3. Stratégie cumulative pour LEGENDARY
    legendary_strat = simulate_forge_strategy("LEGENDARY", max_cycles=500)

    lines = [
        "# Forge progression Emago",
        "",
        "## 1. Probabilité d'au moins 1 LEGENDARY direct au build",
        "",
        "| Builds | P(at least 1 LEGENDARY) |",
        "|---:|---:|",
    ]
    for d in direct_probs:
        lines.append(f"| {d['builds']} | {d['p_at_least_one']*100:.1f} % |")

    lines.extend([
        "",
        "## 2. Distribution Drift (5 % chance par forge)",
        "",
        f"Sur 20 simulations × 1000 forges chacune :",
        "",
        f"- Drift % moyen : **{drift_mean*100:.2f} %** (cible 5 %)",
        f"- Drift % min : {drift_min*100:.2f} %",
        f"- Drift % max : {drift_max*100:.2f} %",
        f"- Tolérance acceptable : [3.5 %, 6.5 %]",
        f"- Statut : {'✅ Conforme' if 0.035 <= drift_mean <= 0.065 else '⚠️ Hors fourchette'}",
        "",
        "## 3. Stratégie cumulée pour atteindre LEGENDARY",
        "",
        "Build + Forge cumulé : combien de cycles (1 cycle = 1 build) ?",
        "",
    ])

    if legendary_strat["reached_in"] > 0:
        lines.extend([
            f"- Itérations atteignant LEGENDARY : {legendary_strat['reached_in']} / 1000",
            f"- Cycles min : {legendary_strat['cycles_min']}",
            f"- Cycles moyens : {legendary_strat['cycles_mean']:.0f}",
            f"- Cycles p50 (médiane) : {legendary_strat['cycles_p50']}",
            f"- Cycles p95 : {legendary_strat['cycles_p95']}",
        ])
    else:
        lines.append("- Aucune simulation n'a atteint LEGENDARY dans le max_cycles.")

    md = "\n".join(lines)

    if args.output:
        args.output.write_text(md, encoding="utf-8")
        print(f"✅ Rapport : {args.output}", file=sys.stderr)
    else:
        print(md)


if __name__ == "__main__":
    main()
