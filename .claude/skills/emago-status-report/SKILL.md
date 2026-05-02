---
name: emago-status-report
description: Génère un rapport d'avancement hebdomadaire du projet Emago basé sur les docs/ du projet, l'activité Git récente, et les tâches "EN COURS" / "À FAIRE" dans chaque doc agent. Sortie un markdown structuré par agent (Agent 1-9) avec sections FAIT / EN COURS / NOUVEAUX BLOCKERS / SEMAINE PROCHAINE. Use when l'utilisateur dit "fais le point Emago", "rapport hebdo", "où on en est", "standup Emago", "synthèse de la semaine", "weekly report Emago", "qu'est-ce qui a avancé".
license: MIT
metadata:
  author: Antoine
  version: 1.0.0
  project: emago
  agent: 1-chef-de-projet
---

# emago-status-report

Génère un rapport hebdomadaire structuré du projet Emago. Coordonne lecture de la documentation projet, analyse Git, et synthèse pour produire un standup auto-généré.

---

## Quand utiliser ce skill

- Standup hebdomadaire Agent 1 (Chef de projet).
- Avant un point projet avec parties prenantes.
- Après un push de commits importants pour acter le statut.
- Quand on demande "où on en est" sur une mécanique précise (espionnage, alliances, frontend…).

## Quand NE PAS utiliser ce skill

- Pour un rapport d'incident → utilise `engineering:incident-response`.
- Pour une décision technique → utilise `emago-adr-writer`.
- Pour un audit sécurité → utilise `emago-attack-vector-audit`.

---

## Instructions

### Étape 1 — Cadrer la fenêtre temporelle

Demande à l'utilisateur :
- Période : "depuis quand ?" (défaut : 7 derniers jours).
- Périmètre : tous les agents, ou un sous-ensemble (ex. uniquement Agent 5 + 6 + 8 si sprint sécurité) ?
- Format de sortie : markdown court (≤ 1 page) ou détaillé (≥ 2 pages) ?

### Étape 2 — Lire les sources

Sources de vérité, dans l'ordre :

1. **`docs/01_chef_de_projet.md`** — section 7 (Roadmap actuelle) et section 9 (Tableau de bord global).
2. **`docs/10_ameliorations.md`** — Sprint Phase 2A/2B/2C avec priorités.
3. **Pour chaque agent concerné** : section "Améliorations à prévoir" de sa doc (`docs/0X_*.md` dernière section).
4. **Git log** : `git log --since="<date>" --oneline --no-merges` pour voir ce qui a été livré.
5. **Optionnel** : si MCP GitHub connecté, chercher les PR mergées et les issues fermées sur la fenêtre.

### Étape 3 — Croiser et synthétiser

Pour chaque agent :
- Marque ✅ FAIT les tâches dont les commits matchent.
- Marque 🚧 EN COURS celles taggées comme telles ou avec activité partielle.
- Marque ⚠️ BLOCKER les tâches avec dépendances non résolues (cf. section "Décisions ouvertes" de `01_chef_de_projet.md`).
- Liste les **3 prochaines actions prioritaires** depuis `10_ameliorations.md`.

### Étape 4 — Produire le rapport

Utilise le template `references/report_template.md`. Toujours respecter cet ordre :

1. **Résumé exécutif** (3-5 lignes max).
2. **Métriques de la semaine** (commits, PRs, issues, lignes code, tests ajoutés si possible).
3. **Avancement par agent** (sections collapsibles si format long).
4. **Blockers et décisions à prendre** (extraite de section 8 de `01_chef_de_projet.md`).
5. **Prochaine semaine — top 3 priorités** (par agent ou globales).
6. **Annexe** : commits notables, références aux docs.

### Étape 5 — Proposer mise à jour des docs

À la fin du rapport, demande à l'utilisateur :
> "Veux-tu que je mette à jour `docs/01_chef_de_projet.md` (section 9 Tableau de bord) ou `docs/10_ameliorations.md` selon ce qui a évolué cette semaine ?"

Si oui, utilise `emago-roadmap-update` (autre skill) ou édite directement.

---

## Examples

### Exemple 1 — Demande simple

**User** : "Fais le point Emago de la semaine"

**Actions** :
1. Lit `docs/01_chef_de_projet.md` + `docs/10_ameliorations.md`.
2. Run `git log --since="7 days ago" --oneline --no-merges`.
3. Produit un rapport markdown avec 9 sections agent + résumé exécutif.
4. Met en évidence 2 blockers : "Espionnage GDD pas finalisé bloque Agent 5", "Tests d'intégration alliances absents".

### Exemple 2 — Périmètre restreint

**User** : "Standup Emago côté backend uniquement, sur les 14 derniers jours"

**Actions** :
1. Filtre sur Agent 5 + Agent 7 (services et migrations).
2. Run `git log --since="14 days ago" -- backend/`.
3. Rapport ciblé avec 2 sections agent + roadmap backend Phase 2A.

### Exemple 3 — Format ultra-court

**User** : "Donne-moi le TL;DR Emago de la semaine en 5 bullets"

**Actions** :
1. Skip les sections détaillées.
2. Sort 5 bullets : 1 résumé + 3 progrès clés + 1 blocker.

---

## Troubleshooting

### Aucun commit dans la fenêtre

**Cause** : repo Git pas accessible OU période trop courte OU branche pas synchronisée.
**Solution** : élargir la fenêtre ; pull avant ; basculer sur lecture `docs/` uniquement et signaler l'absence d'activité Git.

### Trop de commits — bruit

**Cause** : refactor en masse, ou commits trop granulaires.
**Solution** : grouper par fichier modifié (ex. tous les commits sur `app/routers/alliances.py`). Utiliser `--shortstat` pour mesurer l'ampleur.

### Conflit entre docs et code

**Cause** : tâche marquée "À FAIRE" dans `docs/` mais le commit suggère qu'elle est faite.
**Solution** : signaler explicitement dans le rapport sous "Inconsistances doc ↔ code" et proposer mise à jour `docs/`.

### Multi-agents ambigus

**Cause** : un commit touche backend + BDD + tests à la fois.
**Solution** : attribuer à l'agent principal (Agent 5 si router, 7 si migration, 8 si test) mais mentionner les co-agents en note.

---

## References

- `references/report_template.md` — template markdown complet du rapport.
- `references/agent_responsibilities.md` — mapping agent → doc → fichier code (utile pour attribuer un commit).
- `references/git_patterns.md` — patterns de commit Emago (préfixes, conventions).

## Scripts

- `scripts/git_summary.sh` — wrapper bash autour de `git log` qui sort un JSON par auteur et par fichier touché. Utilisable comme : `bash scripts/git_summary.sh --since="7 days ago" --format=json`.
