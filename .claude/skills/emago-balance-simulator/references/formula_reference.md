# Formules Emago — référence

## Génération stats à la construction

```
stat_finale = base × rarity_mult + uniform(-0.10, +0.10) × (base × rarity_mult)
            = base × rarity_mult × (1 + uniform(-0.10, +0.10))
```

Exemple : ATTACK Légendaire hull = 100 × 2.40 × (1 + ±0.10) = 240 × [0.90, 1.10] = [216, 264].

Arrondi :
- speed → 1 décimale
- stealth, support_aura → 2 décimales (cap 100)
- hull, shield, dps, cargo → entier (`max(0, round(...))`)

## Pedigree

```
boosted_stat = parent_best_stat × 1.05
```

Conditions :
- Parent.grade ≥ 3.
- Parent.ship_type == new_ship.ship_type.
- Parent.status == DOCKED.
- `find_best_stat` exclut `stealth` et `support_aura`.

## Current stats (combat-ready)

```
# Étape 1 : base + bonus grade
after_grade[stat] = base[stat] × (1 + GRADE_BONUS[grade])
if grade == 5:
    after_grade["stealth"] = min(100, after_grade["stealth"] + 10)

# Étape 2 : modules
for module in modules:
    affinity = (module.type matches class)
    boost = MODULE_BOOST[level] × (AFFINITY_MULT if affinity else 1.0)
    boost_ratio[stat] += boost

# Étape 3 : application
target = after_grade[stat] + base[stat] × boost_ratio[stat]
cap_value = base[stat] × 2.5  # +150 % au-dessus de la base
final[stat] = min(target, cap_value)
if target > cap_value:
    cap_reached.append(stat)
```

> **Important** : le cap +150 % est sur la BASE, pas sur la stat post-grade. Donc un Légendaire Grade 5 avec base hull = 240 a un cap à 240 × 2.5 = 600.

## Power d'une flotte

```
power = max(1.0, Σ (dps × hull_max × (1 + shield_max / hull_max)))
```

Pour 1 ship : ATTACK COMMON typique :
- dps = 80, hull = 100, shield = 20
- power = 80 × 100 × (1 + 20/100) = 9600

## Synergies de classe (appliquées AVANT les rounds)

```python
n_attack = count(class == ATTACK)
n_defense = count(class == DEFENSE)
n_support = count(class == SUPPORT)
n_exploration = count(class == EXPLORATION)
total = len(fleet)

# ATTACK + SUPPORT : +20 % DPS pour les ATTACK
if n_attack > 0 and n_support > 0:
    for ship in fleet:
        if ship.class == ATTACK:
            ship.dps *= 1.20

# DEFENSE × 3+ : +15 % shield collectif
if n_defense >= 3:
    for ship in fleet:
        if ship.class == DEFENSE:
            ship.shield_max *= 1.15
            ship.shield = min(ship.shield, ship.shield_max)  # rééquilibrer

# DEFENSE + SUPPORT : hull regen 5%/round (DEFENSE alive)
if n_defense > 0 and n_support > 0:
    bonus["hull_regen"] = 0.05  # appliqué dans _resolve_round

# ATTACK + EXPLORATION ≥ 20% : +10 % vitesse flotte (loggé, pas appliqué en combat)
if n_attack > 0 and (n_exploration / total) >= 0.20:
    log("ATTACK+EXPLORATION: +10% speed")
```

## Round combat

```python
for ship_attaquant in fleet_a.alive:
    target = rng.choice(fleet_b.alive)
    raw_dps = ship_attaquant.dps × rng.uniform(0.90, 1.10)
    effective_dps = int(raw_dps × (1 + support_aura_total_a / 100))
    target.take_damage(effective_dps)

# take_damage :
def take_damage(raw_dmg):
    shield_absorbed = min(self.shield, raw_dmg)
    self.shield -= shield_absorbed
    hull_dmg = raw_dmg - shield_absorbed
    self.hull = max(0, self.hull - hull_dmg)
    if self.hull == 0:
        if self.grade >= 4 and not self.immunity_used:
            self.hull = 1
            self.immunity_used = True
        else:
            self.alive = False

# Régen post-round (Grade 3+)
for ship in fleet.alive:
    regen = int(ship.shield_max × ship.shield_regen)
    ship.shield = min(ship.shield_max, ship.shield + regen)

# Hull regen synergie DEFENSE+SUPPORT (DEFENSE alive uniquement)
if synergy_def_sup_active:
    for ship in defense_ships.alive:
        repair = int(ship.hull_max × 0.05)
        ship.hull = min(ship.hull_max, ship.hull + repair)
```

## XP différentielle

```python
ratio = enemy_power / own_power
diff_factor = max(0.0, ratio - 1.0) × 2.5
xp_final = int(base_xp × (1 + diff_factor))
```

| Cas | ratio | diff_factor | XP (base 100) |
|---|---:|---:|---:|
| Equal | 1.0 | 0.0 | 100 |
| 2× plus fort | 2.0 | 2.5 | 350 |
| 3× plus fort | 3.0 | 5.0 | 600 |
| 5× plus fort | 5.0 | 10.0 | 1100 |
| 0.5× (plus faible) | 0.5 | 0.0 | 100 (plancher) |
| 0.1× (très faible) | 0.1 | 0.0 | 100 |

## Cicatrices — conditions

```python
def should_earn_scar(ship, enemy_power, own_power):
    if not ship.alive:
        return False
    hull_loss_ratio = (ship.hull_start - ship.hull) / max(ship.hull_start, 1)
    if hull_loss_ratio >= 0.75:
        return True
    power_ratio = enemy_power / max(own_power, 1.0)
    if power_ratio >= 2.0:
        return True
    return False
```

## Forge — fusion

```python
new_base_stats = {k: max(stats_a[k], stats_b[k]) for k in stats_a.keys() | stats_b.keys()}

# Drift (5%)
if random() < 0.05:
    drift_stat = random_choice([s for s in DRIFT_ELIGIBLE_STATS if s in new_base_stats])
    new_base_stats[drift_stat] *= 0.80
    is_drift = True
    # + INSERT ShipScar tag "born_in_drift"

new_rarity = RARITY_UPGRADE[rarity]  # COMMON→UNCOMMON, etc.
new_xp = int(max(xp_a, xp_b) × 0.30)
new_grade = 0
new_name = generate_ship_name(class, new_rarity)  # RARE+
new_trait = roll_trait()  # tous

# Coût = 3 × build cost
cost = {k: SHIP_TYPE_BUILD_COST[ship_type][k] × 3 for k in cost_keys}
```

## Forge fenêtre temporelle

```
started_at = now()
completed_at = now() + 8 hours
```

## Distribution rareté (cumulative)

```python
r = secrets.SystemRandom().random()  # ∈ [0, 1)

if r < 0.55: COMMON
elif r < 0.82: UNCOMMON
elif r < 0.94: RARE
elif r < 0.99: EPIC
else: LEGENDARY
```

Probabilités exactes :
- COMMON : 55 %
- UNCOMMON : 27 %
- RARE : 12 %
- EPIC : 5 %
- LEGENDARY : 1 %

## Resource tick (production)

```python
def _mine_output(base_rate, level):
    if level <= 0:
        return 0.0
    return base_rate × level × (1.1 ** level)

# Énergie
energy_produced = _mine_output(20.0, solar_level)
energy_need = 10*metal_level + 10*crystal_level + 20*deut_level
energy_factor = min(1.0, energy_produced / energy_need) if energy_need > 0 else 1.0

# Production effective
metal_produced = _mine_output(30.0, metal_level) × elapsed_hours × energy_factor
crystal_produced = _mine_output(15.0, crystal_level) × elapsed_hours × energy_factor
deut_produced = _mine_output(5.0, deut_level) × elapsed_hours × energy_factor

# Cap par capacité
planet.metal = min(metal_capacity, planet.metal + metal_produced)
# (idem)
```

## Capacité par défaut planète natale

```python
metal_capacity = 10_000
crystal_capacity = 10_000
deut_capacity = 5_000

# Stocks initiaux
metal = 500
crystal = 300
deuterium = 100
```
