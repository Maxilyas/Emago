# Constantes d'équilibrage Emago

Source de vérité : code de production. Tout changement doit être propagé ici ET dans `docs/02_game_designer.md` section 16.

## Rareté — `ship_build_service.py`

```python
_RARITY_THRESHOLDS = [
    (ShipRarity.COMMON,    0.55),
    (ShipRarity.UNCOMMON,  0.82),
    (ShipRarity.RARE,      0.94),
    (ShipRarity.EPIC,      0.99),
    (ShipRarity.LEGENDARY, 1.00),
]

_RARITY_MULT = {
    "COMMON":    1.00,
    "UNCOMMON":  1.25,
    "RARE":      1.55,
    "EPIC":      1.90,
    "LEGENDARY": 2.40,
}

_RARITY_SLOTS = {
    "COMMON":    (2, 0),
    "UNCOMMON":  (3, 0),
    "RARE":      (4, 1),
    "EPIC":      (5, 2),
    "LEGENDARY": (6, 3),
}
```

## Stats de base par classe — `ship_build_service.py`

```python
_BASE_STATS_BY_CLASS = {
    "ATTACK":      {"hull": 100, "shield": 20,  "dps": 80, "speed": 45,  "cargo": 200,  "stealth": 0,  "support_aura": 0},
    "DEFENSE":     {"hull": 350, "shield": 120, "dps": 15, "speed": 15,  "cargo": 500,  "stealth": 0,  "support_aura": 0},
    "SUPPORT":     {"hull": 150, "shield": 40,  "dps": 8,  "speed": 30,  "cargo": 1000, "stealth": 0,  "support_aura": 15},
    "EXPLORATION": {"hull": 80,  "shield": 15,  "dps": 12, "speed": 90,  "cargo": 3000, "stealth": 25, "support_aura": 0},
}
```

## Coûts construction — `ship_build_service.py`

```python
SHIP_TYPE_BUILD_COST = {
    "frigate_attack":      {"metal": 3000,  "crystal": 1000, "deuterium": 0},
    "frigate_defense":     {"metal": 6000,  "crystal": 2000, "deuterium": 0},
    "frigate_support":     {"metal": 2000,  "crystal": 2000, "deuterium": 500},
    "frigate_exploration": {"metal": 2000,  "crystal": 1000, "deuterium": 1000},
    "cruiser_attack":      {"metal": 20000, "crystal": 7000, "deuterium": 2000},
    "cruiser_defense":     {"metal": 30000, "crystal": 10000,"deuterium": 2000},
}

SHIP_SHIPYARD_REQUIREMENTS = {
    "frigate_attack": 1,
    "frigate_defense": 1,
    "frigate_support": 1,
    "frigate_exploration": 2,
    "cruiser_attack": 4,
    "cruiser_defense": 4,
}
```

## Modules — `ship_stats_service.py`

```python
_MODULE_BOOST = {1: 0.08, 2: 0.14, 3: 0.22, 4: 0.32, 5: 0.44}
_AFFINITY_MULT = 1.15
_PREMIUM_REQUIRED_LEVELS = {4, 5}

_MODULE_EFFECT = {
    "PROPELLER": {"stat": "speed",        "affinity_class": "EXPLORATION"},
    "ARMOR":     {"stat": "hull",         "affinity_class": "DEFENSE"},
    "CANNON":    {"stat": "dps",          "affinity_class": "ATTACK"},
    "EMITTER":   {"stat": "support_aura", "affinity_class": "SUPPORT"},
    "SHIELD":    {"stat": "shield",       "affinity_class": "DEFENSE"},
    "CARGO":     {"stat": "cargo",        "affinity_class": "EXPLORATION"},
}
```

## Cap & grades — `ship_stats_service.py`

```python
_STAT_CAP_RATIO = 1.50  # +150% au-dessus de base → cap = base × 2.5

_GRADE_BONUS = {
    0: 0.00,
    1: 0.05,  # +5%
    2: 0.10,  # +10%
    3: 0.15,  # +15%
    4: 0.22,  # +22%
    5: 0.30,  # +30%
}

GRADE_SHIELD_REGEN = {
    0: 0.00, 1: 0.00, 2: 0.00,
    3: 0.02,  # +2 % bouclier_max/round
    4: 0.02,
    5: 0.02,
}

GRADE_5_STEALTH_BONUS = 10.0  # +10 absolu, plafonné à 100
```

## Combat — `combat_engine.py`

```python
MAX_ROUNDS = 50

_BASE_XP = {
    "ATTACK_WIN":      100,
    "ATTACK_WIN_LOOT": 80,
    "DEFENSE_WIN":     150,
    "ALLIANCE":        60,
    "LOSS_SURVIVOR":   40,
}

_GRADE_THRESHOLDS = [
    (5, 40000),
    (4, 15000),
    (3,  6000),
    (2,  2000),
    (1,   500),
]

GRADE_4_IMMUNITY_HP = 1

SCAR_HULL_LOSS_THRESHOLD = 0.75
SCAR_POWER_RATIO_THRESHOLD = 2.0
```

## Forge — `forge_service.py`

```python
_DRIFT_PROBABILITY = 0.05
_DRIFT_ELIGIBLE_STATS = ["hull", "shield", "dps", "speed"]
DRIFT_SCAR_TAG_CODE = "born_in_drift"
DRIFT_STAT_REDUCTION = 0.80  # × 0.80 = -20 %

FORGE_DURATION_HOURS = 8
_XP_TRANSFER_RATIO = 0.30
_FORGE_STATUS_TTL = 8*3600 + 600  # 29 400 s

_RARITY_UPGRADE = {
    "COMMON":   "UNCOMMON",
    "UNCOMMON": "RARE",
    "RARE":     "EPIC",
    "EPIC":     "LEGENDARY",
    # LEGENDARY non upgradable → 422
}

# Forge cost = SHIP_TYPE_BUILD_COST × 3
```

## Synergies combat — `_compute_synergy_bonuses`

| Synergie | Condition | Effet |
|---|---|---|
| ATTACK + SUPPORT | ≥ 1 SUPPORT | DPS des ATTACK × 1.20 |
| DEFENSE + SUPPORT | ≥ 1 SUPPORT | hull regen 5%/round (DEFENSE alive) |
| DEFENSE × 3+ | ≥ 3 DEFENSE | shield_max × 1.15 |
| ATTACK + EXPLORATION | ≥ 20% EXPLO + ≥ 1 ATTACK | +10% vitesse de flotte (loggé seulement) |

## Resource tick — `tasks/resource_tick.py`

```python
_BASE_METAL_RATE = 30.0   # par heure × niveau × 1.1^niveau
_BASE_CRYSTAL_RATE = 15.0
_BASE_DEUT_RATE = 5.0

# Production solaire : _mine_output(20.0, solar_level)
# Besoin énergie : 10 × niveau métal + 10 × niveau cristal + 20 × niveau deut
# Facteur appliqué : min(1.0, energy_prod / energy_need)
```

## Pedigree — `ship_build_service.py`

```python
PEDIGREE_BONUS = 1.05  # × 1.05 sur la meilleure stat (excl. stealth/aura)
PEDIGREE_MIN_PARENT_GRADE = 3
```

## XP différentielle — `combat_engine._compute_differential_xp`

```python
ratio = enemy_power / own_power
diff_factor = max(0.0, ratio - 1.0) × 2.5
xp_gained = int(base_xp × (1 + diff_factor))
```

## Power calculation — `combat_engine._fleet_power`

```python
power = max(1.0, sum(
    ship.dps × ship.hull_max × (1 + ship.shield_max / ship.hull_max)
    for ship in fleet
))
```

## DPS effectif round — `_resolve_round`

```python
dps_raw = ship.dps × rng.uniform(0.90, 1.10)
dps_effective = int(dps_raw × (1 + support_aura_total / 100))
```

## Récap — fourchettes attendues simulations

| Scénario | Indicateur | Cible |
|---|---|---|
| Combat équilibré (rareté égale, grade égal) | winrate ATTACKER | 45-55 % |
| Combat équilibré | rounds moyens | 8-15 |
| LEGENDARY G5 vs 50 COMMON G0 | winrate LEGENDARY | 75-95 % |
| RNG distribution rareté | écart vs cible | < 5 % par catégorie |
| Drift distribution | % drift sur 1000 forges | 4-6 % |
| XP progression Grade 0 → 5 (combats équilibrés) | combats requis | ~400 |
| XP progression vs +5× plus fort | combats requis | ~70 |
