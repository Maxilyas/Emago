# Conventions de commit Emago

Conventions recommandées pour les messages de commit. Permet d'extraire l'agent et le scope automatiquement.

## Format

```
<type>(<scope>): <description>

[corps optionnel]

[footer optionnel]
```

## Types

| Type | Sens | Exemples |
|---|---|---|
| `feat` | Nouvelle fonctionnalité | `feat(forge): ajoute mécanique Dérive 5%` |
| `fix` | Correction de bug | `fix(planets): math.floor sur ressources` |
| `refactor` | Refonte sans changement comportement | `refactor(combat_engine): extraction _resolve_round` |
| `test` | Ajout/modif tests | `test(alliances): tests intégration création` |
| `docs` | Documentation | `docs(05): ajoute section service espionnage` |
| `chore` | Tâche de maintenance | `chore(deps): bump fastapi 0.115.5 → 0.116` |
| `perf` | Optimisation perf | `perf(ranking): batch SELECT au lieu de N+1` |
| `style` | Formatage / lint | `style: black + isort` |
| `ci` | CI/CD | `ci: ajoute job pip-audit` |
| `build` | Docker / build | `build: Dockerfile multi-stage` |

## Scopes typiques Emago

`auth`, `ships`, `modules`, `forge`, `planets`, `fleets`, `combat`, `ranking`, `scars`, `galaxy`, `expeditions`, `tech`, `daily`, `alliances`, `ws`, `tasks`, `migration`, `nginx`, `docker`, `ci`, `cd`, `frontend`, `backend`, `bdd`, `redis`, `config`.

## Mapping scope → agent

- `forge`, `combat`, `ships`, `modules`, `fleets`, `planets`, `tasks`, `ws`, `auth`, `expeditions`, `tech`, `daily`, `alliances`, `scars` → Agent 5
- `migration`, `bdd`, `redis` → Agent 7
- `frontend`, `pages`, `composants` → Agent 6
- `nginx`, `docker`, `ci`, `cd` → Agent 9
- `tests`, `audit`, `security` → Agent 8
- `gdd`, `balance`, `rng` → Agent 2
- `archi`, `adr` → Agent 3
- `uiux`, `palette`, `design` → Agent 4
- `docs`, `roadmap` → Agent 1

## Exemples de bons commits

```
feat(forge): ajoute mécanique Dérive 5% chance
fix(planets): math.floor sur comparaison ressources (bug 1999.87 vs 2000)
test(forge): test_forge_in_fleet_ship_rejected (vecteur Agent 8)
refactor(combat_engine): extraction _compute_synergy_bonuses
docs(02): GDD complet espionnage avec formules détection
chore(deps): bump fastapi 0.115.5 → 0.116, asyncpg 0.30 → 0.31
perf(ranking): batch SELECT players + ships au lieu de N+1
ci: ajoute job pip-audit + npm audit
```

## Tags Git

Les releases sont taggées `v0.X.Y` (semver light) :

- `v0.1.0` — Lancement Phase 1 (mai 2026)
- `v0.2.0` — Phase 2A : sécurité & robustesse
- `v0.3.0` — Phase 2B : espionnage + colonisation + marché
- `v1.0.0` — Stable, scale-out validé

## Branches

- `main` : protégée, déploiement automatique via CD.
- `develop` : intégration continue (CI sur push).
- `feat/<scope>-<courte-desc>` : feature branches.
- `fix/<scope>-<courte-desc>` : hotfixes.
- `docs/<scope>` : updates docs uniquement.
