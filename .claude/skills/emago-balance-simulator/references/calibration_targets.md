# Cibles de calibrage Emago

Fourchettes acceptables pour valider qu'un changement d'équilibrage tient.

## Combats — fourchettes par scénario

### Scénario 1 : Match symétrique

**Setup** : 3 ships ATTACK COMMON Grade 0 vs 3 ships ATTACK COMMON Grade 0.

| Indicateur | Cible | Tolérance |
|---|---|---|
| Winrate ATTACKER | 50 % | ± 5 % (RNG combat) |
| Winrate DEFENDER | 50 % | ± 5 % |
| Winrate DRAW | < 5 % | (rare avec compositions équilibrées) |
| Rounds moyens | 5-10 | |
| Cicatrices générées | 0-10 % | (pas asymétrique) |

### Scénario 2 : Match avec synergie ATT+SUP

**Setup** : 3 ATTACK COMMON + 1 SUPPORT COMMON vs 3 ATTACK COMMON.

| Indicateur | Cible |
|---|---|
| Winrate côté avec SUPPORT | 60-70 % |
| Synergies appliquées au log | "ATTACK+SUPPORT: +20% DPS" présent |

### Scénario 3 : Match grade vs sans grade

**Setup** : 1 ATTACK Grade 5 vs 5 ATTACK Grade 0 (équivalent power).

| Indicateur | Cible |
|---|---|
| Winrate Grade 5 | 60-75 % (cap +150 % limite la suprématie) |
| Immunité Grade 4 utilisée | si applicable Grade 4 |
| XP gagnée par survivants | élevée si Grade 5 perd quand-même |

### Scénario 4 : Légendaire vs essaim

**Setup** : 1 ATTACK LEGENDARY Grade 5 + 6 modules CANNON V vs 50 ATTACK COMMON Grade 0.

| Indicateur | Cible |
|---|---|
| Winrate LEGENDARY | 75-95 % |
| `cap_reached` contient `dps` | dans 100 % des cas |
| Rounds moyens | 30-50 (peut atteindre max 50) |
| Le LEGENDARY survit | dans 80-100 % des victoires |
| Cicatrice générée pour LEGENDARY | 50-90 % (combat difficile contre essaim) |

### Scénario 5 : Sandbag (battre +faible)

**Setup** : 5 ATTACK COMMON G0 vs 1 ATTACK COMMON G0.

| Indicateur | Cible |
|---|---|
| Winrate attacker | > 95 % |
| XP gagnée par attaquant | ~80 (base ATTACK_WIN_LOOT, plancher car ratio < 1) |
| Verdict design | XP désavantageuse → décourage farm |

### Scénario 6 : Audacieux (attaquer +fort)

**Setup** : 5 ATTACK COMMON G0 vs 15 ATTACK COMMON G0.

| Indicateur | Cible |
|---|---|
| Winrate attacker | < 30 % (audacieux mais difficile) |
| Si victoire, XP gagnée | ~350 (base × 3.5 selon ratio 3×) |
| Verdict design | XP énorme si réussite → encourage l'audace |

## Distribution RNG — fourchettes acceptables

Sur N = 10 000 builds :

| Rareté | Cible | Fourchette acceptable |
|---|---:|---|
| COMMON | 5 500 (55 %) | [5 250, 5 750] (52.5-57.5 %) |
| UNCOMMON | 2 700 (27 %) | [2 500, 2 900] |
| RARE | 1 200 (12 %) | [1 050, 1 350] |
| EPIC | 500 (5 %) | [400, 600] |
| LEGENDARY | 100 (1 %) | [70, 130] |

Sur N = 100 000 builds (plus précis) :

| Rareté | Cible | Fourchette acceptable |
|---|---:|---|
| COMMON | 55 000 | [54 500, 55 500] (54.5-55.5 %) |
| LEGENDARY | 1 000 | [900, 1 100] |

Si écart > fourchette → vérifier `secrets.SystemRandom()` (pas `random.random()`).

## Drift distribution

Sur N = 1000 forges :

| Indicateur | Cible | Fourchette |
|---|---:|---|
| % drift | 5 % (50 sur 1000) | [3.5, 6.5] % (35-65 sur 1000) |
| Stat impactée | uniforme parmi hull/shield/dps/speed | < 30 % par stat |
| `is_drift = True` flag | présent | toutes les forges drift |
| ShipScar `born_in_drift` | présent | toutes les forges drift |

## XP progression Grade 0 → 5

Total XP requise : 40 000.

### Match symétrique (ratio = 1.0)

XP par combat : `base × (1 + 0) = base`.

| Type combat | XP/combat | Combats requis |
|---|---:|---:|
| ATTACK_WIN | 100 | 400 |
| DEFENSE_WIN | 150 | 267 |
| ATTACK_WIN_LOOT | 80 | 500 |
| LOSS_SURVIVOR | 40 | 1000 |

### Combat audacieux (ratio = 3.0)

XP : `base × (1 + 5.0) = base × 6`.

| Type combat | XP/combat | Combats requis |
|---|---:|---:|
| ATTACK_WIN | 600 | 67 |
| DEFENSE_WIN | 900 | 45 |

### Combat audacieux (ratio = 5.0)

XP : `base × (1 + 10.0) = base × 11`.

| Type combat | XP/combat | Combats requis |
|---|---:|---:|
| ATTACK_WIN | 1100 | 37 |

## Forge progression

### Probabilité d'obtenir un LEGENDARY

**Direct au build** : 1 % par tirage. Pour avoir au moins 1 LEGENDARY au bout de N builds :
- N = 50 : 39.5 %
- N = 100 : 63.4 %
- N = 200 : 86.6 %
- N = 500 : 99.3 %

**Via forge** :
- Pour forger LEGENDARY, il faut 2 EPIC.
- Probabilité d'EPIC au build : 5 %.
- Espérance : 1 EPIC tous les 20 builds, 2 EPIC tous les ~40 builds (cumulatif).
- Avec ressources illimitées, ~40 builds + 1 forge = 1 LEGENDARY garanti via fusion.
- En réalité ressources limitées → coût-opportunité significatif.

### Drift après 100 forges

Espérance : 5 forges drift sur 100. Std : √(100 × 0.05 × 0.95) ≈ 2.18.
Fourchette ±2σ : [0.6, 9.4] → typiquement 1 à 9 drifts.

## Cap stats — fourchette d'usage

Sur un ship optimal (LEGENDARY G5 + 6 modules CANNON V) :

| Stat | Base | Avec grade ×1.30 | Avec modules CANNON V × 6 | Cap |
|---|---:|---:|---:|---:|
| dps (ATTACK base 80) | 80 | 104 | 104 + 80 × 6×0.506 = 348 | min(348, 200) = **200** |
| → cap_reached | | | | ✅ `["dps"]` |

Le cap +150 % limite à 80 × 2.5 = 200.

## Rétention vs progression

| Activité | Fréquence cible | Justification |
|---|---|---|
| Daily login | 1×/jour | Récompense streak |
| Combat audacieux | 1-2/jour | XP × 5-10 |
| Build vaisseau | 2-5/jour | Continuité gameplay |
| Lancer forge | 1/2 jours | Forge dure 8h |
| Lancer expé | 1/jour | Variable selon durée |
| Connexion totale | ~30 min/jour | Cohérent avec flow casual |

Si simulation suggère qu'on doit être en ligne > 1h/jour pour progresser → grind trop punitif → ajuster.

## Économie

### Inflation ressources

Sur 24h sans dépense :
- Mine de métal niv 5 : 30 × 5 × 1.1^5 = 241/h × 24 = 5800 métal/jour.
- Mine de cristal niv 5 : 121/h × 24 = 2900/jour.
- Mine de deut niv 5 : 40/h × 24 = 970/jour.

→ Un joueur passif accumule ~9700 ressources/jour.

### Coût d'un ship

`frigate_attack` = 4000 ressources. → 1 ship par jour pour un joueur passif niv 5 mines.

`cruiser_attack` = 29 000 ressources. → ~3 jours.

`forge frigate_attack` = 12 000. → 1.2 jours.

→ Ratio progression cohérent avec sessions quotidiennes courtes.

## Verdicts attendus

| Scénario | Action si écart |
|---|---|
| Winrate symétrique != 50 ± 5 % | bug dans le combat engine → STOP |
| Distribution RNG hors fourchette | bug RNG → STOP |
| LEGENDARY G5 winrate > 95 % vs essaim | cap inefficace → revoir _STAT_CAP_RATIO |
| Drift % hors [3.5, 6.5] | bug `_DRIFT_PROBABILITY` |
| XP progression > 1000 combats équilibrés | trop grindy → augmenter base XP ou diff_factor |
| Cap_reached jamais atteint | modules trop faibles → revoir _MODULE_BOOST |
| Synergies sans effet visible | bug synergie engine |
