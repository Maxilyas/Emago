#!/usr/bin/env python3
"""
emago-balance-simulator / xp_progression.py

Calcule combien de combats sont nécessaires pour passer un grade donné
selon le type de combat et le ratio de puissance.

Usage :
    python scripts/xp_progression.py [--start-grade 0] [--target-grade 5] \
        [--combat-type ATTACK_WIN] [--power-ratio 1.0] [--output xp.md]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


_BASE_XP = {
    "ATTACK_WIN":      100,
    "ATTACK_WIN_LOOT": 80,
    "DEFENSE_WIN":     150,
    "ALLIANCE":        60,
    "LOSS_SURVIVOR":   40,
}

_GRADE_THRESHOLDS = {
    0: 0,
    1: 500,
    2: 2000,
    3: 6000,
    4: 15000,
    5: 40000,
}


def differential_xp(base_xp: int, ratio: float) -> int:
    diff_factor = max(0.0, ratio - 1.0) * 2.5
    return int(base_xp * (1 + diff_factor))


def combats_to_grade(start_grade: int, target_grade: int, base_xp: int, ratio: float) -> dict:
    if target_grade <= start_grade:
        return {"error": "target_grade <= start_grade"}

    xp_required = _GRADE_THRESHOLDS[target_grade] - _GRADE_THRESHOLDS[start_grade]
    xp_per_combat = differential_xp(base_xp, ratio)
    if xp_per_combat <= 0:
        return {"error": "XP per combat = 0"}
    combats = xp_required // xp_per_combat + (1 if xp_required % xp_per_combat else 0)
    return {
        "xp_required": xp_required,
        "xp_per_combat": xp_per_combat,
        "combats_needed": combats,
    }


def main():
    parser = argparse.ArgumentParser(description="XP progression Emago.")
    parser.add_argument("--start-grade", type=int, default=0)
    parser.add_argument("--target-grade", type=int, default=5)
    parser.add_argument("--combat-type", choices=list(_BASE_XP.keys()), default="ATTACK_WIN")
    parser.add_argument("--power-ratio", type=float, default=1.0,
                        help="Ratio enemy_power / own_power (1.0 = équilibré, 3.0 = audacieux)")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    base_xp = _BASE_XP[args.combat_type]

    # Cas spécifique
    case = combats_to_grade(args.start_grade, args.target_grade, base_xp, args.power_ratio)

    # Comparaisons
    lines = [
        "# XP progression Emago",
        "",
        f"**Cas demandé** : Grade {args.start_grade} → Grade {args.target_grade}",
        f"**Type combat** : {args.combat_type} (base XP = {base_xp})",
        f"**Power ratio** : {args.power_ratio} (1.0 = équilibré)",
        "",
    ]

    if "error" in case:
        lines.append(f"❌ {case['error']}")
    else:
        lines.extend([
            "## Résultat",
            "",
            f"- XP requise totale : **{case['xp_required']}**",
            f"- XP par combat : {case['xp_per_combat']}",
            f"- **Combats nécessaires : {case['combats_needed']}**",
            "",
        ])

    # Tableau comparatif
    lines.extend([
        "## Comparaison par ratio de puissance (Grade 0 → 5)",
        "",
        f"Type combat : {args.combat_type} (base XP = {base_xp})",
        "",
        "| Power ratio | XP/combat | Combats requis | Verdict |",
        "|---:|---:|---:|---|",
    ])
    full_xp = _GRADE_THRESHOLDS[5]
    for ratio in [0.5, 1.0, 1.5, 2.0, 3.0, 5.0]:
        xp_per = differential_xp(base_xp, ratio)
        combats = full_xp // xp_per + (1 if full_xp % xp_per else 0)
        if combats <= 100:
            verdict = "✅ Rapide"
        elif combats <= 400:
            verdict = "OK"
        elif combats <= 800:
            verdict = "⚠️ Long"
        else:
            verdict = "❌ Trop long"
        lines.append(f"| {ratio} | {xp_per} | {combats} | {verdict} |")

    lines.extend([
        "",
        "## Tableau de référence par type de combat",
        "",
        "| Type combat | Base XP | À ratio 1.0 | À ratio 3.0 |",
        "|---|---:|---:|---:|",
    ])
    for ct, bxp in _BASE_XP.items():
        c1 = full_xp // differential_xp(bxp, 1.0)
        c3 = full_xp // differential_xp(bxp, 3.0)
        lines.append(f"| {ct} | {bxp} | {c1} | {c3} |")

    lines.extend([
        "",
        "## Verdict design",
        "",
        "- À **ratio 1.0** (combat équilibré) : ATTACK_WIN demande ~400 combats. **OK pour rétention**, ni trop court ni grindy.",
        "- À **ratio 3.0** (combat audacieux) : ~67 combats. **Excellent — encourage l'audace.**",
        "- À **ratio 5.0** (combat extrême) : ~37 combats. **Rare en pratique mais valorisé.**",
        "- À **ratio < 1.0** (sandbag) : XP plancher 100. **Décourage le farm de newbies.** ✅",
        "",
        "Si simulation suggère > 1000 combats type ATTACK_WIN à ratio 1.0 → grind trop punitif → revoir base XP.",
    ])

    md = "\n".join(lines)

    if args.output:
        args.output.write_text(md, encoding="utf-8")
        print(f"✅ Rapport : {args.output}", file=sys.stderr)
    else:
        print(md)


if __name__ == "__main__":
    main()
