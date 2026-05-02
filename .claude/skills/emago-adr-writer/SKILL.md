---
name: emago-adr-writer
description: Rédige un Architecture Decision Record (ADR) pour le projet Emago en respectant la stack (Python 3.12 / FastAPI / SQLAlchemy 2.0 async / asyncpg / PostgreSQL 16 / Redis 7 / APScheduler / WebSocket / Docker / Nginx) et les décisions existantes documentées dans docs/03_architecte.md. Stocke l'ADR dans docs/decisions/ avec numérotation incrémentale et template Contexte/Options/Décision/Conséquences/Cohérence avec existant. Use when l'utilisateur dit "ADR Emago", "écris une décision", "documenter le choix de", "trade-off X vs Y Emago", "Celery vs APScheduler", "scale-out", "trancher entre".
license: MIT
metadata:
  author: Antoine
  version: 1.0.0
  project: emago
  agent: 3-architecte
---

# emago-adr-writer

Rédige des Architecture Decision Records (ADRs) cohérents avec l'écosystème Emago. Chaque ADR documente une décision technique avec son contexte, les options évaluées, le choix retenu, et ses conséquences.

---

## Quand utiliser ce skill

- Choix technique structurant (ex. WebSocket sticky sessions, Celery vs APScheduler, multi-VPS).
- Trade-off avec impact long terme (sécurité vs performance, simplicité vs scalabilité).
- Décision qui résout une "Question ouverte" de `docs/01_chef_de_projet.md` section 8 ou `docs/10_ameliorations.md` section 5.
- Évolution majeure de la stack (ex. migration PostgreSQL 16 → 17, Redis 7 → 8).
- Quand on remplace une décision passée (Superseded by ADR-XXX).

## Quand NE PAS utiliser ce skill

- Pour une décision triviale (renommer une variable, ajouter une route mineure) — pas besoin d'ADR.
- Pour un design de mécanique de jeu → utilise `emago-gdd-writer`.
- Pour un choix purement UI → utilise `emago-screen-spec`.

---

## Instructions

### Étape 1 — Cadrer la décision

Pose à l'utilisateur :

1. **Sujet en une phrase** : "Choisir entre X et Y pour …"
2. **Pourquoi maintenant** : qu'est-ce qui force la décision (incident, scale, demande Phase 2…) ?
3. **Agents concernés** (1 à 9) — qui est impacté par la décision ?
4. **Contraintes** : budget, perf cible, deadline, contrainte de stack imposée ?

### Étape 2 — Vérifier les ADRs existants

Liste les ADRs déjà écrits dans `docs/decisions/`. Vérifie qu'aucun n'aborde déjà ce sujet (sinon → mise à jour ou Superseded). Si la décision contredit la section 2 de `docs/03_architecte.md` (Décisions techniques majeures), c'est un signal qu'on remplace une décision existante.

### Étape 3 — Identifier les options réalistes

Pour chaque option, capture :
- Description (1 phrase).
- Avantages (3-5 bullets).
- Inconvénients (3-5 bullets).
- Coût d'implémentation (faible/moyen/élevé).
- Impact sur les agents.

**Toujours** inclure l'option "Statu quo" (ne rien changer) avec ses pour/contre — souvent la bonne décision si l'urgence est faible.

### Étape 4 — Croiser avec l'existant

Vérifie la cohérence avec les décisions déjà actées (cf. `references/architecture_decisions.md`) :
- Pile asynchrone end-to-end ? (FastAPI / asyncio).
- Source de vérité = serveur ?
- Immuabilité `base_stats` via trigger PG ?
- RNG via `secrets.SystemRandom` ?
- Scheduler in-process (APScheduler) ?
- WebSocket via Redis pub/sub ?

Si la décision contredit l'une de ces, c'est un point à noter dans la section "Cohérence avec existant".

### Étape 5 — Rédiger l'ADR

Numérotation incrémentale : `docs/decisions/ADR-NNN-titre-court.md` où `NNN` = max existant + 1, padding 3 chiffres.

Utilise le template `references/adr_template.md`.

### Étape 6 — Mettre à jour les docs liées

- `docs/03_architecte.md` section 2 : ajouter ligne au tableau "Décisions techniques majeures".
- `docs/10_ameliorations.md` section 5 : retirer la question si elle était ouverte, marquer "Tranchée par ADR-NNN".
- `docs/01_chef_de_projet.md` section 8 : idem.

---

## Examples

### Exemple 1 — Décision claire

**User** : "Écris un ADR sur le choix de garder APScheduler in-process plutôt que Celery"

**Actions** :
1. Vérifie le numéro suivant (ex. ADR-007).
2. Identifie les options : APScheduler / Celery / pgcron / dramatiq.
3. Note les contraintes : <1000 joueurs (cf. `docs/03_architecte.md`), 1 VPS, équipe solo.
4. Note les avantages APScheduler : zéro infra additionnelle, code Python pur, déjà en place.
5. Note les inconvénients : pas de retry distribué, pas de scale horizontal natif.
6. Décision : garder APScheduler tant que < 1000 joueurs, prévoir migration Celery avec ADR à venir.
7. Sort `docs/decisions/ADR-007-scheduler-in-process.md`.
8. Met à jour `docs/03_architecte.md` ligne `Scheduler` du tableau section 2.

### Exemple 2 — Décision contraire à l'existant

**User** : "ADR : on doit passer toutes les écritures BDD sur un cluster Postgres répliqué"

**Actions** :
1. Identifie que ça contredit l'option actuelle "VPS unique" de `docs/03_architecte.md`.
2. Section "Cohérence avec existant" : signale que l'ADR remplace partiellement la décision actuelle "VPS unique".
3. Status : "Proposed" (à valider Agent 1 + Agent 9).
4. Met en footer : "Cet ADR rend nécessaire la mise à jour de DEVOPS_SPEC.md et de docker-compose.prod.yml".

### Exemple 3 — Décision urgente

**User** : "Vite un ADR : on a un incident, faut décider entre rollback ou hotfix maintenant"

**Actions** :
1. Format ADR ultra-court (Lightweight ADR) : Contexte (1 paragraphe) + Décision (1 paragraphe) + À auditer plus tard.
2. Status : "Accepted (urgence)".
3. Suggère de faire un suivi post-incident avec un ADR complet.

---

## Troubleshooting

### Numérotation ADR conflictuelle

**Cause** : deux ADRs avec le même numéro (cas de PR concurrentes).
**Solution** : renuméroter le plus récent à `max(existing) + 1` avant merge.

### Pas certain que ce soit une décision méritant un ADR

**Solution** : si la décision a un impact sur ≥ 2 agents OU sur la stack OU sur la perf/sécurité prod → ADR. Sinon, simple commentaire dans le code ou note dans `docs/`.

### Décision déjà actée mais pas dans `docs/decisions/`

**Cause** : décisions historiques non formalisées (cf. section 2 de `03_architecte.md`).
**Solution** : créer un ADR rétroactif (status "Accepted (rétroactif)") pour formaliser. Date = date estimée de la décision originelle.

### La décision implique un agent absent

**Solution** : marquer "Status : Proposed" et lister explicitement les agents dont l'avis est attendu avant validation.

---

## References

- `references/adr_template.md` — template markdown ADR.
- `references/architecture_decisions.md` — extrait des décisions techniques actées (section 2 de `03_architecte.md`).
- `references/existing_decisions_open.md` — questions ouvertes en attente d'ADR (section 5 de `10_ameliorations.md`).
