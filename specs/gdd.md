Voici le GDD complet du système de vaisseaux d'Emago. Je vais d'abord te poser le cadre avec un aperçu visuel, puis dérouler chaque couche du système.

---

## GDD — Système de vaisseaux Emago v1.0

Le cœur du système repose sur une idée simple : **chaque vaisseau est unique, vivant, et narratif**. Pas un chiffre dans une liste — un compagnon de guerre avec une histoire. Voici l'architecture complète.

------

## 1. Les 4 classes de vaisseaux

### Mécanique

Chaque vaisseau appartient à une classe définie à la conception du modèle (type de chassis). La classe ne change jamais — elle définit la vocation du vaisseau et ses limites naturelles. Les quatre classes sont pensées pour être interdépendantes : une flotte mono-classe est toujours vulnérable à quelque chose.

### Formules / Valeurs

**Stats de base normalisées (Commun, niveau 1, sans modules)**

| Stat | Attaque | Défense | Soutien | Exploration |
|---|---|---|---|---|
| Points de coque | 100 | 350 | 150 | 80 |
| Boucliers | 20 | 120 | 40 | 15 |
| DPS (attaque/round) | 80 | 15 | 8 | 12 |
| Vitesse (UA/heure) | 45 | 15 | 30 | 90 |
| Cargo (unités) | 200 | 500 | 1 000 | 3 000 |
| Furtivité (%) | 0 | 0 | 0 | 25 |
| Aura de soutien (%) | 0 | 0 | 15 | 0 |

**Interplay des classes (tableau de synergies)**

| Duo | Bonus | Seuil |
|---|---|---|
| Attaque + Soutien | +20% DPS pour l'Attaque | ≥ 1 Soutien dans la flotte |
| Défense + Soutien | Réparation en combat (+5% coque/round) | ≥ 1 Soutien |
| Attaque + Exploration | +10% vitesse de flotte | ≥ 20% Exploration |
| Défense + Défense | Bouclier collectif (+15%) | ≥ 3 Défense |

Ces synergies sont calculées côté serveur au moment du calcul de combat — elles ne sont visibles que dans le rapport de combat (résultat de ce qui s'est passé, pas en pré-combat) pour éviter l'optimisation mécanique trop froide et garder une part de surprise.

### Cas limites

Un joueur avec 100% de vaisseaux Attaque sera rapide et brutal mais fragile au grinding d'attrition. Un joueur full Défense ne peut quasiment pas raider. Ces asymétries sont voulues et encouragent le multirôle sans le rendre obligatoire.

### Notes pour les développeurs

Le champ `class` dans la table `ships` est un enum PostgreSQL : `ATTACK | DEFENSE | SUPPORT | EXPLORATION`. Les synergies sont calculées dans le service `combat_engine.py` à l'initialisation d'un round — elle ne doivent jamais être stockées, seulement logguées dans le rapport de combat.

---

## 2. Système de rareté — RNG pondéré

### Mécanique

À chaque fabrication, le serveur tire un nombre entre 0 et 1 et le mappe sur une distribution de probabilité cumulée. La rareté est alors verrouillée pour la durée de vie du vaisseau. Elle définit la fourchette dans laquelle les stats RNG seront tirées.

### Formules / Valeurs

**Distribution de probabilité**

| Rareté | Probabilité | Cumulé | Multiplicateur de stats |
|---|---|---|---|
| Commun | 55% | 0–0.55 | ×1.0 |
| Peu commun | 27% | 0.55–0.82 | ×1.25 |
| Rare | 12% | 0.82–0.94 | ×1.55 |
| Épique | 5% | 0.94–0.99 | ×1.90 |
| Légendaire | 1% | 0.99–1.00 | ×2.40 |

**Fourchette de stats RNG par rareté** (exemple sur la coque d'un vaisseau Attaque base 100)

| Rareté | Min | Max | Valeur attendue |
|---|---|---|---|
| Commun | 95 | 115 | 105 |
| Peu commun | 115 | 140 | 127 |
| Rare | 145 | 165 | 155 |
| Épique | 175 | 205 | 190 |
| Légendaire | 225 | 255 | 240 |

La formule générale est : `stat_rng = base × rarity_mult + random_offset` où `random_offset ~ Uniform(-10%, +10%)` de la valeur après multiplicateur.

**Slots de modules disponibles par rareté**

| Rareté | Slots modules | Slots "premium" |
|---|---|---|
| Commun | 2 | 0 |
| Peu commun | 3 | 0 |
| Rare | 4 | 1 |
| Épique | 5 | 2 |
| Légendaire | 6 | 3 |

Les slots "premium" acceptent des modules de niveau supérieur que les slots standard.

### Cas limites

Un Légendaire sorti avec de mauvaises stats RNG (bas de fourchette) peut être moins puissant qu'un Épique chanceux. C'est volontaire — cela crée de la valeur narrative et de la surprise. Le plancher reste néanmoins nettement au-dessus du plafond de la rareté inférieure, donc aucun Légendaire n'est "mauvais" dans l'absolu.

### Notes pour les développeurs

Le tirage RNG doit utiliser `secrets.SystemRandom()` côté Python (non prédictible, non seedable par l'extérieur). Les stats de base sont stockées dans la table `ships` dans deux colonnes JSON : `base_stats` (immuable, NEVER UPDATE) et `current_stats` (calculé à la volée = base + modules + XP bonus). Un trigger PostgreSQL empêche toute modification de `base_stats` après insertion.

---

## 3. Modules manuels — 6 familles

### Mécanique

Les modules sont des pièces d'équipement que le joueur fabrique ou trouve, et installe dans les slots disponibles d'un vaisseau. Un module installé peut être retiré (récupère le module, perd les ressources d'installation) ou remplacé. Les modules ont des prérequis de rareté : un module Épique ne peut s'installer que dans un slot premium ou dans un vaisseau Épique+.

**Mécanique innovante — les modules ont une "affinité de classe"** : un module installé sur la classe pour laquelle il est conçu donne un bonus de +15% sur son effet. Cela crée de la spécialisation sans bloquer l'expérimentation.

### Formules / Valeurs

**6 familles de modules**

| Famille | Effet principal | Stat boostée | Affinité classe |
|---|---|---|---|
| Propulseur | +% vitesse et initiative | Vitesse | Exploration |
| Blindage | +% coque et résistance | Coque | Défense |
| Canon | +% DPS et portée | Attaque | Attaque |
| Émetteur | +% aura de soutien | Aura | Soutien |
| Bouclier | +% régén. de bouclier | Bouclier | Défense |
| Cargo amélioré | +% capacité cargo | Cargo | Exploration |

**Valeurs de boost par niveau de module**

| Niveau module | Boost (sans affinité) | Boost (avec affinité) | Coût ressources |
|---|---|---|---|
| I | +8% | +9.2% | Métal ×500 |
| II | +14% | +16.1% | Métal ×1200, Cristal ×300 |
| III | +22% | +25.3% | Métal ×3000, Cristal ×800, Deut. ×200 |
| IV | +32% | +36.8% | Métal ×8000, Cristal ×2500, Deut. ×800 |
| V | +44% | +50.6% | Métal ×20k, Cristal ×7k, Deut. ×2.5k |

Les modules de niveau IV et V ne peuvent s'installer que dans des slots "premium" (Rare+).

### Cas limites

Un joueur qui stacke 6 modules Canon niveau V sur un Légendaire Attaque atteindrait un DPS ×3.6 — potentiellement trop fort. Le plafond global est limité : un vaisseau ne peut pas dépasser +150% sur une stat unique, tous modules combinés. Ce cap est calculé côté serveur à chaque modification du loadout.

### Notes pour les développeurs

La table `ship_modules` stocke les associations (ship_id, slot_index, module_type, module_level). Le `current_stats` est recalculé par le service `ship_stats_service.py` à chaque modification du loadout et mis en cache dans Redis (TTL 5 minutes ou invalidation sur changement). Il ne doit jamais être calculé côté client.

---

## 4. XP de combat — 5 grades

### Mécanique

Chaque vaisseau survivant gagne de l'XP après un combat. L'XP est liée au vaisseau, pas au joueur. Elle débloque des grades qui octroient des bonus passifs permanents, en plus des modules. Un vaisseau détruit perd toute son XP — ce qui crée du "poids" dans les décisions tactiques.

**Mécanique innovante — XP différentielle** : l'XP gagnée est proportionnelle à l'écart de puissance entre les flottes. Battre une flotte plus forte rapporte beaucoup plus d'XP. Farmer des flottes faibles rapporte presque rien. Cela décourage le farming de newbies et encourage l'audace.

```
XP_gagnée = base_XP × (1 + max(0, puissance_ennemie / puissance_propre - 1) × 2.5)
```

### Formules / Valeurs

**Grades et seuils**

| Grade | Nom | XP requise | Bonus passif |
|---|---|---|---|
| 0 | Recrue | 0 | — |
| 1 | Vétéran | 500 | +5% toutes stats |
| 2 | Élite | 2 000 | +10% toutes stats, +1 slot module |
| 3 | Légion | 6 000 | +15% toutes stats, régén. 2% bouclier/round |
| 4 | Légende | 15 000 | +22% toutes stats, immunité première destruction |
| 5 | Spectre | 40 000 | +30% toutes stats, +1 slot premium, furtivité +10% |

Le grade 4 confère l'immunité à la première destruction (le vaisseau survit à 1 HP au lieu d'être détruit) — elle se réinitialise après 48h de non-combat. Cela crée un attachement fort aux vaisseaux anciens.

**XP de base par type de mission**

| Type de combat | XP de base |
|---|---|
| Défense réussie | 150 |
| Attaque victorieuse | 100 |
| Attaque victorieuse + pillage | 80 |
| Participation en alliance | 60 |
| Combat perdu (survivant) | 40 |

### Cas limites

Un vaisseau Grade 5 avec des stats Légendaire et des modules niveau V est très puissant mais aussi très précieux à perdre — ce qui crée naturellement de la prudence et de la décision tactique. L'équilibre est que même 50 vaisseaux Communs Grade 0 peuvent menacer un Légendaire Grade 5 s'ils sont bien organisés (le cap de +150% sur les stats empêche un one-shot systématique).

### Notes pour les développeurs

Le champ `combat_xp` et `grade` sont dans la table `ships`. Le calcul de `XP_gagnée` se fait dans `combat_engine.py` après résolution du combat. La mise à jour des stats suite à un changement de grade doit invalider le cache Redis du vaisseau.

---

## 5. Mécaniques innovantes de rétention

Ce sont les systèmes qui créent du plaisir de revenir, de la narration personnelle, et de l'attachement sans être des dark patterns.

---

### 5a. Le Pedigree — héritage entre vaisseaux

Quand un vaisseau Grade 3+ est démoli volontairement (pas détruit en combat), il peut "transmettre" une trace à un vaisseau du même type fabriqué immédiatement après. Cette trace s'appelle un **Pedigree**. Le nouveau vaisseau hérite d'un bonus mineur (+5% sur la meilleure stat du parent) et d'une mention dans son historique ("Issu de l'*Astraeus Prime*, Grade Légion").

Cela crée une culture de la lignée et un attachement multi-générationnel aux vaisseaux. C'est purement cosmétique-narratif au-delà du +5%, donc non pay-to-win.

---

### 5b. La Forge — fusion stratégique

Deux vaisseaux du même type et de même rareté peuvent être fusionnés à la Forge. Le résultat est un vaisseau de rareté supérieure d'un cran, avec les meilleures stats des deux parents, et 30% de l'XP du vaisseau le plus expérimenté transférée.

| Coût | Détail |
|---|---|
| Ressources | Équivalent à construire 3 vaisseaux du type |
| Temps | 8h (peut être suivi en temps réel) |
| Contrainte | Même type strict, même rareté. Pas de Rare + Épique |

La Forge est la soupape anti-frustration pour les joueurs qui n'ont jamais tiré de Légendaire : deux Épiques chanceux peuvent en forger un.

---

### 5c. Réputation et missions de vaisseau

Un vaisseau qui atteint Grade 2+ peut recevoir des **missions de vaisseau** — des défis optionnels liés à son historique de combat ("Ce vaisseau a détruit 10 frégates ennemies — mission : participer à un siège"). Compléter ces missions débloque des skins de coque uniques ou des titres affichés dans le hangar.

Ce système encourage le joueur à revenir régulièrement vérifier les missions disponibles (elles se renouvellent toutes les 72h) et à engager activement ses vaisseaux importants.

---

### 5d. Cicatrices de combat — identité narrative

Un vaisseau qui survit à un combat particulièrement difficile (perte de plus de 75% de sa coque, combat contre une flotte ×2 plus puissante) reçoit automatiquement une **Cicatrice**. Chaque cicatrice est un tag narratif généré aléatoirement parmi une liste : "Rescapé de la Nébuleuse Kha", "Survivant du Siège de l'Anneau IV", etc.

Les cicatrices sont affichées sur la carte du vaisseau dans le hangar. Elles n'ont aucun effet mécanique — elles sont purement narratives. Mais elles créent de l'attachement et de la fierté, et sont visibles des autres joueurs.

---

## Handoff

```
---
HANDOFF EMAGO
De : Agent 2 — Game Designer
À : Agent 7 — Développeur Base de données
Sujet : Schéma de données pour le système de vaisseaux complet
Date : 2025-01-29
---

### Contexte reçu
Conception du GDD complet du système de vaisseaux : classes, rareté RNG,
modules, XP/grades, et mécaniques de rétention (Pedigree, Forge, Missions, Cicatrices).

### Décisions prises
- Stats RNG : deux champs JSON distincts (base_stats immuable / current_stats calculé)
- Modules : table de relation séparée avec slot_index et niveau
- XP différentielle : calculée côté serveur, stockée en entier dans ships.combat_xp
- Forge : table forge_queue avec timestamps (asynchrone, suivi en temps réel)
- Cicatrices : table ship_scars avec tag_id (pool de ~500 tags narratifs)
- Pedigree : champ parent_ship_id nullable dans ships

### Livrable
GDD v1.0 complet — voir document ci-dessus

### Ce que l'Agent 7 doit savoir
- Un trigger PostgreSQL MUST prevent UPDATE sur la colonne base_stats après INSERT
- Les énums requis : ship_class (ATTACK/DEFENSE/SUPPORT/EXPLORATION), 
  rarity (COMMON/UNCOMMON/RARE/EPIC/LEGENDARY), ship_grade (0–5)
- La colonne current_stats est calculée et mise en cache Redis — PAS stockée en dur
- La table ship_modules doit avoir une contrainte d'unicité sur (ship_id, slot_index)
- La table forge_queue a besoin d'un index sur completed_at pour le scheduler

### Prochaine étape suggérée
Agent 3 (Architecte) peut maintenant concevoir les endpoints REST
pour le hangar (/ships), le loadout (/ships/{id}/modules), et la forge (/forge).
Agent 5 (Backend) peut commencer le service ship_stats_service.py
une fois le schéma de l'Agent 7 livré.
---
```