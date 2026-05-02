---
name: emago-attack-vector-audit
description: Audite un endpoint Emago (existant ou en cours de design) contre les 25 vecteurs d'attaque connus du projet documentés dans docs/08_qa_securite.md — ownership masqué (404 vs 403), double-soumission Forge, race conditions, manipulation RNG, énumération login, immuabilité base_stats via trigger PG, isolation WebSocket cross-player, math.floor pour ressources, rate-limit sliding-window. Sortie un rapport markdown avec risques par criticité (CRITIQUE / ÉLEVÉ / MOYEN / FAIBLE) et corrections suggérées avec ligne de code. Use when l'utilisateur dit "audit sécurité Emago", "vecteur d'attaque", "review sécurité endpoint", "OWASP Emago", "QA endpoint", "valide la sécurité de", "check sécurité router".
license: MIT
metadata:
  author: Antoine
  version: 1.0.0
  project: emago
  agent: 8-qa-securite
---

# emago-attack-vector-audit

Bloque les régressions sécurité avant qu'elles arrivent en prod. Encapsule les 25 vecteurs d'attaque documentés dans `docs/08_qa_securite.md`.

---

## Quand utiliser ce skill

- **Avant de merger** un PR qui ajoute/modifie un endpoint.
- **Audit périodique** (mensuel) des endpoints existants.
- **Suite à un bug sécurité** détecté en prod, pour vérifier si d'autres endpoints sont vulnérables.
- **Avant un release majeur** (v0.X.0), passer tous les routers au crible.

## Quand NE PAS utiliser ce skill

- Pour tester effectivement les vulnérabilités (= écriture de tests pytest) → utilise `emago-test-integration-writer`.
- Pour un test de charge / DoS → utilise k6 ou locust direct.
- Pour un audit OWASP général (pas Emago-specific) → utilise `engineering:security-review`.

---

## Catégories de vecteurs

### CRITIQUES (toujours bloquer le merge)

| # | Vecteur | Risque |
|---:|---|---|
| C1 | Ownership cross-player révèle existence ressource | Énumération |
| C2 | Double-soumission qui crée 2 ressources concurrentes | Duplication / vol |
| C3 | Modification `base_stats` après création | Triche RNG |
| C4 | Re-roll de stats (manipuler RNG) | Triche directe |
| C5 | Token JWT expiré accepté | Auth bypass |
| C6 | Manipulation XP en input API | Triche directe |
| C7 | SECRET_KEY fuitée (committed, logged) | Compromission totale |

### ÉLEVÉS

| # | Vecteur | Risque |
|---:|---|---|
| E1 | Vaisseau IN_FLEET envoyé en forge | État incohérent |
| E2 | WebSocket cross-player (channel pas isolé) | Fuite info |
| E3 | Énumération login (messages différents email inconnu vs MDP) | Découverte de comptes |
| E4 | Participation `/combat/{id}` non vérifiée | Lecture combats d'autrui |
| E5 | Pedigree avec parent d'autrui | Vol génétique |
| E6 | Rate-limit absent sur endpoint sensible | Abus, DoS |
| E7 | Injection SQL via JSONB | Data corruption |
| E8 | CORS trop permissif en prod (DEBUG=true en prod) | XSS facilité |

### MOYENS

| # | Vecteur | Risque |
|---:|---|---|
| M1 | `with_for_update` manquant sur mutation | Race condition |
| M2 | `math.floor` manquant sur comparaison ressources | Bug 1999.87 vs 2000 |
| M3 | N+1 queries | Perf dégradée |
| M4 | Pas d'index sur requête fréquente | Perf |
| M5 | Headers HTTP de sécurité manquants (HSTS, CSP, X-Frame) | XSS, clickjacking |
| M6 | `_active_research` mémoire (perdu redémarrage) | Data loss |
| M7 | Pas de heartbeat WS server-side | Connexions zombies |
| M8 | Logs avec données sensibles (tokens, MDP) | Fuite info |

### FAIBLES

| # | Vecteur | Risque |
|---:|---|---|
| F1 | Scaling WS horizontal pas activé | Performance future |
| F2 | Index JSONB pour participation combat | Perf scale |
| F3 | Heartbeat WS timeout | UX dégradée |
| F4 | Logs JSON pas centralisés | Debug difficile |
| F5 | Pas de monitoring dépendances (`pip-audit`) | Vulnérabilités tierces |

---

## Instructions

### Étape 1 — Cadrer l'audit

Demande à l'utilisateur :

1. **Cible** : un router (`app/routers/<name>.py`) ou un endpoint spécifique ?
2. **Profondeur** : audit rapide (CRITIQUE + ÉLEVÉ uniquement) ou complet (tous les vecteurs) ?
3. **Format de sortie** : checklist concise ou rapport détaillé ?
4. **Contexte** : suite à un bug ? Prep release ? Audit de routine ?

### Étape 2 — Lire le code

Lis le fichier router (et son service si applicable). Identifie :

- Liste des endpoints (méthode + path + fonction).
- Présence des helpers `_get_owned_*`, `_require_role`, `_check_resources`.
- `with_for_update` présents/absents.
- `math.floor(float(...))` sur comparaisons ressources.
- `publish_event` pour events WS.
- Codes erreur (en français ?).
- TODO / FIXME / XXX dans le code.

### Étape 3 — Appliquer la checklist

Pour chaque vecteur applicable au type d'endpoint :

| Type endpoint | Vecteurs critiques à vérifier |
|---|---|
| **GET avec `<id>`** | C1 (ownership 404) |
| **POST création** | C2, C5, C6, E6 (rate-limit), M1 (FOR UPDATE), M2 (math.floor) |
| **POST avec ID externe (forge, pedigree)** | C2, E5 (pedigree d'autrui), C1 |
| **PUT mutation** | C1, M1 (FOR UPDATE) |
| **DELETE** | C1, M1 |
| **WS handler** | E2 (channel isolé), C5 (token kind), F3 (heartbeat) |
| **Auth endpoint** | E3 (anti-énumération), E6 (rate-limit) |
| **Endpoint avec body JSONB** | E7 (injection JSONB) |

### Étape 4 — Pour chaque vecteur, statuer

Trois statuts possibles :

- ✅ **FAIT** : protection en place, code identifié.
- ⚠️ **EN COURS** : protection partielle ou TODO connu.
- ❌ **MANQUANT** : protection absente, action requise.

Pour chaque ❌, identifier :
- **Ligne(s) de code** concernées.
- **Fix proposé** (si simple) ou **suggestion** (si plus complexe).

### Étape 5 — Produire le rapport

Format attendu :

```markdown
## Audit sécurité — `app/routers/<name>.py`

**Date** : YYYY-MM-DD
**Auditeur** : Agent 8 (via emago-attack-vector-audit)
**Endpoints audités** : N

---

### Risques bloquants (CRITIQUE)

| # | Vecteur | Statut | Endpoint | Action |
|---:|---|---|---|---|
| C1 | Ownership masqué | ✅ FAIT | GET /xxx/{id} (ligne 45) | Helper `_get_owned_xxx` correct |
| C2 | Double-soumission | ❌ MANQUANT | POST /xxx (ligne 78) | Ajouter `select(...).with_for_update()` sur la planète |

### Risques élevés

(idem)

### Risques moyens

(idem)

### Recommandations prioritaires

1. **[CRITIQUE]** Ajouter `with_for_update` sur `POST /xxx` ligne 78 — race condition possible si deux clients créent simultanément.
2. **[ÉLEVÉ]** Ajouter rate-limit sur `POST /yyy` (action sensible) — ajouter `_LIMITS["yyy:create"] = 5` dans middleware.
3. **[MOYEN]** Refactor `math.floor(float(...))` sur ligne 102 — bug arrondi 1999.87.

### Tests à ajouter

(par criticité décroissante)

- ☐ `test_xxx_double_submission` (C2)
- ☐ `test_xxx_other_player_returns_404` (C1) — déjà présent ? (vérifier)
- ☐ `test_yyy_rate_limited` (E6)

### Références

- Documentation vecteurs : `docs/08_qa_securite.md` section 2.
- Exemples tests : `tests/routers/test_ships.py` (vecteurs C1 + V12).
```

### Étape 6 — Après l'audit

Si des risques CRITIQUES sont identifiés :
- Bloquer le merge.
- Créer des tickets / issues GitHub pour chaque action.
- Si déjà en prod : envisager hotfix immédiat.

Sinon : merger possible, ajouter les tests recommandés en suite.

---

## Examples

### Exemple 1 — Audit nouveau router

**User** : "Audit sécurité du nouveau router /espionage avant merge"

**Actions** :
1. Lit `app/routers/espionage.py`.
2. Identifie 3 endpoints : POST /probe, GET /reports, GET /reports/{id}.
3. Applique la checklist :
   - POST /probe : C2 ❌ (pas de FOR UPDATE sur deutérium → 2 sondes simultanées peuvent dépasser le coût). E6 ❌ (pas de rate-limit). M2 ❌ (compare deuterium float sans floor).
   - GET /reports : ✅ filtré sur owner_id (pas C1 puisque liste filtrée).
   - GET /reports/{id} : C1 ✅ (helper `_get_owned_report` 404).
4. Produit rapport avec 3 actions prioritaires.

### Exemple 2 — Audit suite à incident

**User** : "On a eu un bug : un joueur a forgé un ship d'un autre joueur. Audit /forge"

**Actions** :
1. Lit `app/routers/forge.py` + `app/services/forge_service.py`.
2. Suspecte C1 ou E5 (pedigree d'autrui).
3. Vérifie `start_forge` :
   - C1 ✅ : SELECT FOR UPDATE 2 ships + check `owner_id != player_id` → 403.
   - C2 ✅ : transaction unique avec FOR UPDATE.
4. Continue audit :
   - E5 : pedigree d'autrui ? Forge ne prend pas de parent — N/A.
5. Bug réel : peut-être race condition entre 2 forges sur le même ship_a ? Vérifier `_validate_pedigree_parent` dans `ship_build_service`. Trouvé : 403 si owner ≠ player. ✅
6. Conclusion : audit ne reproduit pas le bug rapporté → demander reproduction exacte (logs, payload exact).

### Exemple 3 — Audit complet pré-release

**User** : "Audit sécurité complet de tous les routers avant release v0.2.0"

**Actions** :
1. Lit chaque router de `app/routers/`.
2. Applique checklist complète.
3. Produit rapport agrégé :
   - 14 routers × ~5 endpoints = 70 audits.
   - Top 10 actions prioritaires.
   - Estimation effort de remédiation.
4. Suggère : créer milestone GitHub "Security Hardening v0.2.0" avec issues.

---

## Troubleshooting

### Comment savoir si un endpoint est "sensible" ?

**Critères** :
- Mute des ressources joueur (build, forge, fleet send).
- Crée une nouvelle entité (alliance create, expedition launch).
- Authentification (login, register, refresh).

→ Vérifier rate-limit + with_for_update + math.floor.

### L'endpoint est `GET` mais sans `<id>` — tester C1 ?

**Réponse** : non, C1 ne s'applique qu'aux endpoints qui prennent un ID en path. Pour un GET filtré sur `owner_id` (ex. `GET /ships`), il n'y a pas d'énumération possible.

### Le code utilise `with_for_update` mais la race condition existe quand même

**Cause** : transaction trop courte (commit avant la fin) ou requête FOR UPDATE pas sur la bonne table.

**Solution** :
- Vérifier que `with_for_update` est sur la ressource **partagée** (la planète si on consomme ses ressources, pas le ship).
- Vérifier qu'aucun `await db.commit()` explicite n'est dans le router (laisse `get_db_dep` gérer).
- Tester effectivement avec `pytest` + `asyncio.gather` pour double-soumission (cf. `emago-test-integration-writer`).

### J'identifie un vecteur non-listé

**Solution** : ajouter à `references/attack_vectors_full.md` + `docs/08_qa_securite.md` section 2. Documenter :
- Description du vecteur.
- Criticité estimée.
- Test associé.
- Endpoints potentiellement affectés.

### Faux positif : `with_for_update` "manquant" mais en fait inutile

**Cas** : endpoint qui ne mute rien (GET pur) ou qui mute uniquement la session (auth refresh).

**Solution** : marquer ✅ avec note "N/A — aucune mutation ressource concurrente possible".

---

## References

- `references/attack_vectors_full.md` — détail des 25 vecteurs avec exemples de code KO et fix.
- `references/audit_template.md` — template markdown du rapport d'audit.
- `references/router_audit_examples.md` — exemples d'audits passés sur les routers existants.
- `references/owasp_emago_mapping.md` — mapping OWASP Top 10 ↔ vecteurs Emago.

## Scripts

- `scripts/audit_router.py` — script Python qui parse un router et flag automatiquement les vecteurs détectables statiquement (helpers manquants, codes erreur incorrects, FOR UPDATE absent sur POST/DELETE).
