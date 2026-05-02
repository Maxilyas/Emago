# Mapping Agent → Périmètre de code Emago

Utilisé pour attribuer un commit à un agent automatiquement.

| Agent | Doc | Périmètre code | Exemples de fichiers |
|---|---|---|---|
| 1 — Chef de projet | `01_chef_de_projet.md` | `docs/`, README projet | `docs/*.md`, root README |
| 2 — Game Designer | `02_game_designer.md` | GDDs, formules services | `*GDD*.md`, services avec constantes équilibrage |
| 3 — Architecte | `03_architecte.md` | Architecture, deps inter-modules | `app/main.py`, `app/core/config.py`, ADRs |
| 4 — UI/UX | `04_uiux_designer.md` | Spec UI, composants visuels | `UIUX_SPEC.md`, `frontend/src/index.css`, `tailwind.config.js` |
| 5 — Dev Backend | `05_dev_backend.md` | Routers, services, tasks, WS | `app/routers/*.py`, `app/services/*.py`, `app/tasks/*.py`, `app/websocket/*.py` |
| 6 — Dev Frontend | `06_dev_frontend.md` | Pages, composants, hooks, stores | `frontend/src/pages/*.tsx`, `frontend/src/components/**/*.tsx`, `frontend/src/hooks/*.ts`, `frontend/src/stores/*.ts` |
| 7 — Dev BDD | `07_base_de_donnees.md` | Modèles, migrations, schéma | `app/models/*.py`, `alembic/versions/*.py` |
| 8 — QA & Sécurité | `08_qa_securite.md` | Tests, audit, rate-limit | `tests/**/*.py`, `app/middleware/rate_limit.py`, security headers Nginx |
| 9 — DevOps | `09_devops.md` | Docker, Nginx, CI/CD, scripts | `Dockerfile`, `docker-compose*.yml`, `nginx/`, `github/workflows/`, `scripts/`, `.env.example` |

## Règles d'attribution

1. Si commit touche **uniquement un seul périmètre** → l'agent correspondant.
2. Si commit touche **plusieurs périmètres** → l'agent du périmètre majeur (au nombre de lignes), et lister les co-agents en note.
3. Si commit touche `docs/` uniquement → Agent 1 (sauf si la doc concerne directement un agent — ex. édition de `02_game_designer.md` → Agent 2).
4. Si commit modifie une formule d'équilibrage (`combat_engine`, `ship_stats`, etc.) → flagger pour Agent 2 ET Agent 5 (Game Designer = source de vérité, Backend = implémentation).
5. Si commit ajoute une migration Alembic ET met à jour des modèles SQLAlchemy → Agent 7 principal, Agent 5 secondaire.

## Exemples concrets

| Commit | Fichiers | Attribution |
|---|---|---|
| Ajout endpoint `/espionage/probe` | `app/routers/espionage.py`, `app/services/espionage_service.py`, `tests/routers/test_espionage.py` | Agent 5 (principal) + Agent 8 (tests) |
| Migration `0007_espionage_reports` | `alembic/versions/0007_*.py`, `app/models/espionage_models.py` | Agent 7 |
| Refonte palette rareté | `frontend/src/index.css`, `tailwind.config.js`, `frontend/UIUX_SPEC.md` | Agent 4 (principal) + Agent 6 (impl) |
| Configuration Uptime Kuma | `docker-compose.prod.yml`, `nginx/conf.d/monitoring.conf`, `docs/09_devops.md` | Agent 9 |
| Ajout test intégration alliances | `tests/routers/test_alliances.py` | Agent 8 |
| Fix bug arrondi ressources | `app/routers/planets.py` (ajout `math.floor`) | Agent 5 (impl) + Agent 8 (vecteur identifié) |
