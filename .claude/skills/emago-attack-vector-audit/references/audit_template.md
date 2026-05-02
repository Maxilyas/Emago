# Audit sécurité Emago — `<router/feature>`

| Champ | Valeur |
|---|---|
| **Cible** | `app/routers/<name>.py` |
| **Date** | YYYY-MM-DD |
| **Auditeur** | Agent 8 (via `emago-attack-vector-audit`) |
| **Endpoints audités** | N |
| **Profondeur** | Rapide (CRITIQUE+ÉLEVÉ) / Complète |
| **Contexte** | Pré-merge / Audit routine / Post-incident |

---

## Endpoints scannés

| Méthode | Path | Function | Ligne |
|---|---|---|---:|
| GET | `/xxx` | `list_xxx` | 23 |
| POST | `/xxx` | `create_xxx` | 45 |
| GET | `/xxx/{id}` | `get_xxx` | 78 |

---

## Récap par criticité

| Criticité | ✅ FAIT | ⚠️ EN COURS | ❌ MANQUANT |
|---|---:|---:|---:|
| CRITIQUE | X | Y | Z |
| ÉLEVÉ | X | Y | Z |
| MOYEN | X | Y | Z |
| FAIBLE | X | Y | Z |

---

## Détail par vecteur

### CRITIQUES

#### C1 — Ownership masqué (404 vs 403)

| Endpoint | Statut | Détail |
|---|---|---|
| GET /xxx/{id} | ✅ FAIT | Helper `_get_owned_xxx` ligne 78, lève 404 |
| PUT /xxx/{id} | ❌ MANQUANT | Pas de check ownership → fuite info |

**Action** : ajouter `_get_owned_xxx` au début du handler PUT (ligne 92).

#### C2 — Double-soumission

(idem)

#### C3 — Immuabilité base_stats
✅ FAIT (trigger PG actif globalement, pas de modif visible dans ce router)

#### C4 — Re-roll RNG
N/A (pas d'endpoint de re-roll)

#### C5 — Token JWT
✅ FAIT (CurrentPlayer décodage automatique)

#### C6 — Manipulation XP
✅ FAIT (aucun endpoint accepte XP en input)

#### C7 — SECRET_KEY
N/A (pas de manipulation de SECRET_KEY dans ce router)

---

### ÉLEVÉS

#### E1 — Vaisseau IN_FLEET en forge
{détail}

#### E2 — WebSocket cross-player
{détail}

#### E3 — Énumération login
N/A

#### E4 — Participation combat
N/A

#### E5 — Pedigree d'autrui
{détail}

#### E6 — Rate-limit absent
{détail}

#### E7 — Injection JSONB
{détail}

#### E8 — DEBUG=true en prod
N/A (config-level)

---

### MOYENS

#### M1 — `with_for_update`
{détail}

#### M2 — `math.floor` ressources
{détail}

#### M3 — N+1 queries
{détail}

(autres si applicable)

---

### FAIBLES

(uniquement si profondeur=complète)

---

## Risques bloquants

(à corriger avant merge)

1. **C2 — Double-soumission `POST /xxx`** : ajouter `select(...).with_for_update()` ligne 56.
2. **E6 — Rate-limit absent `POST /xxx`** : ajouter `_LIMITS["xxx:create"] = 5/min`.

---

## Recommandations prioritaires

| # | Criticité | Action | Endpoint | Effort |
|---:|---|---|---|---|
| 1 | CRITIQUE | Ajouter `with_for_update` | POST /xxx | 5 min |
| 2 | ÉLEVÉ | Ajouter rate-limit | POST /xxx | 10 min |
| 3 | MOYEN | Refactor `math.floor` | POST /xxx ligne 102 | 5 min |

---

## Tests à ajouter

(par criticité décroissante)

- ☐ `test_xxx_double_submission` (C2)
- ☐ `test_xxx_other_player_returns_404` (C1) — déjà présent ?
- ☐ `test_xxx_rate_limited` (E6)
- ☐ `test_xxx_resources_floor_safety` (M2)

→ Utiliser `emago-test-integration-writer` pour générer le squelette.

---

## Verdict

- ☐ **GO** — aucun risque CRITIQUE, ÉLEVÉS gérables.
- ☐ **HOLD** — risques CRITIQUES à corriger avant merge.
- ☐ **HOTFIX** — risques en prod à corriger immédiatement.

---

## Annexe — Code analysé

### Helpers identifiés
- `_get_owned_xxx(xxx_id, player_id, db)` ligne 15 — lève 404, conforme.
- `_check_resources(planet, cost)` ligne 32 — utilise `math.floor` ✅.

### TODO/FIXME dans le code
- Ligne 89 : `# TODO: Phase 2 — index JSONB`
- Ligne 145 : `# FIXME: race condition possible`

### Messages d'erreur
✅ Tous en français, format cohérent.

---

## Références

- `docs/08_qa_securite.md` section 2 — vecteurs documentés.
- `references/attack_vectors_full.md` — détail par vecteur.
- Tests existants : `tests/routers/test_<name>.py` (si applicable).
