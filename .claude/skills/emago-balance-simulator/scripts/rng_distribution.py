#!/usr/bin/env python3
"""
emago-balance-simulator / rng_distribution.py

Vérifie que la distribution de rareté tirée par secrets.SystemRandom().random()
respecte les thresholds Emago (55/27/12/5/1).

Usage :
    python scripts/rng_distribution.py [--iterations 10000] [--output dist.md]
"""
from __future__ import annotations

import argparse
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

_TARGETS = {
    "COMMON":    0.55,
    "UNCOMMON":  0.27,
    "RARE":      0.12,
    "EPIC":      0.05,
    "LEGENDARY": 0.01,
}

_TOLERANCE = 0.05  # ± 5 % par catégorie


def roll_rarity() -> str:
    r = secrets.SystemRandom().random()
    for rarity, threshold in _RARITY_THRESHOLDS:
        if r < threshold:
            return rarity
    return "LEGENDARY"


def main():
    parser = argparse.ArgumentParser(description="Distribution rareté Emago.")
    parser.add_argument("--iterations", type=int, default=10000)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    print(f"Tirage de {args.iterations} raretés…", file=sys.stderr)
    counts = Counter(roll_rarity() for _ in range(args.iterations))

    lines = [
        "# Distribution rareté Emago",
        "",
        f"**Iterations** : {args.iterations}",
        f"**Méthode** : `secrets.SystemRandom().random()` (non prédictible)",
        "",
        "| Rareté | Compte | % | Cible | Δ | OK ? |",
        "|---|---:|---:|---:|---:|---|",
    ]

    all_ok = True
    for rarity in ["COMMON", "UNCOMMON", "RARE", "EPIC", "LEGENDARY"]:
        count = counts.get(rarity, 0)
        pct = count / args.iterations
        target = _TARGETS[rarity]
        delta = pct - target
        within_tolerance = abs(delta) <= _TOLERANCE
        if not within_tolerance:
            all_ok = False
        ok = "✅" if within_tolerance else "❌"
        lines.append(
            f"| {rarity} | {count} | {pct*100:.2f} % | {target*100:.0f} % | "
            f"{delta*100:+.2f} % | {ok} |"
        )

    lines.extend([
        "",
        "## Verdict",
        "",
    ])

    if all_ok:
        lines.append(f"✅ **Distribution conforme** — toutes les catégories dans la tolérance ±{_TOLERANCE*100:.0f} %.")
    else:
        lines.append(f"❌ **Écart détecté** — au moins une catégorie hors tolérance ±{_TOLERANCE*100:.0f} %.")
        lines.append("")
        lines.append("**Causes possibles** :")
        lines.append("- `random.random()` utilisé au lieu de `secrets.SystemRandom().random()` (biaisé).")
        lines.append("- Thresholds modifiés sans mise à jour de _RARITY_THRESHOLDS.")
        lines.append("- Itérations insuffisantes pour LEGENDARY (1 % → besoin de N ≥ 10 000 pour précision).")

    md = "\n".join(lines)

    if args.output:
        args.output.write_text(md, encoding="utf-8")
        print(f"✅ Rapport : {args.output}", file=sys.stderr)
    else:
        print(md)


if __name__ == "__main__":
    main()
