# Exemples d'audits passés — routers Emago

Pour comprendre comment auditer en pratique. Ces audits ont été réalisés sur les routers existants.

## Audit `auth.py` — ✅ Globalement OK

**Endpoints** : 3 (register, login, refresh).

| Vecteur | Statut | Détail |
|---|---|---|
| C1 | N/A | pas d'endpoint avec ID utilisateur |
| C2 | ⚠️ EN COURS | register : pas de FOR UPDATE → 2 inscriptions simultanées même email peuvent passer (rare) |
| C5 | ✅ FAIT | python-jose valide exp + kind |
| E3 | ✅ FAIT | message 401 identique pour email inconnu vs MDP |
| E6 | ⚠️ EN COURS | register/login dans `_LIMITS` mais à valider en prod sur volume réel |

**Recommandation** : ajouter `with_for_update` sur SELECT player en register OU contrainte UNIQUE BDD garde-fou (déjà en place via `uq_players_username/email` → 409 propre).

---

## Audit `ships.py` + `modules.py` — ✅ Excellent

**Endpoints** : 4 + 3 = 7.

| Vecteur | Statut |
|---|---|
| C1 | ✅ FAIT (helper `_get_owned_ship` 404) |
| C2 | ✅ FAIT (FOR UPDATE sur démolition) |
| C3 | ✅ FAIT (trigger PG global) |
| E1 | ✅ FAIT (409 si IN_FLEET sur démolition, 409 si IN_FORGE sur module) |
| E5 | ✅ FAIT (`_validate_pedigree_parent` 403 cross-player explicit) |
| E6 | ✅ FAIT (rate-limit `ships:build` 10/min, `modules:install` 30/min) |
| M2 | ✅ FAIT (`math.floor` dans `_check_and_deduct_resources`) |

**Tests existants** : `tests/routers/test_ships.py` couvre C1, E5, validation slots premium.

**Verdict** : exemplaire, pattern à reproduire.

---

## Audit `forge.py` + `forge_service.py` — ✅ Bon avec notes

**Endpoints** : 3.

| Vecteur | Statut | Détail |
|---|---|---|
| C1 | ✅ FAIT (filtrage `player_id` sur GET history) |
| C2 | ✅ FAIT (FOR UPDATE 2 ships ORDER BY id anti-deadlock + planète) |
| E1 | ✅ FAIT (409 si statut ≠ DOCKED) |
| E5 | N/A (forge ne prend pas de parent externe) |
| E6 | ✅ FAIT (`forge:start` 5/min) |

**Tests existants** : `tests/routers/test_forge.py` couvre `different_rarities` (422), `same_ship` (400), `in_fleet` (409).

**À ajouter** :
- `test_forge_double_submission` (V2 explicite avec `asyncio.gather`).
- `test_forge_pedigree_other_player_parent` — pas applicable forge mais redondant avec audit `ship_build_service`.
- `test_forge_drift_5pct_distribution` (statistique sur 100 forges).

---

## Audit `planets.py` — ✅ Bon, MAIS gros router

**Endpoints** : 4 (487 lignes).

| Vecteur | Statut | Détail |
|---|---|---|
| C1 | ✅ FAIT (filtrage `owner_id`) |
| C2 | ✅ FAIT (FOR UPDATE planète sur build) |
| M2 | ✅ FAIT (commentaire ligne 419-422 explique le fix `math.floor`) |
| M3 | ⚠️ N+1 possible sur queue par planet — vérifier en prod |

**À surveiller** : taille du fichier (487 lignes). Candidat refacto pour extraire `BUILDING_CONFIG` dans un module dédié.

---

## Audit `fleets.py` — ✅ Excellent

**Endpoints** : 4 (382 lignes).

| Vecteur | Statut | Détail |
|---|---|---|
| C1 | ✅ FAIT (filtrage owner + helper sur recall) |
| C2 | ✅ FAIT (FOR UPDATE sur ships + fleet sur recall) |
| E1 | ✅ FAIT (409 si statut ship ≠ DOCKED) |
| E2 | ✅ FAIT (`publish_event(channel=f"player:{player.id}", ...)` cohérent) |

**Note** : `text("INSERT INTO fleet_ships ...")` ligne ~280 utilise paramètres binds → OK pour E7 injection.

**À ajouter** :
- `test_send_with_other_player_ship` (403, vecteur explicite).
- `test_send_with_in_flight_ship` (409).
- `test_recall_already_arrived` (409).

---

## Audit `combat.py` — ⚠️ Note de perf

**Endpoints** : 2.

| Vecteur | Statut | Détail |
|---|---|---|
| C1 | ✅ FAIT (404 si combat introuvable) |
| E4 | ✅ FAIT (helper `_is_participant` 403 si pas participant) |
| F2 | ⚠️ TODO | ligne 107 : "En phase 2 : utiliser un index JSONB PostgreSQL pour performance". Filtre Python actuellement |

**Note** : OK pour Phase 1, à optimiser si > 1k joueurs ou > 10k combats.

---

## Audit `expeditions.py` — ✅ Bon

**Endpoints** : 5.

| Vecteur | Statut | Détail |
|---|---|---|
| C1 | ✅ FAIT (filtrage `player_id` sur Redis SET) |
| C2 | ⚠️ EN COURS | pas de FOR UPDATE sur deutérium → race condition possible si 2 expéditions simultanées (rare en pratique) |
| E1 | ✅ FAIT (409 si ship ≠ DOCKED) |
| M2 | ✅ FAIT (`math.floor` deutérium) |

**Action recommandée** : ajouter `select(Planet).with_for_update()` sur le homeworld dans launch.

---

## Audit `tech.py` — ⚠️ Bug critique connu

**Endpoints** : 3.

| Vecteur | Statut | Détail |
|---|---|---|
| C1 | ✅ FAIT (filtrage `player.id`) |
| C2 | ⚠️ EN COURS | pas de FOR UPDATE → race conditions, MAIS surtout `_active_research` en mémoire |
| **M6** | ❌ MANQUANT | **`_active_research: dict` ligne 212 — perdu au redémarrage Uvicorn** |

**Action prioritaire** : migrer `_active_research` en BDD via migration `0007_research_queue` (cf. `emago-migration-alembic`).

---

## Audit `daily.py` — ✅ Globalement OK

**Endpoints** : 4.

| Vecteur | Statut |
|---|---|
| C1 | N/A (toutes opérations sur le current player) |
| C2 | ✅ Idempotent — login déjà claim → already_claimed=True (200, pas erreur) |
| E6 | ⚠️ Pas de rate-limit explicite (probablement pas nécessaire vu idempotence) |

---

## Audit `alliances.py` — ⚠️ Plusieurs notes

**Endpoints** : 7 (470 lignes).

| Vecteur | Statut | Détail |
|---|---|---|
| C1 | N/A (alliances publiques) |
| C2 | ⚠️ EN COURS | create : pas de FOR UPDATE → 2 créations simultanées même tag peuvent passer (UNIQUE BDD attrape) |
| E6 | ⚠️ EN COURS | rate-limit absent sur create + declare_war (vulnérable au spam guerre par leader malveillant) |
| (Phase 2) | TODO | declare_peace docstring : "phase 2 dual-leader" — actuellement leader unilatéral suffit |

**Actions** :
- Ajouter `_LIMITS["alliances:create"] = 5/min` et `["alliances:war_declared"] = 1/h`.
- (Phase 2) implémenter dual-leader paix.

---

## Audit `scars.py` — ✅ Bon (lecture publique intentionnelle)

**Endpoints** : 3.

| Vecteur | Statut | Détail |
|---|---|---|
| C1 | ⚠️ Partiel — scars publiques intentionnellement (pas de check ownership). Missions owner-only. |
| (autres) | ✅ FAIT |

**Note** : la lecture publique des cicatrices est un choix design (narratif). Pas un vecteur d'attaque.

---

## Audit `ranking.py` + `galaxy.py` — ✅ Endpoints publics OK

| Vecteur | Statut |
|---|---|
| C1 | N/A (lecture publique) |
| F2 | ⚠️ ranking : N+1 possible si chargement alliance_tag (TODO ligne 53) |

---

## Récap global

| Router | CRITIQUES | ÉLEVÉS | MOYENS | Action prioritaire |
|---|---:|---:|---:|---|
| auth | 0 | 1 | 0 | Rate-limit en prod confirmer |
| ships | 0 | 0 | 0 | — |
| modules | 0 | 0 | 0 | — |
| forge | 0 | 0 | 0 | — |
| planets | 0 | 0 | 0 | — |
| fleets | 0 | 0 | 0 | Tests à compléter |
| combat | 0 | 0 | 1 | Index JSONB Phase 2 |
| ranking | 0 | 0 | 1 | TODO alliance_tag |
| scars | 0 | 0 | 0 | — |
| galaxy | 0 | 0 | 0 | — |
| expeditions | 0 | 1 | 0 | FOR UPDATE deutérium |
| **tech** | 0 | 0 | **1** | **`_active_research` → BDD URGENT** |
| daily | 0 | 0 | 0 | — |
| alliances | 0 | 1 | 0 | Rate-limit war_declared |

**Global** : projet bien protégé. 2 actions critiques :
1. **`tech.py` `_active_research` migrer en BDD** (M6).
2. **`alliances.py` rate-limit declare_war** (E6).

Le reste est nominal pour Phase 1, à creuser au fil de Phase 2.
