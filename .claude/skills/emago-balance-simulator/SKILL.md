---
name: emago-balance-simulator
description: Simule des combats Emago, des distributions RNG de rareté, et des progressions XP/grade pour vérifier l'équilibrage du jeu. Reproduit fidèlement les formules de combat_engine.py — synergies de classe (ATTACK+SUPPORT DPS×1.20, DEFENSE×3+ shield×1.15, DEFENSE+SUPPORT hull regen 5%/round), XP différentielle base × (1 + max(0, ratio-1) × 2.5), cap +150% par stat, immunité Grade 4 (rebond à 1 HP), max 50 rounds, scar conditions (75% hull loss OR enemy ≥2× power). Sort des stats agrégées sur N tirages : winrate, rounds moyens, distribution rareté, drift probability, XP gain. Use when l'utilisateur dit "équilibrage Emago", "simule un combat", "Légendaire vs Communs", "distribution rareté", "test balance", "RNG Emago", "vérifie équilibre", "balance check forge".
license: MIT
metadata:
  author: Antoine
  version: 1.0.0
  project: emago
  agent: 2-game-designer
---

# emago-balance-simulator

Donne confiance dans l'équilibrage avant chaque tweak GDD. Encapsule la logique de simulation des combats Emago avec les formules exactes du backend.

---

## Quand utiliser ce skill

- Avant de modifier une constante d'équilibrage (`_RARITY_MULT`, `_GRADE_BONUS`, `_MODULE_BOOST`, etc.).
- Pour répondre à une question de design type "un Légendaire Grade 5 peut-il battre 50 Communs ?".
- Pour vérifier qu'une nouvelle synergie ne déséquilibre pas le jeu.
- Pour valider la distribution RNG (rareté tirée, Drift 5 %, XP gain).
- Avant un patch d'équilibrage en prod.

## Quand NE PAS utiliser ce skill

- Pour exécuter le vrai combat_engine en BDD → utiliser un test d'intégration via `emago-test-integration-writer`.
- Pour la perf du combat (latence, throughput) → utiliser k6/locust.
- Pour designer une nouvelle mécanique (pas de simulation possible si elle n'existe pas) → utiliser `emago-gdd-writer`.

---

## Constantes à respecter (à jour, code de production)

Source : `app/services/combat_engine.py`, `ship_stats_service.py`, `ship_build_service.py`, `forge_service.py`.

| Constante | Valeur | Source |
|---|---|---|
| Distribution rareté | COMMON 55%, UNCOMMON 27%, RARE 12%, EPIC 5%, LEGENDARY 1% | `_RARITY_THRESHOLDS` |
| Multiplier rareté | 1.0 / 1.25 / 1.55 / 1.90 / 2.40 | `_RARITY_MULT` |
| Slots (total, premium) | (2,0) / (3,0) / (4,1) / (5,2) / (6,3) | `_RARITY_SLOTS` |
| Variance build | uniform(-10%, +10%) | `generate_base_stats` |
| Cap stat | × 2.5 (= +150 %) | `_STAT_CAP_RATIO` |
| Bonus grade | 0/5/10/15/22/30 % | `_GRADE_BONUS` |
| Shield regen | 0/0/0/2/2/2 % par round | `GRADE_SHIELD_REGEN` |
| Grade 5 stealth | +10 % absolu (cap 100) | `GRADE_5_STEALTH_BONUS` |
| Module boosts (I-V) | 8/14/22/32/44 % | `_MODULE_BOOST` |
| Affinity | × 1.15 | `_AFFINITY_MULT` |
| XP diff factor | `× (1 + max(0, ratio-1) × 2.5)` | `_compute_differential_xp` |
| Base XP | ATTACK_WIN 100, DEFENSE_WIN 150, LOSS_SURVIVOR 40, ATTACK_WIN_LOOT 80 | `_BASE_XP` |
| Grade thresholds | 500 / 2000 / 6000 / 15000 / 40000 | `_GRADE_THRESHOLDS` |
| Synergie ATT+SUP | DPS × 1.20 | `_compute_synergy_bonuses` |
| Synergie DEF+SUP | hull regen 5%/round | idem |
| Synergie DEF×3+ | shield_max × 1.15 | idem |
| Cicatrice hull | seuil ≥ 75 % perdue | `SCAR_HULL_LOSS_THRESHOLD` |
| Cicatrice power | seuil enemy ≥ 2× | `SCAR_POWER_RATIO_THRESHOLD` |
| Grade 4 immunité | rebond à 1 HP | `GRADE_4_IMMUNITY_HP` |
| Max rounds combat | 50 | `MAX_ROUNDS` |
| Forge XP transfer | 30 % du max | `_XP_TRANSFER_RATIO` |
| Drift probability | 5 % | `_DRIFT_PROBABILITY` |
| Drift impact | stat × 0.80 | `apply_drift` |
| Forge cost | × 3 du build | `start_forge` |

**Si une de ces constantes change**, mettre à jour le script `scripts/simulate_combat.py` AVANT de simuler.

---

## Instructions

### Étape 1 — Cadrer la simulation

Demande à l'utilisateur :

1. **Type** :
   - **Combat** : 2 flottes vs.
   - **RNG distribution** : N tirages de rareté, vérifier conformité.
   - **Forge progression** : prob. d'obtenir un LEGENDARY au bout de K builds + forges.
   - **Drift distribution** : N forges, comptez les is_drift.
   - **XP progression** : combien de combats type X pour atteindre Grade Y ?

2. **Inputs** :
   - Combat : composition flotte attaquante (N ships avec class/rarity/grade/modules), même chose défenseur, nombre d'itérations (défaut 1000).
   - RNG distribution : N (défaut 10 000).
   - Forge progression : nombre builds + forges, rareté de départ.
   - XP : grade de départ, type de combat (ATTACK_WIN, DEFENSE_WIN, LOSS_SURVIVOR), puissance ratio.

3. **Format de sortie** : markdown / JSON / CSV.

### Étape 2 — Lancer la simulation

```bash
# Combat
python scripts/simulate_combat.py \
  --attacker '<json composition>' \
  --defender '<json composition>' \
  --iterations 1000 \
  --output report.md

# RNG distribution
python scripts/rng_distribution.py --iterations 10000 --output dist.md

# Forge progression
python scripts/forge_progression.py --start-rarity COMMON --target LEGENDARY --iterations 1000

# XP progression
python scripts/xp_progression.py --start-grade 0 --target-grade 5 --combat-type ATTACK_WIN_LOOT --power-ratio 1.5
```

### Étape 3 — Interpréter

#### Combat

- **Winrate** : 40-60 % = équilibré. > 75 % = un côté domine. < 25 % = un côté écrasé.
- **Rounds moyens** : 5-15 = sain. > 30 = combats trop longs (DPS trop bas ou hull trop élevé). 50 (= max) = combats interminables (problème).
- **XP moyenne par côté** : doit refléter la difficulté. Battre +fort → +XP via différentielle.
- **Cicatrices générées** : si > 50 % des combats donnent une cicatrice, le jeu est trop punitif.
- **Cap reached** : si beaucoup de stats cap_reached = build trop optimal, peut-être refacto modules.

#### Distribution RNG

- COMMON ∈ [50, 60] % (cible 55 % ± 5).
- UNCOMMON ∈ [22, 32] %.
- RARE ∈ [9, 15] %.
- EPIC ∈ [3, 7] %.
- LEGENDARY ∈ [0.5, 1.5] %.

Si écart > tolérance → vérifier `secrets.SystemRandom()` (jamais `random.random()`) et thresholds.

#### Forge progression

Probabilité d'obtenir un LEGENDARY direct au build : 1 %.
Probabilité par forge depuis 2 EPIC : 100 % (déterministe).
Calcul : combien de cycles build → forge cumulatifs pour avoir un LEGENDARY ?

#### Drift distribution

Sur 1000 forges, attendu ~50 drift (5 %). Si écart > 10 → vérifier `_DRIFT_PROBABILITY`.

#### XP progression

Combien de combats type X pour passer Grade 0 → Grade 5 (40 000 XP) ?
- ATTACK_WIN base 100 vs équivalent : 400 combats.
- ATTACK_WIN base 100 vs 3× plus fort : 80 combats (XP × 5).
- DEFENSE_WIN base 150 : 267 combats à parité.

### Étape 4 — Recommandation GDD

Selon les résultats :
- ✅ **Équilibré** : pas d'action, on peut merger.
- ⚠️ **Marginal** : noter dans le rapport, à surveiller en prod (logs combats).
- ❌ **Déséquilibré** : proposer ajustement constante (ex. `_RARITY_MULT[LEGENDARY] = 2.30` au lieu de 2.40).

Toujours documenter le raisonnement dans `docs/02_game_designer.md` ou un ADR (`emago-adr-writer`).

### Étape 5 — Mettre à jour les tests

Si la simulation révèle un cas limite intéressant (ex. Légendaire Grade 5 winrate 87 %), ajouter un test d'intégration correspondant pour anti-régression.

```python
# tests/services/test_balance.py
@pytest.mark.asyncio
async def test_legendary_g5_vs_50_commons():
    # Run 100 simulations
    winrates = []
    for _ in range(10):
        result = await simulate_combat(...)
        winrates.append(result["attacker_winrate"])
    assert 0.75 <= np.mean(winrates) <= 0.95
```

---

## Examples

### Exemple 1 — "Légendaire Grade 5 vs essaim Communs"

**User** : "Simule un Légendaire Grade 5 ATTACK avec 6 modules CANNON V vs 50 Communs Grade 0 frigate_attack"

**Actions** :
1. Compose les flottes :
   - Attaquant : 1 ship LEGENDARY + grade 5 + 6 modules CANNON V.
   - Défenseur : 50 ships COMMON + grade 0 + 0 modules.
2. Run 1000 itérations.
3. Mesure winrate Légendaire (typiquement > 80 % grâce au cap +150 %).
4. Vérifie que le cap stat limite le DPS du Légendaire (`cap_reached: ['dps']` dans tous les rapports).
5. Conclut : "Équilibre OK — Légendaire écrase mais pas d'one-shot, perd toujours du shield/hull dans le combat."

### Exemple 2 — Distribution RNG

**User** : "Vérifie que le tirage rareté respecte 55/27/12/5/1 sur 100 000 builds"

**Actions** :
1. Run 100 000 tirages via `secrets.SystemRandom().random()`.
2. Compte par catégorie selon thresholds.
3. Sort tableau :
   ```
   COMMON   : 55 023 (55.02 %)  ✅ cible 55 %
   UNCOMMON : 26 988 (26.99 %)  ✅ cible 27 %
   RARE     : 12 014 (12.01 %)  ✅ cible 12 %
   EPIC     :  4 991 ( 4.99 %)  ✅ cible 5 %
   LEGENDARY:    984 ( 0.98 %)  ✅ cible 1 %
   ```
4. Verdict : distribution conforme.

### Exemple 3 — Évaluation modification constante

**User** : "Si on change `_RARITY_MULT[LEGENDARY]` de 2.40 à 2.20, qu'est-ce que ça donne sur un combat équilibré ?"

**Actions** :
1. Run 1000 simulations Légendaire vs Légendaire avec mult=2.40 (baseline).
2. Run 1000 simulations avec mult=2.20.
3. Compare winrate (devrait rester ~50/50 puisque les 2 côtés ont la même rareté).
4. Compare rounds moyens (l'effet du nerf est moins visible en match symétrique).
5. Run 1000 LEGENDARY vs 5 EPIC pour mesurer l'écart.
6. Recommandation : nerf valide ou pas selon le résultat.

---

## Troubleshooting

### Le winrate est 100 % pour un côté

**Cause probable** : le cap stat n'est pas appliqué dans la simulation.
**Solution** : vérifier que `_STAT_CAP_RATIO = 1.50` est utilisé, et que le calcul fait bien `min(target, base × 2.5)`.

### Distribution RNG hors fourchette

**Cause** : code utilise `random.random()` au lieu de `secrets.SystemRandom()`.
**Solution** : `import secrets; _srng = secrets.SystemRandom(); _srng.random()`.

### Drift à 0 % ou 100 %

**Cause** : `_DRIFT_PROBABILITY` mal lu ou comparé inversement.
**Solution** : vérifier `_srng.random() < 0.05` (et non `> 0.05`).

### Combats qui durent toujours 50 rounds

**Cause** : DPS trop bas ou hull trop élevé.
**Solution** : vérifier les stats de base (cf. `_BASE_STATS_BY_CLASS`), ajuster ou identifier que la composition n'a pas assez de DPS pour réduire l'autre.

### XP gain non symétrique

**Cause** : oubli de `max(0, ratio-1)` qui fait que ratio < 1 donne diff_factor négatif.
**Solution** : `diff_factor = max(0.0, ratio - 1.0) × 2.5` strictement.

### Score équilibrage incohérent avec le jeu

**Cause** : la simulation ne prend pas en compte les traits narratifs (~200 traits avec +5-16 % conditionnel).
**Solution** : actuellement les traits ne sont pas dans le moteur `combat_engine` (uniquement `apply_trait_bonus` exposé), donc le code de production a la même limitation. Le script reflète cet état. À enrichir Phase 2 quand les traits seront intégrés en combat.

---

## References

- `references/balance_constants.md` — toutes les constantes Emago avec leur source code.
- `references/formula_reference.md` — formules détaillées avec dérivation.
- `references/calibration_targets.md` — fourchettes acceptables par cas (winrate, rounds, etc.).

## Scripts

- `scripts/simulate_combat.py` — moteur de simulation combat (réimplémente combat_engine).
- `scripts/rng_distribution.py` — distribution rareté.
- `scripts/forge_progression.py` — probabilité LEGENDARY au bout de K cycles.
- `scripts/xp_progression.py` — combats requis pour Grade Y.
