# ADR-{NNN} : {Titre court de la décision}

| Champ | Valeur |
|---|---|
| **Date** | YYYY-MM-DD |
| **Statut** | Proposed / Accepted / Deprecated / Superseded by ADR-XXX |
| **Auteur** | {nom} |
| **Agents concernés** | {1, 3, 5, …} |
| **Tags** | {scaling, security, perf, devops, …} |

---

## Contexte

{Décris en 5-10 lignes la situation actuelle. Quelle contrainte pousse à décider maintenant ? Quel problème observé ?
Référence aux docs Emago : ex. "Cf. `docs/03_architecte.md` section 2 — décision actuelle X."}

## Forces en présence

- {Contrainte 1 — perf, sécurité, budget, deadline, dette}
- {Contrainte 2}
- {Contrainte 3}

---

## Options évaluées

### Option A — {Nom}

**Description** : {1 phrase}

**Avantages** :
- …
- …

**Inconvénients** :
- …
- …

**Coût d'implémentation** : faible / moyen / élevé
**Impact agents** : {liste}
**Réversibilité** : oui / non / partielle

---

### Option B — {Nom}

{idem}

---

### Option C — Statu quo (ne rien changer)

**Avantages** :
- Aucun coût d'implémentation
- Pas de risque de régression
- Permet de rester focus sur d'autres priorités

**Inconvénients** :
- {pourquoi ce choix ne tient pas long terme}

---

## Décision

> **Option retenue** : {A / B / C}

**Justification** :

{3-5 paragraphes expliquant pourquoi cette option l'emporte. Cite les contraintes Emago spécifiques (ex. "à <1000 joueurs simultanés, la simplicité d'APScheduler l'emporte sur la robustesse de Celery").}

---

## Conséquences

### Positives
- …
- …

### Négatives / risques
- …
- …

### Effets sur les autres agents

| Agent | Impact | Action requise |
|---|---|---|
| 5 — Backend | … | … |
| 7 — BDD | … | … |
| 9 — DevOps | … | … |

---

## Cohérence avec l'existant

Cette décision est :
- ☐ **Cohérente** avec les décisions actées dans `docs/03_architecte.md` section 2.
- ☐ **Étend** une décision existante (préciser laquelle).
- ☐ **Remplace** une décision existante → marquer l'ancienne comme `Deprecated` ou `Superseded by ADR-NNN`.

Décisions existantes liées :
- {ADR-XXX ou section X de `03_architecte.md`} — relation : {complète / contredit / précise}

---

## Plan d'implémentation

| Étape | Owner | Échéance | Statut |
|---|---|---|---|
| {action 1} | Agent X | sem 1 | À faire |
| {action 2} | Agent Y | sem 2 | À faire |
| Mise à jour `docs/0X_*.md` | Agent X | sem 1 | À faire |
| Tests d'intégration / régression | Agent 8 | sem 2 | À faire |
| Mise à jour `docs/03_architecte.md` section 2 | Agent 3 | sem 1 | À faire |

---

## Métriques de succès

Comment saurons-nous que la décision est bonne ?

- **Quantitatif** : {ex. p95 < 200ms, < 1% erreur scheduler, < 5min déploiement}
- **Qualitatif** : {ex. moins de support tickets, équipe à l'aise avec la nouvelle stack}

---

## Références externes

- {liens docs externes, RFC, articles, benchmarks}

## Annexe — Notes de discussion

{Optionnel : notes brutes des discussions Slack/réunions ayant mené à cette décision.}

---

*ADR-{NNN} créé le {DATE} par `emago-adr-writer`*
