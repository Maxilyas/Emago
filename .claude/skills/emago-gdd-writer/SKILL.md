---
name: emago-gdd-writer
description: Conçoit et documente une mécanique de jeu Emago en respectant les piliers du projet (fun, équitable, zéro pay-to-win) et les contraintes techniques (Python/FastAPI/PostgreSQL/WebSocket). Produit une entrée GDD structurée avec description de la mécanique, formules d'équilibrage, cas limites, notes pour les développeurs (Agents 5/6/7). Met à jour docs/02_game_designer.md. Use when l'utilisateur dit "design mécanique Emago", "GDD espionnage", "mécanique de marché", "formule d'équilibrage", "ajoute une feature de jeu", "design système de X", "comment fonctionne Y dans le GDD".
license: MIT
metadata:
  author: Antoine
  version: 1.0.0
  project: emago
  agent: 2-game-designer
---

# emago-gdd-writer

Conçoit et documente des mécaniques de jeu Emago cohérentes avec le GDD existant. Garantit l'équilibre, la jouabilité et l'implémentabilité avant de transmettre aux agents techniques.

---

## Quand utiliser ce skill

- Concevoir une nouvelle mécanique de jeu (espionnage, marché galactique, guildes, artefacts…).
- Modifier une mécanique existante (rebalancer les classes de vaisseaux, ajuster les seuils XP, changer les probabilités RNG).
- Répondre à une question de design ("combien de temps pour forger un LEGENDARY ?", "faut-il limiter les forges par jour ?").
- Rédiger une entrée GDD propre avant de passer à l'implémentation.

## Quand NE PAS utiliser ce skill

- Pour simuler chiffrée l'impact d'une mécanique → utilise `emago-balance-simulator` d'abord.
- Pour une décision technique (API shape, modèle BDD) → utilise `emago-adr-writer`.
- Pour coder la mécanique → utilise `emago-router-scaffold` (Agent 5) + `emago-service-pattern` (Agent 5).

---

## Instructions

### Étape 1 — Cadrer la mécanique

Pose à l'utilisateur :

1. **Nom de la mécanique** (ex. "Espionnage", "Marché galactique", "Artefacts anciens").
2. **Objectif joueur** : qu'est-ce que le joueur cherche à faire avec cette mécanique ?
3. **Piliers concernés** : fun / équité / zéro pay-to-win — lesquels sont mis en tension ?
4. **Contraintes connues** : stack technique, temps de dev estimé, phase (1 = MVP, 2 = enrichissement).
5. **Mécaniques voisines** : quelles mécaniques existantes interagissent (flottes, forge, alliances) ?

### Étape 2 — Vérifier la cohérence avec le GDD existant

Lire `docs/02_game_designer.md` pour :
- Identifier si une mécanique similaire existe (éviter les doublons).
- Aligner sur les constantes déjà décidées (rareté, classes, XP, coûts de build).
- Repérer les "Questions ouvertes" dans `docs/01_chef_de_projet.md` section 8 — la mécanique répond-elle à l'une d'elles ?

### Étape 3 — Concevoir la mécanique

Structurer en 5 parties :

#### A. Description de la mécanique
- 2-3 phrases : ce que le joueur fait et ce qu'il obtient.
- Exemple joueur typique (parcours du casual et du hardcore).

#### B. Formules / Valeurs
- Tableaux de valeurs précis (coûts, durées, probabilités, seuils).
- Toute formule mathématique avec variables nommées.
- Comparaison avec les mécaniques similaires (ex. coût espionnage vs coût forge).

#### C. Cas limites à prévoir
- Ce qui pourrait créer un déséquilibre (farming, exploit, spam).
- Ce qui casse l'équité (avantage pay-to-win implicite).
- Cas edge (0 vaisseaux, valeurs négatives, joueur sans planète).

#### D. Notes pour Agent 5 (Dev Backend)
- Tables BDD nécessaires (nouvelle ou extension d'existante).
- Endpoints API requis (méthode, path, payload estimé).
- Events WebSocket à émettre.
- Jobs scheduler si processus asynchrone.

#### E. Notes pour Agent 6 (Dev Frontend)
- Écrans impactés ou à créer.
- Données temps réel (refetch interval, WS events).
- Composants réutilisables potentiels.

### Étape 4 — Vérification piliers

Avant de livrer, cocher :
- ☐ **Fun** : la mécanique est-elle engageante pour casual ET hardcore ?
- ☐ **Équité** : pas d'avantage disproportionné pour les gros joueurs ?
- ☐ **Zéro pay-to-win** : aucun chemin qui nécessite de l'argent réel ?
- ☐ **Implémentable** : faisable avec Python/FastAPI/PostgreSQL/Redis/WS ?
- ☐ **Cohérente** : n'entre pas en conflit avec une mécanique GDD existante ?

Si un pilier est rouge → ajuster la mécanique ou documenter explicitement le compromis.

### Étape 5 — Mettre à jour `docs/02_game_designer.md` (obligatoire)

- Ajouter la mécanique dans la section appropriée.
- Si modification d'une mécanique existante : mettre à jour les formules + noter la version (ex. "v1.1 — rebalance grade thresholds").
- Si question ouverte résolue : la retirer de `docs/01_chef_de_projet.md` section 8.

### Étape 6 — Handoff vers les agents techniques

Produire un brief au format handoff Emago :

```
HANDOFF EMAGO
De : Agent 2 — Game Designer
À : Agent 3 — Architecte (validation technique), puis Agent 5 — Dev Backend
Sujet : [Nom mécanique]
---
### Contexte reçu
[Ce qui a été demandé]
### Décisions prises
[Choix de design et pourquoi]
### Livrable
[La section GDD produite]
### Ce que l'agent destinataire doit savoir
[Contraintes, dépendances, points d'attention]
### Prochaine étape suggérée
[emago-adr-writer si décision archi, ou emago-router-scaffold si impl directe]
```

---

## Examples

### Exemple 1 — Nouvelle mécanique : espionnage

**User** : "Design la mécanique d'espionnage pour Emago"

**Actions** :
1. Cadrage : objectif = observer les ressources et flottes adverses. Pilier tension = équité (l'info stratégique ne doit pas avantager trop les gros).
2. GDD existant : flottes + missions déjà là. Espionnage = nouvelle mission type ESPIONAGE.
3. Mécanique : envoi d'une flotte d'exploration dédiée (furtivité élevée), durée = distance × speed, résultat JSONB (ressources visibles ?, flottes ?, niveau bâtiments ?), probabilité de détection = tech_espionage_target / tech_espionage_prober.
4. Formules : détection `P = max(0, tech_def / tech_att - 0.5)`, coût flotte 1 ship EXPLORATION minimum.
5. Cas limites : espionnage de soi-même → bloquer 400. Spam espionnage → rate-limit 5/min. Espionnage d'une alliance amie → permettre si coalition.
6. Notes Agent 5 : nouvelle table `espionage_reports`, endpoints `/espionage/probe` + `/espionage/reports`, event WS `espionage.report_ready`, job scheduler pour arrivée sonde.
7. Met à jour `docs/02_game_designer.md` section espionnage.

### Exemple 2 — Rebalance existant : thresholds XP

**User** : "Les joueurs atteignent Grade 5 trop vite, on veut rallonger la progression"

**Actions** :
1. Lire la constante actuelle : `_GRADE_THRESHOLDS = [(5, 40_000), (4, 15_000), ...]`.
2. Simuler avec `emago-balance-simulator` : combien de combats pour Grade 5 actuellement ?
3. Proposer nouveau seuil Grade 5 à 60 000 (soit +50 %) pour ~120 combats au lieu de 80.
4. Vérifier cohérence : Grade 4 immunité reste accessible en ~60 combats.
5. Note Agent 5 : changer la constante dans `combat_engine.py` ligne `_GRADE_THRESHOLDS`.
6. Met à jour `docs/02_game_designer.md` tableau des seuils XP.

### Exemple 3 — Question d'équilibrage

**User** : "Est-ce qu'un joueur peut réaliser un full LEGENDARY en jouant seulement ?"

**Actions** :
1. Calcul probabiliste : probabilité build direct LEGENDARY = 1%. Probabilité via forge = 100% depuis 2 EPIC. EPIC = 5%.
2. Chemin joueur : build 40 ships en moyenne pour obtenir 2 EPIC, forge 1 fois. Build ~2000 ships pour obtenir 2 EPIC directement. Ou ~3 cycles avec forge.
3. Verdict : oui, accessible sans pay-to-win. Le joueur hardcore peut full LEGENDARY en ~1 semaine de jeu intensif.
4. Recommandation : ok pour le GDD, aucune modification requise.

---

## Troubleshooting

### La mécanique déséquilibre le jeu selon emago-balance-simulator

**Solution** : ajuster les paramètres (coûts, probabilités, cooldowns) dans l'itération. Documenter dans le GDD le ratio cible (ex. "un LEGENDARY ne doit pas gagner > 75 % de ses combats contre 10 COMMON").

### La mécanique nécessite une décision d'architecture

**Cause** : besoin d'une nouvelle table, d'un nouveau service Redis, ou d'une modification du WS.
**Solution** : livrer d'abord l'entrée GDD, puis transmettre à Agent 3 pour `emago-adr-writer` avant l'implémentation.

### Conflit avec une mécanique existante

**Cause** : deux mécaniques qui permettent d'obtenir le même avantage par des voies différentes.
**Solution** : documenter le conflit dans le GDD + demander arbitrage à Agent 1 (Chef de projet).

---

## References

- `references/gdd_template.md` — template d'entrée GDD avec toutes les sections.
- `references/existing_mechanics.md` — résumé des mécaniques GDD existantes (rareté, forge, combat, XP, cicatrices, alliances).
- `references/balance_constraints.md` — contraintes d'équilibre à respecter (winrates cibles, durées de progression, coûts relatifs).
