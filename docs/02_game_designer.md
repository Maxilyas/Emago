# Agent 2 — Game Designer

> Game Design Document complet d'Emago. Toutes les mécaniques, formules, valeurs équilibrées extraites du code de production (services + routers + migrations). Source de vérité unique pour l'équilibrage.

---

## 1. Système de classes de vaisseaux

Quatre classes avec stats normalisées (Commun, Grade 0, sans modules) :

| Stat | ATTACK | DEFENSE | SUPPORT | EXPLORATION |
|---|---|---|---|---|
| Hull | 100 | 350 | 150 | 80 |
| Shield | 20 | 120 | 40 | 15 |
| DPS / round | 80 | 15 | 8 | 12 |
| Speed (UA/h) | 45 | 15 | 30 | 90 |
| Cargo (unités) | 200 | 500 | 1 000 | 3 000 |
| Stealth (%) | 0 | 0 | 0 | 25 |
| Aura soutien (%) | 0 | 0 | 15 | 0 |

> Source : `ship_build_service._BASE_STATS_BY_CLASS`

### Types de vaisseaux disponibles

| ship_type | Classe | Coût Métal | Coût Cristal | Coût Deutérium | Chantier requis |
|---|---|---:|---:|---:|---:|
| frigate_attack | ATTACK | 3 000 | 1 000 | 0 | 1 |
| frigate_defense | DEFENSE | 6 000 | 2 000 | 0 | 1 |
| frigate_support | SUPPORT | 2 000 | 2 000 | 500 | 1 |
| frigate_exploration | EXPLORATION | 2 000 | 1 000 | 1 000 | 2 |
| cruiser_attack | ATTACK | 20 000 | 7 000 | 2 000 | 4 |
| cruiser_defense | DEFENSE | 30 000 | 10 000 | 2 000 | 4 |

> Source : `ship_build_service.SHIP_TYPE_BUILD_COST` + `SHIP_SHIPYARD_REQUIREMENTS`

### Synergies inter-classes (combat uniquement)

| Synergie | Condition | Effet |
|---|---|---|
| ATTACK + SUPPORT | ≥ 1 SUPPORT | DPS des ATTACK × 1.20 |
| DEFENSE + SUPPORT | ≥ 1 SUPPORT | +5 % hull/round (réparation, DEFENSE alive uniquement) |
| ATTACK + EXPLORATION | ≥ 20 % EXPLO + ≥ 1 ATTACK | +10 % vitesse de flotte (logué uniquement, pas appliqué en combat) |
| DEFENSE × 3+ | ≥ 3 DEFENSE | shield_max × 1.15 |

> Source : `combat_engine._compute_synergy_bonuses`

Les synergies sont calculées **côté serveur uniquement**, à l'initialisation de chaque combat. Elles apparaissent dans le rapport (`synergies.attacker`, `synergies.defender`) mais pas en pré-combat — choix délibéré pour préserver la surprise.

---

## 2. Système de rareté — RNG pondéré

À chaque construction, le serveur tire `r = secrets.SystemRandom().random()` et compare aux seuils cumulés.

| Rareté | Probabilité | Seuil cumulé | Multiplicateur stats |
|---|---:|---:|---:|
| COMMON | 55 % | 0.00 – 0.55 | × 1.00 |
| UNCOMMON | 27 % | 0.55 – 0.82 | × 1.25 |
| RARE | 12 % | 0.82 – 0.94 | × 1.55 |
| EPIC | 5 % | 0.94 – 0.99 | × 1.90 |
| LEGENDARY | 1 % | 0.99 – 1.00 | × 2.40 |

> Source : `ship_build_service._RARITY_THRESHOLDS` + `_RARITY_MULT`

### Fourchettes de stats (variance ±10 %)

```
stat_finale = base × rarity_mult + uniform(-0.10, +0.10) × (base × rarity_mult)
```

Exemple sur la **coque ATTACK (base 100)** :

| Rareté | Min | Espérance | Max |
|---|---:|---:|---:|
| COMMON | 90 | 100 | 110 |
| UNCOMMON | 113 | 125 | 138 |
| RARE | 140 | 155 | 171 |
| EPIC | 171 | 190 | 209 |
| LEGENDARY | 216 | 240 | 264 |

> Arrondi : speed → 1 décimale, stealth/support_aura → 2 décimales, autres → entier (`max(0, round(...))`).

### Slots de modules par rareté

| Rareté | Slots totaux | Dont premium |
|---|---:|---:|
| COMMON | 2 | 0 |
| UNCOMMON | 3 | 0 |
| RARE | 4 | 1 |
| EPIC | 5 | 2 |
| LEGENDARY | 6 | 3 |

Les **slots premium** sont les derniers de la liste (`slot_index >= total_slots - premium_slots`). Ils sont les seuls à accepter les modules niveau IV et V.

---

## 3. Système de modules — 6 familles, 5 niveaux

### Familles et affinités

| Famille | Stat boostée | Classe d'affinité |
|---|---|---|
| PROPELLER | speed | EXPLORATION |
| ARMOR | hull | DEFENSE |
| CANNON | dps | ATTACK |
| EMITTER | support_aura | SUPPORT |
| SHIELD | shield | DEFENSE |
| CARGO | cargo | EXPLORATION |

### Niveaux et boost

| Niveau | Boost (sans affinité) | Boost (avec affinité ×1.15) |
|---|---:|---:|
| I | +8.0 % | +9.2 % |
| II | +14.0 % | +16.1 % |
| III | +22.0 % | +25.3 % |
| IV (premium uniquement) | +32.0 % | +36.8 % |
| V (premium uniquement) | +44.0 % | +50.6 % |

> Source : `ship_stats_service._MODULE_BOOST` + `_AFFINITY_MULT = 1.15`

### Cap absolu : +150 % par stat

Le `current_stats` final est plafonné à `base × 2.5` par stat. Si plusieurs modules empilés dépassent ce plafond, la stat est inscrite dans `cap_reached` (retourné dans la réponse `ModuleInstallResponse`) pour signaler à l'UI qu'il est inutile d'empiler davantage.

```
target = (base × (1 + grade_bonus)) + (base × Σ module_boosts)
cap_value = base × (1 + 1.50)  # base × 2.5
final = min(target, cap_value)
```

---

## 4. Système de grades XP

Cinq grades (en plus de Grade 0 Recrue), chacun apportant un bonus passif permanent.

| Grade | Nom | XP requise | Bonus |
|---|---|---:|---|
| 0 | Recrue | 0 | — |
| 1 | Vétéran | 500 | +5 % toutes stats |
| 2 | Élite | 2 000 | +10 % toutes stats |
| 3 | Légion | 6 000 | +15 % toutes stats, régén. bouclier 2 %/round |
| 4 | Légende | 15 000 | +22 % toutes stats, **immunité 1ère destruction** (rebond à 1 HP, reset 48 h) |
| 5 | Spectre | 40 000 | +30 % toutes stats, +10 % stealth absolu |

> Source : `ship_stats_service._GRADE_BONUS`, `GRADE_SHIELD_REGEN`, `GRADE_5_STEALTH_BONUS = 10.0` ; seuils dans `combat_engine._GRADE_THRESHOLDS`

### XP différentielle (cœur anti-farm)

```
ratio = puissance_ennemie / puissance_propre
diff_factor = max(0, ratio - 1) × 2.5
XP_gagnée = int(base_XP × (1 + diff_factor))
```

Battre une flotte 2× plus puissante : `× (1 + 2.5) = × 3.5`. Battre une flotte 5× plus faible : `× (1 + 0) = × 1.0` (gain plancher). Ce système rend le farming des newbies inintéressant.

### Base XP par résultat

| Cas | Base XP |
|---|---:|
| Défense réussie | 150 |
| Attaque victorieuse sans pillage | 100 |
| Attaque victorieuse avec pillage | 80 |
| Combat allié (futur) | 60 |
| Combat perdu, vaisseau survivant | 40 |

> Source : `combat_engine._BASE_XP`

### Puissance d'une flotte

```
Power = Σ (dps × hull_max × (1 + shield_max / hull_max))
```

Minimum 1.0 (anti-zéro divide).

---

## 5. La Forge — fusion stratégique

Fusion de **2 vaisseaux du même type ET de même rareté** → 1 vaisseau de la rareté supérieure d'un cran. Durée 8 h. Coût ×3 du build de base. La Forge ne peut s'appliquer à un LEGENDARY (HTTP 422).

### Mécanique de fusion

- `new_base_stats = max(stats_a, stats_b)` élément par élément.
- `transferred_xp = int(max(combat_xp_a, combat_xp_b) × 0.30)`.
- Nouveau nom procédural (RARE+) + nouveau trait via `roll_trait()`.
- Nouveau slots calculés depuis `_RARITY_SLOTS[new_rarity]`.
- Les 2 parents passent en statut `SCRAPPED` (suppression définitive).

### Mécanique Dérive (5 % de chance)

Si `random() < 0.05`, le serveur applique une **Dérive** :
- Choisit aléatoirement une stat parmi `["hull", "shield", "dps", "speed"]` présente.
- Réduit cette stat de 20 % (`× 0.80`).
- Marque `is_drift = True` sur le nouveau vaisseau.
- INSERT automatique d'un `ShipScar` avec tag `"born_in_drift"`.
- L'UI affiche un badge violet pâle + bordure pointillé.

> Source : `forge_service._DRIFT_PROBABILITY = 0.05` + `apply_drift`

### Coûts forge (= 3× build)

| Type | Métal | Cristal | Deutérium |
|---|---:|---:|---:|
| frigate_attack | 9 000 | 3 000 | 0 |
| frigate_defense | 18 000 | 6 000 | 0 |
| frigate_support | 6 000 | 6 000 | 1 500 |
| frigate_exploration | 6 000 | 3 000 | 3 000 |
| cruiser_attack | 60 000 | 21 000 | 6 000 |
| cruiser_defense | 90 000 | 30 000 | 6 000 |

### Validations (HTTP errors)

- 400 : `ship_a_id == ship_b_id`
- 404 : un vaisseau introuvable
- 403 : un vaisseau n'appartient pas au joueur
- 422 : types ou raretés différents, ou rareté LEGENDARY
- 409 : un vaisseau pas DOCKED, ou pas sur planète
- 402 : ressources insuffisantes (×3)

---

## 6. Pedigree — héritage générationnel

Quand un vaisseau **Grade ≥ 3 démoli volontairement** (pas détruit en combat) sert de parent à la fabrication d'un nouveau vaisseau **du même type**, ce dernier reçoit :

- Bonus **+5 %** sur la **meilleure stat** du parent (en excluant `stealth` et `support_aura` qui ont des échelles atypiques).
- Mention "Issu de [nom du parent]" dans son historique (`parent_ship_id`).

```
boosted_stat = parent_best_stat × 1.05  (arrondi cohérent)
```

> Source : `ship_build_service.apply_pedigree_bonus` + `find_best_stat`

Validations Pedigree (HTTP) :
- 404 : parent introuvable
- 403 : parent n'appartient pas au joueur
- 409 : parent pas même type, ou Grade < 3, ou pas DOCKED

---

## 7. Cicatrices de combat — narratif

Un vaisseau qui survit à un combat difficile reçoit une **cicatrice** narrative.

### Conditions de déclenchement (`_should_earn_scar`)

- `hull_loss_ratio = (hull_start - hull) / hull_start` ≥ **0.75** (75 % de coque perdue), OU
- `power_ratio = enemy_power / own_power` ≥ **2.0** (combat contre flotte ≥ 2× plus puissante).

### Pool de tags

- En base : table `scar_tags` avec ~500 tags (seedés par migration `0002_seed_scar_tags`).
- Le combat engine utilise actuellement un pool en dur de 10 tags (cf. `combat_engine._SCAR_TAGS`) : *"Rescapé de la Nébuleuse Kha", "Survivant du Siège de l'Anneau IV", "Témoin de la Chute d'Eryndor", "Vétéran de la Bataille des Trois Lunes", "Rescapé du Couloir de Fenrath", "Survivant de la Purge de Vael", "Marqué par l'Abysse de Corvus", "Dernier de la Flotte Brisée", "Cicatricé aux Abords d'Obsidia", "Rescapé de la Tempête de Fer"*.
- Les expéditions ont leur pool propre (`expedition_service.EXPEDITION_SCAR_TAGS`, 8 tags).
- La Forge Dérive ajoute systématiquement `"born_in_drift"`.

Les cicatrices n'ont **aucun effet mécanique** — pure narration. Visibles par tous les joueurs (l'endpoint `GET /ships/{id}/scars` ne vérifie pas l'ownership).

---

## 8. Traits narratifs — ~200 traits, 8 familles

Chaque vaisseau reçoit **un trait unique à la construction** (RNG indépendant de la rareté), stocké en JSONB dans `ships.trait`. Les COMMON ont aussi un trait. Le trait est immuable.

Format JSONB : `{"key": "...", "name": "...", "description": "..."}`. L'effet n'est PAS sérialisé — il est résolu à l'exécution via `TRAIT_INDEX[key]`.

### Conditions d'activation

| Condition | Activé quand |
|---|---|
| ALWAYS | Tout le temps |
| SOLO | `fleet_size == 1` |
| FLEET_3PLUS | `fleet_size >= 3` |
| CLASS_MATCH | `ship_class == effect.condition_class` |
| NONE | Jamais (traits flavour purs) |

Bonus typique : **+5 % à +16 %** sur une stat unique (`hull`, `shield`, `dps`, `speed`, `cargo`, `stealth`, `support_aura`). Cible : `SELF` ou `ALL_ALLIES` (ce dernier traité par le combat_engine).

### 8 familles thématiques

1. **Chasseurs & Combattants** : bounty_hunter (SOLO dps +10 %), berserker, predator, sniper, duelist, gladiator, void_stalker, warmonger (FLEET_3PLUS dps +6 % ALL_ALLIES)…
2. **Navigateurs & Explorateurs** : navigator_soul (SOLO speed +15 %), pathfinder, deep_spacer, void_runner, eternal_voyager (cargo +15 %)…
3. **Gardiens & Défenseurs** : iron_fortress (hull +10 %), bulwark (FLEET_3PLUS hull +8 %), shield_wall (FLEET_3PLUS shield +10 % ALL_ALLIES), titanium_soul (hull +12 %)…
4. **Soutiens & Commandants** : crew_soul (FLEET_3PLUS dps +8 % ALL_ALLIES), tactician (+9 % ALL), morale_officer, quartermaster (+10 % cargo ALL)…
5. **Éléments & Cosmiques** : antimatter_core, dark_energy (SOLO speed +12 %), pulsar_heart, event_horizon (SOLO dps +9 %)…
6. **Fantômes & Mystiques** : ghost_ship (stealth +14 %), wraith (SOLO stealth +12 %), silent_death (SOLO dps +11 %)…
7. **Marchands & Logisticiens** : merchant_prince (cargo +14 %), war_profiteer (cargo +13 %), supply_chain (FLEET_3PLUS cargo +8 % ALL)…
8. **Élite & Légendes vivantes** : chosen_one, ace_pilot (speed +9 %), war_machine (dps +10 %), apex_predator (SOLO dps +13 %), deathbringer (SOLO dps +14 %)…

### Traits CLASS_MATCH (doctrines)

- `attack_doctrine` — CLASS_MATCH ATTACK, dps +10 % SELF.
- `shield_doctrine` — CLASS_MATCH DEFENSE, hull +10 % SELF.
- `support_doctrine` — CLASS_MATCH SUPPORT, support_aura +12 % SELF.
- `scout_doctrine` — CLASS_MATCH EXPLORATION, stealth +12 % SELF.

### Traits flavour (NONE — sans effet)

`old_faithful`, `painted_black`, `unnamed`, `lucky_charm`, `first_blood`, `scarred_but_whole`, `iron_cross`, `old_warhorse`, `last_of_its_kind`, `born_ready`.

---

## 9. Naming procédural (RARE+)

À partir de RARE inclus, chaque vaisseau reçoit un nom au format `[Racine] [Qualificatif]`.

- **80 racines** : Astraeus, Corvus, Vael, Eryndor, Kha, Fenrath, Obsidia, Arcturus, Veloris, Noctara, Pyreth, Solux, Umbrath, Zephyr, Caelum… (cf. `naming_service._ROOTS`).
- **15 qualificatifs par classe** :
  - **ATTACK** : Noir, Rouge, de Fer, Brisé, Furieux, Sanglant, Impitoyable, Ardent, Vengeur, Implacable, de Guerre, Corrosif, Silencieux, Brutal, Écarlate.
  - **DEFENSE** : Inébranlable, Éternel, de Granit, Immuable, Solide, Stoïque, de Pierre, Indompté, Massif, Invaincu, Forteresse, Blindé, Indestructible, Robuste, Inflexible.
  - **SUPPORT** : Lumineux, Gardien, Bienveillant, de Lumière, Sage, Harmonieux, Protecteur, Guérisseur, Serein, Altruiste, Radieux, Porteur, Fidèle, Vigile, Sanctifié.
  - **EXPLORATION** : Prime, Errant, Libre, Fantôme, de l'Abysse, Solitaire, Perdu, Silencieux, de l'Ombre, Immortel, Nomade, Fugace, Invisible, Lointain, Pionnier.

Probabilité de duplication : `1 / (80 × 15) = 1/1200` par classe. COMMON et UNCOMMON ont `name=NULL`.

---

## 10. Bâtiments planétaires (6 types)

| Bâtiment | Catégorie | Rôle |
|---|---|---|
| metal_mine | Production | Produit du métal |
| crystal_mine | Production | Produit du cristal |
| deuterium_synthesizer | Production | Produit du deutérium |
| solar_plant | Énergie | Soutient les autres mines (futur) |
| shipyard | Construction | Niveau requis pour types de vaisseaux |
| research_lab | Tech | Débloque les recherches |

Coût d'un upgrade : `cost_base × 1.5^current_level`.

> Source : `routers/planets.py BUILDING_CONFIG` + `_building_cost`

Capacités stockage initiales par planète : 10 000 métal, 10 000 cristal, 5 000 deutérium.
Stocks initiaux : 500 métal, 300 cristal, 100 deutérium.

---

## 11. Recherches technologiques

14 technologies réparties en 4 classes (depuis `routers/tech.py TECH_TREE`) :

- **ATTACK** (4) : `att_weapons_1`, `att_weapons_2`, `att_speed`, `att_rng_boost`
- **DEFENSE** (3) : `def_armor`, `def_shields`, `def_regen`
- **SUPPORT** (2) : `sup_aura`, `sup_repair`
- **EXPLORATION** (4) : `exp_speed`, `exp_stealth`, `exp_cargo`, `exp_expedition_bonus`

Chaque tech a : niveau max, bonus par niveau, prérequis (autres techs avec niveau requis), liste de coûts par niveau, icône.

Effet : bonus permanent appliqué à tous les vaisseaux de la classe correspondante.

---

## 12. Expéditions — événements pondérés (12 events)

Lancement de 1 à 5 vaisseaux pour 2 h / 6 h / 12 h. Coût en deutérium : 500 / 1 500 / 4 000.

Multipliers ressources : SHORT × 0.6, MEDIUM × 1.0, LONG × 1.8.
Multipliers XP : SHORT × 0.7, MEDIUM × 1.0, LONG × 1.5.

### Pool d'événements (12 events, poids total 100)

| Tier | Event | Poids | Effet |
|---|---|---:|---|
| Bons (45) | debris_field | 18 | metal[2k–8k], crystal[1k–4k], xp[20–60] |
| | alien_artifact | 12 | module drop, xp[40–80] |
| | derelict_station | 10 | crystal[3k–10k], deut[500–2k], xp[30–50] |
| | rogue_freighter | 5 | tout métal+cristal+deut+xp |
| Neutres (30) | void_storm | 15 | xp[10–25] + scar |
| | strange_signal | 10 | xp[15–40] |
| | navigation_error | 5 | deut_loss[200–800] |
| Difficiles (20) | pirate_ambush | 10 | xp[80–150] + scar + hull_damage |
| | radiation_zone | 6 | xp[30–60] + scar |
| | patrol_encounter | 4 | xp[100–200] + scar + module_damage |
| Exceptionnels (5) | legendary_wreck | 3 | metal[10k–30k], crystal[5k–15k], module rare 40 % |
| | first_contact | 2 | module rare 70 %, xp[200–400] + scar |

Tirage déterministe : `seed = "{exp_id}{duration}"` → `sha256(seed) % 100` → sélection cumulée.

Le module trouvé est actuellement loggé mais **pas persisté** (TODO : table `player_module_inventory`).
Les flags `hull_damage` / `module_damage` ne sont pas encore appliqués (juste dans le payload).

---

## 13. Combat — moteur de résolution

### Algorithme

1. Charger `current_stats` de chaque vaisseau (`ship_stats_service.get_current_stats`).
2. Calculer `att_power`, `def_power`.
3. Appliquer les synergies serveur (mute les `CombatShip`).
4. Calculer les auras de soutien : `support_aura_total = sum(SUPPORT.support_aura) / 100.0`.
5. Tirer un seed `combat_seed = SystemRandom().randint(0, 2^32-1)` → `random.Random(seed)` (rejouabilité).
6. Boucle max **50 rounds** :
   - Chaque shooter tire en simultané : cible aléatoire, `dps × uniform(0.90, 1.10) × (1 + support_aura)`.
   - `take_damage` : shield absorb d'abord, puis hull. Hull ≤ 0 → destroyed (sauf Grade 4 : rebond à 1 HP, immunité consommée).
   - Régen bouclier post-round : Grade 3+ → `+ int(shield_max × 0.02)`.
   - Régen hull post-round (synergie DEFENSE+SUPPORT) : DEFENSE alive → `+ int(hull_max × 0.05)`.
   - Break si une face est exterminée.
7. Décerner XP : différentielle calculée par côté.
8. Vaisseaux détruits : `db.delete()` (suppression définitive, perd tout XP).
9. Vaisseaux survivants : `combat_xp += xp_earned`, recalcul grade depuis seuils (5→4→3→2→1→0).
10. Cicatrices : tirage si conditions remplies, INSERT `ShipScar` + WS event.
11. INSERT `CombatLog` (snapshots JSONB, rounds_log, outcome, pillage, powers).
12. Broadcast WS HORS transaction : `combat.result` (2 owners), `ship.grade_up`, `ship.scar_earned`.

### Outcomes possibles

`ATTACKER_WIN` / `DEFENDER_WIN` / `DRAW` (épuisement 50 rounds).

### Loot (si ATTACKER_WIN sur planète)

Pillage métal/cristal/deutérium calculé par le caller (ratios à finaliser dans Phase 2). Limite par cargo total des vaisseaux survivants.

---

## 14. Daily login & missions

### Streak 7 jours (cycle)

| Jour | Métal | Cristal | Deutérium | Label |
|---:|---:|---:|---:|---|
| 1 | … | … | … | (cf. `routers/daily.py STREAK_REWARDS`) |
| 7 | (top reward) | | | |

Réinitialisation à 1 si pas connecté la veille.

### Missions quotidiennes (3 par jour, déterministes)

Pool de 8 missions, sélection via `sha256(player_id + date) % 8` × 3 (sans répétition) :

`build_ship`, `collect_metal`, `upgrade_building`, `send_fleet`, `install_module`, `check_galaxy`, `have_3_ships`, `forge_active`.

Chacune avec un seuil de progression et une récompense fixe.

---

## 15. Alliances (Sprint 4)

Voir `GDD_ALLIANCES.md` pour le détail. Synthèse :

- **Création** : 10 000 métal + 5 000 cristal sur la planète natale, score ≥ 500.
- **Membres max** : 20 par alliance.
- **Rôles** : `LEADER`, `OFFICER`, `MEMBER` (`MEMBER < OFFICER < LEADER`).
- **Score collectif** : somme des scores individuels.
- **Guerre** : déclarée par le leader. Bonus XP × 1.5 sur les combats inter-alliances en guerre. Durée minimum **48 h** avant déclaration de paix.
- **Tag** : 2-5 chars `[A-Z0-9]+`, unique global.

---

## 16. Tableaux récapitulatifs des constantes

| Domaine | Constante | Valeur |
|---|---|---|
| Cap stat | `_STAT_CAP_RATIO` | +150 % de base |
| Pedigree | bonus | +5 % meilleure stat (Grade ≥ 3) |
| Build variance | offset | uniform(-10 %, +10 %) |
| XP différentielle | facteur | `× (1 + max(0, ratio-1) × 2.5)` |
| Cicatrice hull | seuil | ≥ 75 % perte |
| Cicatrice power | seuil | ≥ 2× plus fort |
| Grade 4 immunité | rebond | 1 HP (reset 48 h) |
| Grade 5 stealth | bonus | +10 % absolu |
| Forge durée | | 8 h |
| Forge coût | | × 3 build |
| Forge XP transfert | | 30 % du max |
| Dérive | proba | 5 %, stat × 0.80 |
| Affinité module | | × 1.15 |
| Module boosts | I-V | 8 / 14 / 22 / 32 / 44 % |
| Grade XP seuils | 1-5 | 500 / 2 000 / 6 000 / 15 000 / 40 000 |
| Grade bonus | 0-5 | 0 / 5 / 10 / 15 / 22 / 30 % |
| Shield regen | par round Grade 3+ | 2 % shield_max |
| Max rounds combat | | 50 |
| Synergie ATT+SUP | | DPS × 1.20 |
| Synergie DEF×3+ | | shield × 1.15 |
| Synergie DEF+SUP | | +5 % hull/round |
| Redis stats TTL | | 300 s |
| Redis hangar TTL | | 120 s |
| Redis forge TTL | | 8 h + 10 min |
| Redis expé TTL | | 48 h |
| Expé multipliers (res) | SHORT/MED/LONG | 0.6 / 1.0 / 1.8 |
| Expé multipliers (xp) | SHORT/MED/LONG | 0.7 / 1.0 / 1.5 |
| Capacité initiale | métal/cristal/deut | 10k / 10k / 5k |
| Stock initial | métal/cristal/deut | 500 / 300 / 100 |

---

## 17. Améliorations GDD à prévoir

| Mécanique | Priorité | Description |
|---|---|---|
| Espionnage | Haute | Sondes, niveau de détection, contre-espionnage |
| Colonisation | Haute | Conditions, MAX planètes, init ressources |
| Anti-farm complet | Haute | Protections débutants, ratio pillage max |
| Marché galactique | Moyenne | Échange ressources joueurs |
| Univers / saisons | Basse | Permanent vs reset 3 mois |
| Limites hangar | Moyenne | MAX vaisseaux par joueur/planète |
| Tutoriel narratif | Haute | Onboarding premier joueur |
| Missions globales | Basse | Événements serveur (invasion, tournoi) |
| Module inventory | Haute | Persistance des drops d'expédition |
| Hull/Module damage expédition | Moyenne | Implémenter les flags `hull_damage` et `module_damage` |
| Pool scar_tags expéditions | Basse | Remplacer `tag_id=1` par lookup réel |
| Mécaniques alliance avancées | Basse | Diplomatie, sous-guildes, chat |
| Skins de vaisseaux | Basse | Cosmétiques pour missions |

---

*Document Agent 2 — Mai 2026*
