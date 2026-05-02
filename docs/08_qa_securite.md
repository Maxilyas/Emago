# Agent 8 — QA & Sécurité

> Tests pytest, vecteurs d'attaque, audit OWASP, anti-triche, équilibrage. Garde-fou de l'équité du jeu.

---

## 1. Stratégie de tests

### Pyramide actuelle

```
          [ Tests E2E ]      ← Phase 2 (Cypress / Playwright)
        [ Tests Intégration ] ← test_auth, test_ships, test_forge (FAIT). À étendre.
      [   Tests Unitaires    ] ← test_ship_services 47 assertions (FAIT)
```

### Couverture actuelle

- **Tests services backend** : `tests/services/test_ship_services.py` (~418 lignes, 47+ assertions). Couvre RNG rareté, génération stats, Pedigree, find_best_stat, compute_current_stats (cap, affinité, grade), validate_module_slot, CombatShip.take_damage (immunité Grade 4), XP différentielle, compute_grade, fleet_power, should_earn_scar, merge_best_stats, rarity_upgrade, XP transfer Forge.
- **Tests routers** : `test_auth.py` (12 tests), `test_ships.py` (11 tests dont 2 vecteurs sécurité ownership), `test_forge.py` (5 tests).
- **Conftest** : 9 fixtures (test_engine, db_session, client, auth_client, registered_player, planet_id, built_ship, other_player_ship_id, ship_in_fleet, two_ships_different_rarity), mock Redis async.

### Cibles de qualité

- **Latence** : p95 < 200 ms sur tous les endpoints REST.
- **WebSocket** : 50 connexions simultanées sans dégradation.
- **Scheduler** : `forge_tick` (60 s) ne doit jamais dépasser 10 s d'exécution.
- **Coverage** : > 70 % sur services métier critiques (ship_build, ship_stats, combat_engine, forge).

---

## 2. Vecteurs d'attaque identifiés et statut

### Critiques (toutes traitées)

| # | Vecteur | Risque | Statut | Mesure de protection |
|---:|---|---|---|---|
| 1 | PUT /modules avec ship_id d'un autre joueur | CRITIQUE | ✅ FAIT | Helper `_get_owned_ship` → 404 (anti-énumération) |
| 2 | DELETE /ships/{id} sur ship d'autrui | CRITIQUE | ✅ FAIT | `ship.owner_id != player.id` → 404 |
| 3 | Double-soumission /forge (race condition) | CRITIQUE | ✅ FAIT | `SELECT FOR UPDATE` 2 ships ordonnés par ID + planète, transaction unique |
| 4 | Manipulation requêtes API (stat injection) | CRITIQUE | ✅ FAIT | Toute la logique de jeu serveur, base_stats immuable |
| 5 | Re-roll de stats RNG via UPDATE | CRITIQUE | ✅ FAIT | Trigger PG `prevent_base_stats_update` |
| 6 | Token JWT expiré accepté | CRITIQUE | ✅ FAIT | `python-jose` vérifie expiration + kind |
| 7 | Manipulation XP en input | CRITIQUE | ✅ FAIT | Aucun endpoint n'accepte XP en body |

### Élevés

| # | Vecteur | Risque | Statut |
|---:|---|---|---|
| 8 | Vaisseau IN_FLEET envoyé en forge | ÉLEVÉ | ✅ FAIT (guard `status != DOCKED` → 409) |
| 9 | WebSocket : recevoir events d'autrui | ÉLEVÉ | ✅ FAIT (channel `player:{id}` strict via Redis pub/sub) |
| 10 | Énumération d'utilisateurs (login) | ÉLEVÉ | ✅ FAIT (même message 401 pour email inconnu et mauvais MDP) |
| 11 | Injection SQL via JSONB | ÉLEVÉ | ✅ FAIT (SQLAlchemy paramétrisé partout) |
| 12 | Vérification participation /combat/{id} | ÉLEVÉ | ✅ FAIT (helper `_is_participant` → 403 si non participant, 404 si introuvable) |
| 13 | Pedigree avec parent d'autrui | ÉLEVÉ | ✅ FAIT (`_validate_pedigree_parent` 403 si owner ≠) |
| 14 | Rate limiting | ÉLEVÉ | ✅ FAIT (slowapi sliding window Redis) |

### Moyens

| # | Vecteur | Risque | Statut |
|---:|---|---|---|
| 15 | Farm de newbies (XP) | MOYEN | ✅ FAIT (XP différentielle décourage) |
| 16 | Race condition expeditions/launch (pas de FOR UPDATE) | MOYEN | ⚠️ EN COURS |
| 17 | Race condition tech/research (pas de FOR UPDATE) | MOYEN | ⚠️ EN COURS |
| 18 | Race condition alliances/create (pas de FOR UPDATE) | MOYEN | ⚠️ EN COURS |
| 19 | Race condition daily/login (pas de FOR UPDATE) | MOYEN | ⚠️ EN COURS |
| 20 | Headers HTTP en production (CORS, CSP, HSTS) | MOYEN | ✅ FAIT (Nginx conf.d/emago.conf : HSTS, CSP, X-Frame, X-Content) |
| 21 | _active_research mémoire perdue redémarrage | MOYEN | ⚠️ TODO migrer en BDD (`tech.py:212`) |
| 22 | Ranking N+1 queries | MOYEN | ⚠️ TODO optim |

### Faibles

| # | Vecteur | Risque | Statut |
|---:|---|---|---|
| 23 | Scaling WebSocket horizontal (sticky) | FAIBLE | ⚠️ Préparé (Redis pub/sub) — pas encore activé |
| 24 | Index JSONB combat_logs participation | FAIBLE | ⚠️ TODO Phase 2 (`combat.py:107`) |
| 25 | Heartbeat WS server-side (timeout) | FAIBLE | ⚠️ TODO |

---

## 3. Vérifications structurelles

### Anti-énumération (404 au lieu de 403)

Lorsqu'un joueur tente d'accéder à une ressource appartenant à un autre joueur, le serveur retourne **404 NOT FOUND** plutôt que **403 FORBIDDEN**, pour ne pas révéler l'existence de la ressource.

Exemples :
- `GET /ships/{id}` d'un autre joueur → 404 "Vaisseau introuvable."
- `DELETE /ships/{id}` d'un autre joueur → 404 (pas 403).
- `PUT /ships/{id}/modules/{slot}` d'un autre joueur → 404 via `_get_owned_ship`.

Exception légitime : `POST /forge` retourne 403 explicite si un parent appartient à un autre joueur (pas 404, car le joueur a fourni 2 IDs et a déjà confirmé qu'un n'est pas à lui).

### Anti-énumération login

```
POST /auth/login {email: "inconnu@x.com", password: "..."}
  → 401 "Email ou mot de passe incorrect."

POST /auth/login {email: "vrai@x.com", password: "FAUX"}
  → 401 "Email ou mot de passe incorrect."
```

Même message, même code. Tests `test_login_wrong_password` et `test_login_unknown_email` valident ce comportement.

### Immuabilité stats

Trigger PostgreSQL `prevent_base_stats_update` BEFORE UPDATE on `ships` lève une exception si `NEW.base_stats != OLD.base_stats`. Bypass via session var `emago.bypass_stats_trigger = 'true'` réservé aux migrations Alembic.

### Cap +150% par stat

Dans `ship_stats_service._compute_current_stats` : si `target > base × 2.5`, force `target = base × 2.5` et ajoute la stat à `cap_reached`. Test `test_cap_150pct_enforced` (6 modules CANNON niveau 5).

---

## 4. Couverture de tests par mécanique

### Tests services (`test_ship_services.py`)

| Mécanique | Tests | Couverture |
|---|---|---|
| Roll rarity | 4 (always_valid, common_most_frequent, thresholds, multiplier_ordering) | ✅ |
| Generate base stats | 7 (range, no_negative, errors, decimals) | ✅ |
| Pedigree | 4 (boost, no_mutate, unknown_stat) | ✅ |
| find_best_stat | 2 (highest, exclude_stealth_aura) | ✅ |
| compute_current_stats | 7 (no_modules, grade1, grade3_regen, cannon, affinity, cap150, grade5_stealth) | ✅ |
| validate_module_slot | 4 (valid, out_of_range, level4_premium) | ✅ |
| CombatShip.take_damage | 6 (shield_first, overflow, destroyed, immunity_g4) | ✅ |
| Differential XP | 4 (equal, stronger, weaker, audit) | ✅ |
| compute_grade | 6 (0 à 5) | ✅ |
| fleet_power | 2 (empty, comparison) | ✅ |
| should_earn_scar | 4 (dead, hull_75, power_2x, no_match) | ✅ |
| merge_best_stats | 2 (max, missing_key) | ✅ |
| rarity_upgrade | 2 (chain, legendary_not) | ✅ |
| XP transfer | 2 (30%, ratio_exact) | ✅ |

### Tests routers d'auth (`test_auth.py`)

5 tests register, 4 tests login, 3 tests refresh. Couvre 401/409/422.

### Tests routers ships (`test_ships.py`)

4 tests build, 3 tests get (dont vecteur ownership 404), 5 tests modules (dont install other_player → 404, slot invalide → 422, premium niveau 4 dans slot standard → 422, install puis remove).

### Tests routers forge (`test_forge.py`)

5 tests : different_rarities (422), same_ship (400), in_fleet (409), history, status_not_found (404).

---

## 5. Tests à compléter (gaps identifiés)

### Tests routers manquants

| Router | Tests à ajouter |
|---|---|
| **planets** | build_already_in_queue (409), build_unknown_building (400), build_insufficient_resources (402 avec `math.floor`), queue list |
| **fleets** | send_with_other_player_ship (403), send_with_in_flight_ship (409), recall_already_arrived (409), incoming_only_enemies |
| **combat** | get_combat_not_participant (403), get_combat_unknown (404), history limit cap |
| **expeditions** | launch_max_5_ships (400), launch_no_homeworld (404), launch_insufficient_deuterium (402), 6th ship rejected |
| **tech** | research_already_in_progress (409), research_prereq_not_met (409), max_level_reached (409) |
| **alliances** | create_already_member (409), create_low_score (403), create_dup_name_or_tag (409), join_full_alliance (409, ≥20), declare_peace_too_early (409, <48h), war_self (400) |
| **daily** | claim_already (409 idempotent OK), claim_not_completed (402) |
| **scars** | missions_grade_below_2 (403), claim_not_completed (409) |

### Tests sécurité

- WebSocket : token expiré → close 4001.
- WebSocket : token valide mais joueur supprimé → close 4004.
- WebSocket : message JSON malformé → `{"type": "error", "detail": "JSON invalide."}`.
- Rate limit : 11ème POST /ships/build dans la minute → 429 + Retry-After: 60.
- Replay combat : même seed → mêmes rounds (déterminisme).

### Tests d'intégration WebSocket

- Connexion → events → close. Multi-onglets. Reconnexion automatique. Cross-talking (joueur A ne reçoit pas events de joueur B).

### Tests de charge

- Locust ou k6 sur `/api/v1/ships/build` à 50 joueurs concurrents.
- Scheduler `resource_tick` avec 100 planètes : doit prendre < 5 s.
- 50 connexions WS simultanées avec ping/pong.

---

## 6. Audit OWASP Top 10 (2021)

| OWASP | Catégorie | Statut Emago |
|---|---|---|
| A01 | Broken Access Control | ✅ Helper `_get_owned_ship`, 404 anti-énumération, helper `_require_role` alliances |
| A02 | Cryptographic Failures | ✅ bcrypt password, JWT HS256, SECRET_KEY 64-char hex env-only, HTTPS forcé Nginx |
| A03 | Injection | ✅ SQLAlchemy paramétré partout, aucun SQL brut sauf `text("INSERT INTO fleet_ships ...")` (paramètres binds) |
| A04 | Insecure Design | ✅ RNG côté serveur, calculs de jeu serveur, immuabilité base_stats |
| A05 | Security Misconfiguration | ⚠️ EN COURS (CSP en place dans Nginx, à valider) |
| A06 | Vulnerable Components | ⚠️ EN COURS (audit `pip audit` + `npm audit` à automatiser dans CI) |
| A07 | Identification & Authentication Failures | ✅ JWT rotation refresh, anti-énumération, rate limit auth |
| A08 | Software & Data Integrity Failures | ✅ Trigger PG immuabilité, déterminisme combat |
| A09 | Security Logging & Monitoring | ⚠️ EN COURS (logs JSON structurés à valider, alertes via Uptime Kuma) |
| A10 | Server-Side Request Forgery (SSRF) | N/A (pas de fetch externe) |

### Headers HTTP de sécurité (`nginx/conf.d/emago.conf`)

```
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; ..." always;
```

CSP exact à raffiner pour Phase 2 (suppression `unsafe-inline`).

---

## 7. Tests d'équilibrage (jeu)

### À vérifier

| Cas | Statut | Comment |
|---|---|---|
| Légendaire Grade 5 vs 50 Communs Grade 0 | ⚠️ À tester | Cap +150% empêche-t-il le one-shot ? Le LEGENDARY doit pouvoir gagner mais pas trivialement |
| Distribution RNG sur 10 000 builds | ✅ Test 2000 tirages valide ratio COMMON 0.45-0.65 | Étendre à 10k pour précision |
| Forge 100 fois → distribution Dérive | ⚠️ À tester | Doit être ~5 % |
| XP différentielle ratio 1:1 vs 1:5 | ✅ Test pyramidal `test_stronger_enemy_gives_more` | OK |
| Combat replay déterminisme | ⚠️ À tester | Même seed → mêmes rounds exact |
| Cap +150% sur toutes les stats | ✅ Test pour DPS | Étendre aux autres stats |

---

## 8. Conventions de code

### Erreurs HTTP cohérentes

```python
raise HTTPException(status_code=404, detail="Vaisseau introuvable.")
raise HTTPException(status_code=409, detail=f"Impossible de démolir un vaisseau {ship.status.value}.")
raise HTTPException(status_code=402, detail="Ressources insuffisantes...")
```

Tous les messages en français. Détail explicite de la cause si non sécuritaire.

### Logging

`logging.basicConfig(...)` ; chaque module a `logger = logging.getLogger(__name__)`. Niveaux : DEBUG (verbose dev), INFO (events), WARNING (anomalies récupérables), ERROR (exceptions critiques).

### Validation Pydantic

Validators au niveau du schéma :
- `username` : strip + len 3-32 + alphanumérique avec `_`.
- `password` : len ≥ 8.
- `email` : `EmailStr` (Pydantic standard).

Erreurs 422 automatiques avec détails par champ.

---

## 9. Audit dépendances

`requirements.txt` (extrait) :
```
fastapi>=0.115
uvicorn[standard]>=0.30
sqlalchemy>=2.0
asyncpg>=0.29
alembic>=1.13
redis>=5.0
python-jose[cryptography]>=3.3
bcrypt>=4.1
pydantic>=2.7
pydantic-settings>=2.0
APScheduler>=3.10
slowapi (rate-limit)
pytest, pytest-asyncio, httpx (test)
```

À automatiser : `pip-audit` dans le job CI.

`package.json` frontend (extrait) :
```
react ^18.3.1, typescript ^5.5.3, vite ^5.3.4
@tanstack/react-query ^5.51, zustand ^4.5.4
react-router-dom ^6.26, react-hot-toast ^2.4
date-fns ^3.6, lucide-react ^0.414, tailwind ^3.4
```

À automatiser : `npm audit` dans le job CI.

---

## 10. Améliorations QA & Sécurité à prévoir

| Tâche | Priorité |
|---|---|
| Tests d'intégration routers manquants (alliances, fleets, combat, expeditions, tech) | Haute |
| Tests d'intégration WebSocket (auth, isolation, reconnexion) | Haute |
| Tests de charge (locust ou k6) sur endpoints critiques | Moyenne |
| Tests E2E critiques (Cypress / Playwright) — login, build, forge, combat | Moyenne |
| `pip-audit` + `npm audit` dans CI | Haute |
| `with_for_update` sur expeditions/launch, tech/research, alliances/create, daily/login | Moyenne |
| Replay combat déterminisme test | Moyenne |
| Heartbeat WS serveur-side avec timeout | Moyenne |
| Test équilibrage Légendaire Grade 5 vs 50 Communs | Haute |
| CSP plus stricte (suppression `unsafe-inline`) | Moyenne |
| Audit OWASP A05 (config) + A06 (deps) trimestriel | Haute |
| Procédure incident response documentée | Haute |
| Honeypot endpoint pour détecter scans | Basse |
| Anti-bot (CAPTCHA optionnel) sur register en cas d'abus | Basse |

---

*Document Agent 8 — Mai 2026*
