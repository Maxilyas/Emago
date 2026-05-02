# Skills Emago à construire — par agent

> Skills **spécifiques au projet Emago** à packager comme dossiers `SKILL.md` (cf. *The Complete Guide to Building Skills for Claude*). Ces skills embarquent la connaissance du projet (palette rareté, immuabilité `base_stats`, conventions FastAPI Emago, helpers `_get_owned_ship`, etc.) — **différents** des skills génériques du plugin `engineering` qui restent valables en complément.
>
> Convention de nommage : tous les skills sont préfixés `emago-*` (kebab-case). Les references/ contiennent des extraits de `docs/` du projet.

---

## 1. Vue d'ensemble — 25 skills priorisés

| # | Agent | Skill | Catégorie* | Priorité |
|---:|---|---|---|---|
| 1 | 1 | `emago-status-report` | 2 — Workflow | Haute |
| 2 | 1 | `emago-decision-log` | 1 — Doc | Moyenne |
| 3 | 1 | `emago-roadmap-update` | 1 — Doc | Moyenne |
| 4 | 2 | `emago-balance-simulator` | 2 — Workflow | Haute |
| 5 | 2 | `emago-gdd-writer` | 1 — Doc | Haute |
| 6 | 2 | `emago-formula-verifier` | 2 — Workflow | Moyenne |
| 7 | 3 | `emago-adr-writer` | 1 — Doc | Haute |
| 8 | 3 | `emago-api-contract-sync` | 2 — Workflow | Moyenne |
| 9 | 3 | `emago-ws-event-spec` | 1 — Doc | Moyenne |
| 10 | 4 | `emago-screen-spec` | 1 — Doc | Haute |
| 11 | 4 | `emago-component-spec` | 1 — Doc | Haute |
| 12 | 4 | `emago-design-system-validator` | 2 — Workflow | Moyenne |
| 13 | 5 | `emago-router-scaffold` | 1 — Doc/Code | Haute |
| 14 | 5 | `emago-service-pattern` | 1 — Doc/Code | Haute |
| 15 | 5 | `emago-test-integration-writer` | 1 — Doc/Code | Haute |
| 16 | 6 | `emago-page-scaffold` | 1 — Doc/Code | Haute |
| 17 | 6 | `emago-ws-handler-emago` | 1 — Doc/Code | Moyenne |
| 18 | 6 | `emago-component-react-emago` | 1 — Doc/Code | Moyenne |
| 19 | 7 | `emago-migration-alembic` | 1 — Doc/Code | Haute |
| 20 | 7 | `emago-redis-key-spec` | 1 — Doc | Moyenne |
| 21 | 7 | `emago-query-explain` | 2 — Workflow | Moyenne |
| 22 | 8 | `emago-attack-vector-audit` | 2 — Workflow | Haute |
| 23 | 8 | `emago-router-test-checklist` | 2 — Workflow | Haute |
| 24 | 9 | `emago-deploy-checklist` | 2 — Workflow | Haute |
| 25 | 9 | `emago-rollback-runbook` | 1 — Doc | Moyenne |

\* Catégories du guide Anthropic : 1 = Document & Asset Creation · 2 = Workflow Automation · 3 = MCP Enhancement.

---

## 2. Skills — détail par agent

### Agent 1 — Chef de projet

#### `emago-status-report` — Rapport d'avancement Emago hebdomadaire (Cat. 2)

**Description (frontmatter)** :
> Génère un rapport hebdomadaire d'avancement du projet Emago basé sur les `docs/` et l'activité Git. Use when l'utilisateur dit "fais le point Emago", "rapport hebdo", "où on en est", "standup Emago".

**Pattern** : Sequential workflow orchestration.

**Steps** :
1. Lire `docs/01_chef_de_projet.md` section roadmap + `docs/10_ameliorations.md`.
2. Inventorier les commits récents (`git log --since='7 days ago'`).
3. Croiser avec les TODO marqués "EN COURS" dans chaque doc agent.
4. Sortir un rapport markdown avec : sections par agent, FAIT/EN COURS/NEW BLOCKERS, prochaine semaine.

**Référence à embarquer** : `references/agent_responsibilities.md` (extrait de `docs/01_chef_de_projet.md` section 3).

---

#### `emago-decision-log` — Journal de décisions architecturales (Cat. 1)

**Description** :
> Crée ou met à jour une entrée dans le journal des décisions Emago (`docs/decisions/`). Use when "décision technique", "ADR", "on doit choisir entre", "tranche entre X et Y" sur un sujet Emago.

**Template embarqué** : ADR léger (Contexte / Options / Décision / Conséquences / Date / Agents concernés).

**Référence** : `references/decisions_ouvertes.md` (extrait section 8 de `01_chef_de_projet.md` + section 5 de `10_ameliorations.md`).

---

#### `emago-roadmap-update` — Mise à jour roadmap (Cat. 1)

**Description** :
> Met à jour `docs/10_ameliorations.md` quand une tâche change de statut ou qu'une nouvelle est ajoutée. Use when "ajoute à la roadmap", "marque comme fait", "déplace en Phase 2".

---

### Agent 2 — Game Designer

#### `emago-balance-simulator` — Simulateur d'équilibrage (Cat. 2)

**Description** :
> Lance des simulations de combat Emago à partir de compositions de flottes (classe + rareté + grade + modules) pour vérifier l'équilibrage. Use when "équilibrage Emago", "Légendaire vs Communs", "simule un combat", "vérifie balance".

**Pattern** : Iterative refinement.

**Scripts à embarquer** :
- `scripts/simulate_combat.py` — réimplémente la logique de `combat_engine.py` (synergies, XP différentielle, cap +150%) pour tourner 1000 combats et sortir winrate, rounds moyens, distribution XP.
- `scripts/rng_distribution.py` — tire 10 000 raretés via `secrets.SystemRandom()` et vérifie que la distribution colle aux thresholds (55/27/12/5/1).

**Référence** : `references/balance_constants.md` (extrait section 16 de `02_game_designer.md`).

---

#### `emago-gdd-writer` — Rédaction GDD Emago (Cat. 1)

**Description** :
> Rédige une nouvelle section du GDD Emago avec la structure standard : Mécanique / Formules / Cas limites / Notes pour les développeurs. Use when "écris le GDD de", "documente la mécanique", "GDD espionnage", "design d'alliance avancée".

**Template** :
```markdown
## [Mécanique]

### Mécanique
[Description claire]

### Formules / Valeurs
[Tableaux ou formules — toutes les constantes nommées]

### Cas limites
[Edge cases qui pourraient casser l'équilibre]

### Notes pour les développeurs
[Pour Agent 5/6/7 : champs BDD, services impactés, events WS]
```

**Référence** : `references/existing_gdd.md` (extrait sections 1-15 de `02_game_designer.md` comme exemple de structure).

---

#### `emago-formula-verifier` — Vérificateur formules code ↔ GDD (Cat. 2)

**Description** :
> Compare les formules implémentées dans le code Emago (combat_engine, ship_stats, ship_build, forge_service) avec celles documentées dans `docs/02_game_designer.md`. Use when "vérifie que le code respecte le GDD", "formule incohérente", "audit balance code".

**Pattern** : Iterative refinement avec validation.

**Vérifications embarquées** :
- XP différentielle : `× (1 + max(0, ratio - 1) × 2.5)` ?
- Cap stat : `base × 2.5` (+150 %) ?
- Forge XP transfer : `int(max × 0.30)` ?
- Drift probability : `0.05` ?
- Forge cost : `× 3` du build ?
- Bonus pedigree : `× 1.05` ?
- Affinity multiplier : `× 1.15` ?
- Module boosts : `[8, 14, 22, 32, 44]` ?

---

### Agent 3 — Architecte

#### `emago-adr-writer` — ADR avec contexte Emago (Cat. 1)

**Description** :
> Rédige un Architecture Decision Record (ADR) pour une décision technique sur le projet Emago, en respectant la stack et les contraintes existantes (FastAPI / SQLAlchemy 2.0 async / asyncpg / Redis / APScheduler / WebSocket). Use when "ADR Emago", "décision technique", "trade-off X vs Y", "Celery vs APScheduler", "scale-out".

**Template embarqué** :
```markdown
# ADR-XXX : [Titre]

**Date** : YYYY-MM-DD
**Statut** : Proposed / Accepted / Superseded by ADR-YYY
**Agents concernés** : Agent X, Y

## Contexte
[Situation actuelle Emago + contrainte qui force la décision]

## Options évaluées
1. [Option A] — pour / contre
2. [Option B] — pour / contre

## Décision
[Choix retenu]

## Conséquences
[Positives / négatives / risques]

## Cohérence avec existant
[Lien avec `docs/03_architecte.md` section 2 (décisions techniques)]
```

**Référence** : `references/architecture_decisions.md` (section 2 de `03_architecte.md`).

---

#### `emago-api-contract-sync` — Sync contrats API (Cat. 2)

**Description** :
> Vérifie la cohérence entre les routers FastAPI Emago, les schémas Pydantic, les types TypeScript frontend, et la documentation `docs/03_architecte.md` section 3. Use when "vérifie l'API Emago", "sync contrat", "le frontend match-il le backend".

**Pattern** : Multi-MCP coordination (lit code backend + frontend simultanément).

**Vérifications** :
- Tous les endpoints listés dans `03_architecte.md` existent-ils dans `app/routers/` ?
- Les types TS (`frontend/src/types/index.ts`) reflètent-ils les schémas Pydantic (`app/schemas/`) ?
- Tous les codes d'erreur (401/402/404/409/422) ont-ils un test pytest correspondant ?

---

#### `emago-ws-event-spec` — Spec d'un nouvel événement WebSocket (Cat. 1)

**Description** :
> Spécifie un nouvel event WebSocket Emago en respectant la convention canal `emago:events:player:{id}` + payload typé côté serveur ET côté frontend. Use when "ajoute un event WS", "nouvel event Emago", "espionnage event".

**Template** : event name, direction, déclencheur serveur, payload Python (Pydantic), payload TS (`@/types`), invalidation queries TanStack à déclencher côté client, handler dans `useWsEventHandlers`.

---

### Agent 4 — UI/UX Designer

#### `emago-screen-spec` — Spec d'écran complet (Cat. 1)

**Description** :
> Rédige une spec UI/UX pour un nouvel écran Emago en respectant la palette de rareté canon, le dark UI Mass Effect, et le design system du projet. Use when "spec écran Emago", "design page espionnage", "concevoir UI marché galactique".

**Template embarqué** :
```markdown
## Écran : [Nom]
**Route** : `/...`
**Layout général** : [Description]
**Composants** :
- `<NomComposant>` (props, role)
**États** : Normal / Chargement / Erreur / Vide
**API endpoints utilisés** : GET/POST/...
**Events WS écoutés** : [...]
**Interactions** : [hover / click / animations]
**Données affichées** : [...]
**Notes mobile-first** : breakpoints 375 / 768 / 1024
**Animations** : [`animate-fade-in`, `animate-slide-up`, etc.]
```

**Référence** : `references/design_system.md` (sections 1-12 de `04_uiux_designer.md` — palette, typo, animations, classes Tailwind).

---

#### `emago-component-spec` — Spec composant React Emago (Cat. 1)

**Description** :
> Génère la spec d'un composant React Emago : interface TypeScript des props, classes Tailwind respectant la palette rareté, animations cohérentes, dépendances stores/hooks. Use when "spec composant Emago", "ShipCard variant", "nouveau composant pour".

---

#### `emago-design-system-validator` — Validateur design system (Cat. 2)

**Description** :
> Vérifie qu'une proposition d'UI/page Emago respecte le design system : palette rareté canon (#9E9E9E/#4CAF50/#2196F3/#9C27B0/#FFD700), couleurs accent (`#2d7dd2`, `#7c3aed`, `#06b6d4`), typographie (Orbitron/Inter/JetBrains Mono), classes `.panel/.btn-primary/.input-field`, animations subtiles. Use when "valide design Emago", "respect palette", "audit UI".

---

### Agent 5 — Dev Backend

#### `emago-router-scaffold` — Scaffold router FastAPI Emago (Cat. 1)

**Description** :
> Génère un nouveau router FastAPI Emago en respectant les conventions du projet : `prefix="/...", tags=["..."]`, `CurrentPlayer + DbDep`, `_get_owned_ship` helper, codes d'erreur 401/402/404/409/422 en français, ordre des routes statiques avant paramétrées, transactions avec `with_for_update`, invalidation cache Redis, publish_event WS si pertinent. Use when "crée un router Emago", "scaffold endpoint", "ajoute /espionage", "ajoute /market".

**Pattern** : Sequential workflow avec template.

**Template de router embarqué** :
```python
"""
app/routers/<NAME>.py — <Description>
Agent 5 — Développeur Backend
"""
from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentPlayer, DbDep
from app.models.models import ...

router = APIRouter(prefix="/<name>", tags=["<name>"])


async def _get_owned_<resource>(<id>, player_id, db) -> ...:
    """Lève 404 si introuvable ou pas owner (anti-énumération)."""
    res = (await db.execute(select(...).where(...))).scalar_one_or_none()
    if not res or res.owner_id != player_id:
        raise HTTPException(status_code=404, detail="<Resource> introuvable.")
    return res


@router.get("")
async def list_resources(player: CurrentPlayer, db: DbDep) -> list[...]:
    """..."""
    ...


@router.post("", status_code=201)
async def create_resource(body: ..., player: CurrentPlayer, db: DbDep) -> ...:
    """..."""
    # SELECT FOR UPDATE si modif ressources
    # Vérification ownership
    # Action métier (déléguée au service)
    # publish_event WS si pertinent
    # invalidate Redis cache si pertinent
    ...
```

**Checklist embarquée** :
- [ ] Routes statiques avant paramétrées (cf. `/forge/history` avant `/forge/{id}`)
- [ ] Owner check via `_get_owned_*` → 404 (jamais 403 pour anti-énumération)
- [ ] `with_for_update` sur opérations qui mutent ressources
- [ ] Codes erreur en français
- [ ] Délégation logique métier au service (pas dans le router)
- [ ] `math.floor(float(...))` pour ressources (cf. fix bug arrondi)
- [ ] Invalidation Redis si mutation
- [ ] `publish_event(channel=f"player:{id}", ...)` si event utilisateur

**Référence** : `references/routers_patterns.md` (extraits de `app/routers/ships.py` + `forge.py` + `_summary_routers.md`).

---

#### `emago-service-pattern` — Service métier Emago (Cat. 1)

**Description** :
> Génère un service métier Emago avec les conventions : transactions ACID, `SELECT FOR UPDATE`, invalidation cache Redis, publish_event WS, RNG via `secrets.SystemRandom`, jamais de logique de jeu côté client. Use when "service métier Emago", "logique espionnage", "service marché".

**Référence** : `references/services_constants.md` (extrait de `_summary_services.md` — toutes les constantes critiques + formules).

---

#### `emago-test-integration-writer` — Tests d'intégration router (Cat. 1)

**Description** :
> Génère les tests pytest d'intégration pour un router Emago en utilisant les fixtures `auth_client / registered_player / planet_id / built_ship / other_player_ship_id` du `conftest.py`. Couvre systématiquement les vecteurs d'attaque (ownership 404, double-soumission, statut invalide). Use when "tests Emago pour", "test integration router", "couverture pytest".

**Checklist tests embarquée** :
- [ ] Test happy path (200/201)
- [ ] Test ownership cross-player → 404 (pas 403)
- [ ] Test ressources insuffisantes → 402
- [ ] Test conflit d'état → 409
- [ ] Test validation Pydantic → 422
- [ ] Test rate-limit → 429 si endpoint soumis (cf. `_LIMITS`)
- [ ] Test concurrence (double soumission simultanée)

**Référence** : `references/conftest_fixtures.md` (extrait de `tests/conftest.py`).

---

### Agent 6 — Dev Frontend

#### `emago-page-scaffold` — Scaffold page React Emago (Cat. 1)

**Description** :
> Génère une nouvelle page React/TypeScript Emago avec les patterns du projet : TanStack Query (refetch interval adapté), Zustand pour state global, `useGameSocket` events, classes Tailwind respectant le design system, layout via `AppLayout`. Use when "nouvelle page Emago", "scaffold /espionage", "page marché", "page profil joueur".

**Template embarqué** :
```tsx
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '@/stores/authStore';
import { api } from '@/lib/api';
import { LoadingSpinner, EmptyState } from '@/components/ui';
import toast from 'react-hot-toast';

export default function NomPage() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ['nom'],
    queryFn: () => api.get<...>('/nom'),
    refetchInterval: 30_000,  // ajuster
  });

  const mutation = useMutation({
    mutationFn: (body) => api.post<...>('/nom', body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['nom'] });
      toast.success('Action réussie');
    },
    onError: (err: any) => toast.error(err.detail ?? 'Erreur'),
  });

  if (isLoading) return <LoadingSpinner />;
  if (!data?.length) return <EmptyState ... />;

  return (
    <div className="animate-fade-in space-y-4">
      <header className="font-display uppercase tracking-wide">...</header>
      ...
    </div>
  );
}
```

**Référence** : `references/page_patterns.md` (extraits de `DashboardPage.tsx` + `HangarPage.tsx`).

---

#### `emago-ws-handler-emago` — Handler WebSocket Emago (Cat. 1)

**Description** :
> Génère le handler d'un nouvel event WS Emago côté frontend : ajout dans `useWsEventHandlers` (NotificationPanel), invalidation TanStack Query appropriée, toast / overlay / mise à jour `gameStore`. Use when "handler WS pour", "nouvel event combat", "frontend event espionnage".

**Pattern** : Sequential workflow.

---

#### `emago-component-react-emago` — Composant React Emago (Cat. 1)

**Description** :
> Génère un composant React respectant le design system Emago : palette rareté via `RARITY_CONFIG`, animations Tailwind, ShipCard-like glow, mobile-first. Use when "composant React Emago", "carte de", "panneau de", "tooltip Emago".

---

### Agent 7 — Dev Base de données

#### `emago-migration-alembic` — Migration Alembic Emago (Cat. 1)

**Description** :
> Génère une migration Alembic respectant les conventions Emago : enums PostgreSQL miroirs des Python, indexes partiels pour scheduler, trigger BEFORE UPDATE si immuabilité requise, FK avec cascade adapté, JSONB pour données extensibles, BigInt pour scores. Use when "migration Emago", "ajoute table", "alter ships", "nouveau enum BDD".

**Patterns à respecter (embarqués)** :
- ID primaire `UUID` avec `server_default=text("gen_random_uuid()")`.
- Index partiels pour scheduler : `WHERE is_completed = FALSE`.
- Trigger PG si champ immuable (cf. `prevent_base_stats_update_fn`).
- Bypass session var : `current_setting('emago.bypass_stats_trigger', true)`.
- Enum PG via `String` en colonne (pas `Enum`) pour faciliter l'évolution.
- FK circulaires (alliance↔player) via `use_alter=True`.

**Référence** : `references/migrations_patterns.md` (extrait de `0001_initial_schema.py` + `0006_ship_rpg_fields.py`).

---

#### `emago-redis-key-spec` — Spec d'une nouvelle clé Redis (Cat. 1)

**Description** :
> Documente une nouvelle clé Redis Emago avec les conventions : nom `<resource>:{id}:<aspect>`, TTL adapté, stratégie d'invalidation, channel pub/sub si pub-sub WS. Use when "nouvelle clé Redis", "ajoute cache pour", "stratégie cache Emago".

**Tableau référence embarqué** : section 6 de `03_architecte.md` (les 8 clés Redis existantes avec TTL).

---

#### `emago-query-explain` — Audit performance requête (Cat. 2)

**Description** :
> Lance EXPLAIN ANALYZE sur une requête SQL Emago + analyse les plans pour proposer des indexes manquants ou des optimisations (N+1, JSONB index). Use when "audit perf Emago", "requête lente", "EXPLAIN", "optim ranking".

**Pattern** : Iterative refinement (run, analyze, propose, re-run).

---

### Agent 8 — QA & Sécurité

#### `emago-attack-vector-audit` — Audit sécurité endpoint (Cat. 2)

**Description** :
> Audite un nouvel endpoint Emago contre les 25 vecteurs d'attaque connus (ownership masqué, double-soumission, race conditions, injection, énumération login, manipulation RNG, etc.) selon la checklist `docs/08_qa_securite.md`. Use when "audit sécurité Emago", "vecteur d'attaque", "review sécurité endpoint", "OWASP".

**Pattern** : Domain-specific intelligence.

**Checklist embarquée** :
- [ ] Ownership masqué : 404 et non 403 pour ressource d'autrui
- [ ] `with_for_update` sur opérations sensibles
- [ ] `_get_owned_*` helper utilisé
- [ ] `math.floor` sur ressources (anti bug arrondi)
- [ ] Rate limiting si endpoint sensible (`_LIMITS`)
- [ ] Anti-énumération login (même message pour email inconnu vs mauvais MDP)
- [ ] Trigger PG `prevent_base_stats_update` non bypassé
- [ ] WebSocket : channel `player:{id}` strict
- [ ] Headers HTTP (CORS strict prod, CSP, HSTS)

**Référence** : `references/attack_vectors_emago.md` (sections 2-3 de `08_qa_securite.md`).

---

#### `emago-router-test-checklist` — Checklist tests router (Cat. 2)

**Description** :
> Génère la checklist exhaustive de tests à écrire pour un router Emago donné, basée sur le tableau des gaps identifiés dans `docs/08_qa_securite.md` section 5. Use when "checklist tests router", "tests à écrire pour alliances", "couverture tests Emago".

---

### Agent 9 — DevOps

#### `emago-deploy-checklist` — Checklist déploiement Emago (Cat. 2)

**Description** :
> Génère et exécute la checklist de pré-déploiement Emago (DNS, .env, alembic upgrade head, /health, certbot, WS test, backup cron). Adaptée au stack Docker + Nginx + Certbot + GitHub Actions. Use when "deploy Emago", "checklist prod", "mise en prod", "vérif avant push main".

**Pattern** : Sequential workflow orchestration avec validation à chaque étape.

**Checklist embarquée** : section 11 de `09_devops.md` (15 items).

**Scripts** :
- `scripts/preflight.sh` — vérifie DNS, .env présence, ports, health endpoint local.
- `scripts/postdeploy.sh` — lance `curl /health`, test WS, vérifie logs.

**Référence** : `references/deploy_steps.md` (sections 6, 11, 12 de `09_devops.md`).

---

#### `emago-rollback-runbook` — Runbook rollback (Cat. 1)

**Description** :
> Génère ou consulte le runbook de rollback Emago selon le type d'incident : image foireuse, migration cassante, data corruption. Documente les commandes exactes et les délais. Use when "rollback Emago", "incident prod", "alembic downgrade", "restaurer backup".

**Référence** : section 10 de `09_devops.md` + script `backup_postgres.sh`.

---

## 3. Trois exemples complets de SKILL.md

### Exemple 1 — `emago-router-scaffold/SKILL.md`

```markdown
---
name: emago-router-scaffold
description: Génère un nouveau router FastAPI Emago en respectant les conventions du projet (CurrentPlayer + DbDep, _get_owned_ship helper, codes 401/402/404/409/422 en français, ordre routes statiques avant paramétrées, with_for_update sur mutations, invalidation cache Redis, publish_event WS). Use when l'utilisateur dit "crée un router Emago", "scaffold endpoint", "ajoute /espionage", "nouveau router pour le marché", ou demande à étendre le backend FastAPI Emago.
license: MIT
metadata:
  author: Antoine
  version: 1.0.0
  project: emago
---

# emago-router-scaffold

## Quand utiliser ce skill

Tu travailles sur le backend Emago (FastAPI) et tu dois ajouter un nouveau router (espionnage, marché galactique, profil détaillé, etc.). Ce skill produit un squelette qui respecte toutes les conventions du projet et évite les pièges connus.

## Prérequis

- Le repo Emago monté (backend/app/routers/ accessible).
- La doc `docs/05_dev_backend.md` et `docs/03_architecte.md` à disposition.

## Instructions

### Étape 1 — Cadrer le router

Pose à l'utilisateur :
1. Nom du router (kebab-case → utilisé pour le préfixe `/api/v1/<nom>`).
2. Liste des endpoints (méthode + path + description courte).
3. Schéma de données (table BDD existante ou nouvelle ?).
4. Y a-t-il un événement WebSocket à publier ?

### Étape 2 — Vérifier les conventions Emago

Toujours appliquer ces règles :

**Routes** :
- Routes statiques (`/history`, `/incoming`) AVANT routes paramétrées (`/{id}`) — sinon FastAPI tente de parser comme UUID → 422.

**Auth & deps** :
- `from app.core.deps import CurrentPlayer, DbDep`.
- Aucun endpoint sensible sans `player: CurrentPlayer`.

**Ownership** :
- Helper `_get_owned_<resource>(<id>, player_id, db)` qui lève 404 (PAS 403) si pas owner — anti-énumération.

**Codes d'erreur** :
- Tous en français : `"Vaisseau introuvable."`, `"Ressources insuffisantes..."`, `"Impossible de modifier un vaisseau en cours de forge."`.
- 401 : token absent/invalide. 402 : ressources insuffisantes. 403 : refus explicite (alliance role). 404 : introuvable OU ownership masqué. 409 : conflit d'état. 422 : validation Pydantic. 429 : rate-limit.

**Transactions** :
- Toute mutation ressources : `select(...).with_for_update()`.
- `math.floor(float(planet.metal))` pour comparer ressources (cf. fix bug arrondi 1999.87 vs 2000).
- Délégation logique métier au service correspondant (`app/services/*.py`).

**Cache & WebSocket** :
- `invalidate_ship_cache(ship_id)` après mutation ship.
- `invalidate_hangar_cache(player_id)` après build/demolish/forge.
- `publish_event(channel=f"player:{id}", event=...)` pour notifier le joueur (channel Redis pub/sub `emago:events:player:{id}`).

### Étape 3 — Générer le code

Utilise `references/router_template.py` comme base. Adapte au schéma exact de l'utilisateur.

### Étape 4 — Lister les tests à écrire

Toujours suggérer la liste des tests pytest correspondants (cf. `emago-test-integration-writer` ou `emago-router-test-checklist`).

### Étape 5 — Mettre à jour la doc

- `docs/05_dev_backend.md` section 4 (router list).
- `docs/03_architecte.md` section 3 (API contracts).

## Examples

**User** : "Crée un router Emago pour l'espionnage avec deux endpoints : POST /espionage/probe et GET /espionage/reports"

**Actions** :
1. Vérifie que la table `espionage_reports` existe (sinon : "Demande à Agent 7 une migration").
2. Génère `app/routers/espionage.py` avec helper `_get_owned_report`.
3. POST /probe : `with_for_update` sur deutérium + appel service.
4. GET /reports : ownership filtré WHERE owner_id = player.id.
5. WS : `publish_event(f"player:{id}", {"type": "espionage.report_ready"})` à la fin de la sonde.
6. Liste les 6 tests à écrire (happy, ownership 404, deut insuffisant 402, etc.).

## Troubleshooting

**Router renvoie 422 sur GET /endpoint/sub** :
Cause : `/sub` est captée comme UUID. Solution : déclarer la route statique AVANT la route paramétrée dans le fichier.

**Race condition observée sur création** :
Cause : pas de `with_for_update` sur la ressource mutée. Solution : ajouter le verrou pessimiste sur la planète/joueur.

**Frontend reçoit le mauvais event WS** :
Cause : channel pas formé `player:{id}` ou pub/sub non isolé. Solution : toujours `publish_event(channel=f"player:{owner_id}", ...)`.
```

---

### Exemple 2 — `emago-attack-vector-audit/SKILL.md`

```markdown
---
name: emago-attack-vector-audit
description: Audite un endpoint Emago (existant ou en cours de design) contre les 25 vecteurs d'attaque connus du projet — ownership masqué (404 vs 403), double-soumission Forge, race conditions, manipulation RNG, anti-énumération login, immuabilité base_stats, isolation WebSocket. Sortie un rapport markdown avec risques par criticité et corrections suggérées. Use when l'utilisateur dit "audit sécurité Emago", "vecteur d'attaque", "review endpoint", "OWASP Emago", "QA endpoint".
license: MIT
metadata:
  author: Antoine
  version: 1.0.0
  project: emago
---

# emago-attack-vector-audit

## Quand utiliser ce skill

Avant de merger un router/service Emago en production, ou pour auditer un endpoint existant. Couvre les vecteurs d'attaque spécifiques au projet documentés dans `docs/08_qa_securite.md`.

## Catégories de vecteurs

### Critiques (toujours bloquer le merge)
- C1 : ownership cross-player → doit retourner 404 (pas 403)
- C2 : double-soumission Forge / autre opération à ressources
- C3 : manipulation `base_stats` (le trigger PG doit empêcher)
- C4 : re-roll RNG (impossible — `secrets.SystemRandom` + trigger)
- C5 : token JWT expiré accepté
- C6 : injection XP en input

### Élevés
- E1 : vaisseau IN_FLEET envoyé en forge → 409
- E2 : WebSocket cross-player (channel `player:{id}` strict)
- E3 : énumération login (même message email inconnu vs mauvais MDP)
- E4 : participation `/combat/{id}` non vérifiée
- E5 : Pedigree avec parent d'autrui
- E6 : rate-limit absent sur endpoint sensible

### Moyens
- M1 : `with_for_update` manquant sur mutation
- M2 : `math.floor` manquant sur comparaison ressources
- M3 : N+1 queries
- M4 : index manquant pour requête fréquente

## Instructions

### Étape 1 — Lire le code

Lit le fichier `app/routers/<nom>.py` (et son service si applicable).

### Étape 2 — Appliquer la checklist

Pour chaque vecteur, marquer ✅ / ⚠️ EN COURS / ❌ MANQUANT.

### Étape 3 — Produire le rapport

Format :

\`\`\`markdown
## Audit sécurité — `<router>`

| # | Vecteur | Criticité | Statut | Détail |
|---:|---|---|---|---|
| C1 | Ownership 404 vs 403 | CRITIQUE | ✅ FAIT | Helper `_get_owned_ship` ligne 23 |
| ... | ... | ... | ... | ... |

### Risques bloquants
- (liste)

### Recommandations
1. ...

### Tests à ajouter
- ...
\`\`\`

## Examples

**User** : "Audit sécurité Emago sur le nouveau router /alliances"

**Actions** :
1. Lit `app/routers/alliances.py`.
2. Vérifie helper `_require_role` ✅.
3. Vérifie ownership `_get_member` ✅.
4. ⚠️ M1 : pas de `with_for_update` sur la création (race condition possible si 2 joueurs créent simultanément le même tag).
5. ⚠️ E6 : pas de rate-limit sur `POST /alliances/{id}/wars` (un leader peut spam déclarations de guerre).
6. Sort le rapport avec ces 2 issues + tests à ajouter.
```

---

### Exemple 3 — `emago-balance-simulator/SKILL.md`

```markdown
---
name: emago-balance-simulator
description: Simule des combats Emago, des distributions RNG de rareté, et des progressions XP/grade pour vérifier l'équilibrage du jeu. Reproduit fidèlement les formules de combat_engine.py (synergies de classe, XP différentielle × (1 + max(0, ratio-1) × 2.5), cap +150%, immunité Grade 4). Sort des stats agrégées sur N tirages : winrate, rounds moyens, distribution rareté. Use when l'utilisateur dit "équilibrage Emago", "Légendaire vs Communs", "simule un combat", "distribution rareté", "test balance", "RNG Emago".
license: MIT
metadata:
  author: Antoine
  version: 1.0.0
  project: emago
---

# emago-balance-simulator

## Quand utiliser ce skill

Avant de merger un changement d'équilibrage (modif de `_RARITY_THRESHOLDS`, `_RARITY_MULT`, formule XP, etc.), ou pour répondre à des questions de design comme "un Légendaire Grade 5 peut-il battre 50 Communs ?".

## Scripts disponibles

- `scripts/simulate_combat.py` — résout N combats entre 2 compositions de flotte. Reproduit synergies + XP différentielle + immunité Grade 4 + max 50 rounds.
- `scripts/rng_distribution.py` — tire 10 000 raretés via `secrets.SystemRandom()` et vérifie l'écart à la distribution théorique 55/27/12/5/1.
- `scripts/forge_progression.py` — simule N forges et calcule la probabilité d'obtenir un LEGENDARY au bout de K builds + forges.

## Constantes Emago à respecter (à jour, code de production)

| Constante | Valeur | Source |
|---|---|---|
| Cap stat | × 2.5 | `ship_stats_service._STAT_CAP_RATIO = 1.50` |
| Synergie ATTACK+SUPPORT | DPS × 1.20 | `combat_engine._compute_synergy_bonuses` |
| XP diff factor | `× (1 + max(0, ratio-1) × 2.5)` | `_compute_differential_xp` |
| Forge XP transfer | 30 % | `_XP_TRANSFER_RATIO = 0.30` |
| Drift | 5 % chance, stat × 0.80 | `_DRIFT_PROBABILITY = 0.05` |
| Affinity | × 1.15 | `_AFFINITY_MULT = 1.15` |

## Instructions

### Étape 1 — Définir le scénario

Demande à l'utilisateur :
1. Composition flotte attaquante (count + class + rarity + grade + modules).
2. Composition flotte défenseur.
3. Nombre d'itérations (défaut 1000).

### Étape 2 — Lancer la simulation

\`\`\`bash
python scripts/simulate_combat.py \\
  --attacker '<json>' \\
  --defender '<json>' \\
  --iterations 1000
\`\`\`

### Étape 3 — Interpréter

- Winrate dans [40-60] % → équilibre acceptable.
- Winrate ≥ 75 % → un côté domine, ajuster constantes.
- Rounds moyens ≥ 45 → combats trop longs, vérifier DPS.

### Étape 4 — Rapport

Sortir un markdown avec :
- Winrate attaquant/défenseur/draw
- Rounds moyens, écart-type
- XP moyenne par côté
- Cicatrices générées
- Recommandation : équilibré / déséquilibré / à creuser

## Examples

**User** : "Simule un Légendaire Grade 5 ATTACK avec 6 modules CANNON V vs 50 Communs Grade 0 ATTACK frigate_attack"

**Actions** :
1. Compose les flottes.
2. Run 1000 itérations.
3. Mesure winrate Légendaire (devrait être > 80 % mais pas 100 %).
4. Vérifie que le cap +150 % limite le DPS du Légendaire (cap_reached = ['dps']).
5. Conclut sur l'équilibre.

## Troubleshooting

**Le winrate est 100 % pour un côté** :
Probable cap stat non appliqué. Vérifier `_STAT_CAP_RATIO` dans le script vs code.

**Distribution RNG hors fourchette** :
Si COMMON tire à 70 % au lieu de 55 ± 5 %, le RNG est biaisé. Vérifier `secrets.SystemRandom()` (jamais `random.random()`).
```

---

## 4. Plan de construction (top 10 absolus)

Si tu construis ces skills dans cet ordre, tu maximises le ROI immédiat :

1. **`emago-router-scaffold`** (Agent 5) — économie énorme, accélère tout futur endpoint.
2. **`emago-attack-vector-audit`** (Agent 8) — bloque les régressions sécurité avant qu'elles arrivent en prod.
3. **`emago-balance-simulator`** (Agent 2) — confiance équilibrage avant chaque tweak GDD.
4. **`emago-deploy-checklist`** (Agent 9) — fait gagner du temps avant chaque déploiement.
5. **`emago-test-integration-writer`** (Agent 5) — rattrape les gaps `docs/08` section 5.
6. **`emago-page-scaffold`** (Agent 6) — accélère pages alliances/profil/espionnage.
7. **`emago-screen-spec`** (Agent 4) — design system embarqué garantit cohérence.
8. **`emago-status-report`** (Agent 1) — dashboard hebdo automatique.
9. **`emago-migration-alembic`** (Agent 7) — toutes les conventions BDD encapsulées.
10. **`emago-adr-writer`** (Agent 3) — historise les décisions Phase 2/3.

---

## 5. Composabilité & complémentarité avec le plugin engineering

Ces skills Emago **ne remplacent pas** les skills du plugin `engineering` — ils s'**empilent** :

| Tâche | Skill Emago + Skill engineering |
|---|---|
| Créer un router | `emago-router-scaffold` → puis `engineering:code-review` |
| Auditer un endpoint | `emago-attack-vector-audit` (spécifique) + `engineering:code-review` (général) |
| Avant déploiement | `emago-deploy-checklist` (Emago) + `engineering:deploy-checklist` (général) |
| Décision technique | `emago-adr-writer` (avec contexte Emago) ou `engineering:architecture` (générique) |
| Debug | `engineering:debug` est suffisant (pas besoin d'Emago-specific) |
| Postmortem incident | `engineering:incident-response` + `emago-rollback-runbook` |

Ne dupliquons pas ce que le plugin `engineering` fait déjà bien. Les skills Emago ajoutent **uniquement la couche projet-spécifique** (palette rareté, helpers FastAPI Emago, formules de jeu, conventions BDD).

---

## 6. Distribution

Suivant le guide chapitre 4 :

1. **Repo GitHub** `emago-skills` séparé (ou sous-dossier `skills/` dans le repo principal).
2. README au niveau du repo (pas dans chaque skill — uniquement `SKILL.md` + `references/` + `scripts/` + `assets/`).
3. Chaque skill dans son sous-dossier kebab-case (ex. `emago-router-scaffold/`).
4. Pour Claude Code : les skills sont chargeables localement dès qu'ils sont dans le dossier des skills utilisateur.
5. Pour Claude.ai : zip du dossier de skill, upload via Settings > Capabilities > Skills.
6. Si le projet a une organisation Anthropic (Team/Enterprise) : déploiement workspace-wide possible (depuis déc 2025).

---

## 7. Tests des skills (chapitre 3 du guide)

Pour chaque skill construit, valider 3 axes :

### 1. Triggering

Préparer 10 phrases qui DOIVENT déclencher le skill et 5 qui ne doivent PAS.

Exemple `emago-router-scaffold` :
- ✅ "Crée un router Emago pour l'espionnage"
- ✅ "Scaffold endpoint marché"
- ✅ "Ajoute /trade au backend"
- ❌ "Comment fonctionne FastAPI ?" (générique, pas Emago)
- ❌ "Tutoriel Python async" (hors scope)

### 2. Functional

Lancer le skill sur un cas réel et vérifier que la sortie respecte toutes les conventions Emago de la checklist.

### 3. Performance comparison

Mesurer combien de back-and-forth sont économisés vs ne pas avoir le skill. Sur `emago-router-scaffold` typique : passe de ~10 messages à ~2.

---

*Document Antoine — Skills Emago à construire — Mai 2026*
