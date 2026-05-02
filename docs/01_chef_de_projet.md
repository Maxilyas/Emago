# Agent 1 — Chef de projet

> Point d'entrée unique du projet. Vue d'ensemble, statut global, roadmap, décisions ouvertes, coordination inter-agents.

---

## 1. Concept du jeu

**Emago** est un jeu de stratégie spatiale multijoueur en temps réel jouable par navigateur. Inspiré d'OGame, modernisé visuellement (dark UI immersive — réf. Mass Effect plutôt que Clash of Clans) et différencié mécaniquement par un système de vaisseaux RPG inédit.

### Piliers du projet

1. **Fun et moderne.** Interface dark UI lisible, animations subtiles, palette par rareté omniprésente.
2. **Équitable.** Zéro pay-to-win. Le RNG vit côté serveur, immuable. Pas de re-roll, pas de boutique d'avantages.
3. **Narratif.** Chaque vaisseau est unique : nom procédural (RARE+), trait propre, cicatrices de combat, lignée Pedigree.
4. **Compétitif sain.** Classements, alliances, guerres alliances avec bonus XP, mais protections anti-farm via XP différentielle.

### Différenciateurs clés vs OGame

- Vaisseaux RPG (stats RNG immuables à la fabrication, classes ATTACK/DEFENSE/SUPPORT/EXPLORATION).
- 5 niveaux de rareté (COMMON 55 %, UNCOMMON 27 %, RARE 12 %, EPIC 5 %, LEGENDARY 1 %).
- Système d'amélioration triple : stats RNG + 6 familles de modules + 5 grades XP.
- Forge : fusion stratégique de 2 vaisseaux → rareté supérieure (8h, ×3 coût build, +30 % XP transférée). Avec 5 % de chance de **Dérive** (stat éligible × 0.80).
- Pedigree : héritage +5 % entre vaisseau Grade 3+ démoli et nouveau vaisseau du même type.
- Cicatrices : tags narratifs aléatoires sur survie difficile (≥75 % hull perdue ou enemy ≥2× plus puissant).
- ~200 traits procéduraux (8 familles thématiques, conditions SOLO/FLEET_3PLUS/CLASS_MATCH/ALWAYS).
- Missions de vaisseau (Grade 2+) renouvelées toutes les 72h.
- Expéditions autonomes 2h/6h/12h avec 12 events pondérés (déterministes via SHA-256).
- Daily login avec streak 7 jours et 3 missions quotidiennes.

---

## 2. Stack technique

| Couche | Technologie | Version | Rôle |
|---|---|---|---|
| Backend | Python + FastAPI | 3.12 / 0.115+ | API REST + WebSocket + logique de jeu |
| Frontend | React + TypeScript + Vite | 18 / 5 / latest | Interface utilisateur SPA |
| Style | Tailwind CSS | v3 | UI dark, responsive |
| État global | Zustand | v4 | Store client léger |
| Requêtes API | TanStack Query | v5 | Cache, refetch, invalidation |
| Base de données | PostgreSQL | 16 | Persistance principale |
| Cache / Temps réel | Redis | 7 | Cache stats, events WS, expéditions |
| ORM | SQLAlchemy | 2.0 async (asyncpg) | Modèles + requêtes async |
| Migrations | Alembic | latest | 6 migrations versionnées |
| Auth | JWT (python-jose) | — | Access 60min + refresh 30j |
| Scheduler | APScheduler | 3.x | 6 jobs (resource, build, fleet, forge, ranking, immunity) |
| Tests | pytest + httpx | — | conftest fixtures, tests services + routers |
| Déploiement | Docker + Compose | latest | dev + prod multi-stage |
| Reverse proxy | Nginx | latest | SSL, WS proxy, static files, gzip |
| CI/CD | GitHub Actions | — | CI pytest+codecov+ghcr, CD SSH appleboy |
| Monitoring | Uptime Kuma (cible) | — | /health endpoint |

---

## 3. Les 9 agents et leurs livrables

| Agent | Rôle | Livrables principaux |
|---|---|---|
| **1** | Chef de projet | Coordination, brief, roadmap, arbitrage |
| **2** | Game Designer | GDD systèmes vaisseaux/modules/forge/expedition/alliance, formules d'équilibrage |
| **3** | Architecte système | Architecture, schéma BDD, contrats API, événements WS, stratégie Redis |
| **4** | UI/UX Designer | Spec UI (`UIUX_SPEC.md`, `FRONTEND_SPEC.md`), palette rareté, écrans, composants |
| **5** | Dev Backend | Services métier, 14 routers FastAPI, 6 tâches APScheduler, WebSocket handler |
| **6** | Dev Frontend | 14 pages React, composants, stores Zustand, hooks WS, routing |
| **7** | Dev Base de données | 6 migrations Alembic, modèles SQLAlchemy 2.0, trigger immuabilité base_stats, indexes, stratégie Redis |
| **8** | QA & Sécurité | Tests pytest (unitaires + intégration), audit OWASP, vecteurs d'attaque, anti-triche |
| **9** | DevOps | Dockerfile multi-stage, docker-compose dev+prod, Nginx, CI/CD GitHub Actions, scripts VPS, backup pg_dump |

### Protocole de handoff

Les livrables inter-agents respectent le format :
```
HANDOFF EMAGO
De : Agent X — [Nom]
À : Agent Y — [Nom]
Sujet : [Titre]
Date : [Date]

### Contexte reçu
### Décisions prises
### Livrable
### Ce que l'agent destinataire doit savoir
### Prochaine étape suggérée
```

---

## 4. Fonctionnement global du projet

### Flow utilisateur type

```
1. Inscription / Login (JWT 60min + refresh 30j)
       ↓
2. Dashboard : ressources live, flotte active, forge en cours, daily missions
       ↓
3. Planète natale : produit métal/cristal/deutérium en continu (resource_tick 60s)
       ↓
4. Construction de bâtiments (build_tick 10s) : chantier naval, mine, labo
       ↓
5. Recherche de technologies (POST /tech/research → bonus permanents par classe)
       ↓
6. Construction de vaisseaux (POST /ships/build) : RNG rareté → base_stats immuables
       ↓
7. Installation de modules (PUT /ships/{id}/modules/{slot}) : cap +150 %
       ↓
8. Combat (envoi flotte → fleet_arrival 5s → combat_engine résout) :
       - XP différentielle, cicatrices, montées de grade, immunité Grade 4
       - WS combat.result + ship.grade_up + ship.scar_earned
       ↓
9. Forge (8h, fusion 2 vaisseaux même type/rareté → rareté supérieure, 5% Dérive)
       ↓
10. Expéditions (2h/6h/12h, autonomes, 12 events pondérés)
       ↓
11. Alliances (création 10k métal + 5k cristal + score ≥500, max 20 membres, guerre 48h min)
       ↓
12. Classement global (ranking job 10min)
```

### Boucle de progression

- Court terme (par session) : daily login, missions quotidiennes, expéditions courtes, combats locaux.
- Moyen terme (par jour) : montée en grade des vaisseaux, lancement de forges, recherches.
- Long terme (par semaine) : Pedigree de Grade 3+, vaisseaux Légendaires, classements, alliances.

---

## 5. Architecture en bref (détails dans 03_architecte.md)

```
                       ┌────────────────────┐
                       │   React Client     │
                       └─────────┬──────────┘
                                 │ REST + WS
                       ┌─────────▼──────────┐
                       │   Nginx (proxy)    │
                       └─────────┬──────────┘
                                 │
                ┌────────────────▼─────────────────┐
                │   FastAPI (Uvicorn x4 workers)   │
                │   - 14 routers REST              │
                │   - WebSocket /ws                │
                │   - APScheduler (6 jobs async)   │
                └────────┬────────────────┬────────┘
                         │                │
                  ┌──────▼─────┐   ┌──────▼──────┐
                  │ PostgreSQL │   │ Redis 7     │
                  │ 16         │   │ - Cache     │
                  │ - 13 tables│   │ - Pub/sub WS│
                  │ - Trigger  │   │ - Expé/forge│
                  └────────────┘   └─────────────┘
```

---

## 6. Décisions techniques majeures

| Décision | Choix | Alternative écartée | Raison |
|---|---|---|---|
| RNG | `secrets.SystemRandom()` | `random.random()` | Non prédictible, anti-triche |
| `current_stats` stockage | Redis cache TTL 300s + recalcul à la volée | Colonne JSONB en BDD | Évite désynchronisation après modules/grade |
| Immuabilité base_stats | Trigger PostgreSQL BEFORE UPDATE | Validation applicative seule | Garantie BDD imparable |
| Scheduler | APScheduler intégré FastAPI | Celery + broker | Sur-ingénierie pour <1000 joueurs |
| WS isolation | `player:{id}` channel via Redis pub/sub | Connection list mémoire pure | Permet scale horizontal futur |
| Forge fallback | Polling REST si WS coupé | WS unique | Robustesse réseau |
| Expéditions storage | Redis (TTL 48h) + index `player_expeditions:{pid}` | Dict en mémoire (v1) | Survit au redémarrage Uvicorn |
| Combat outcome | Suppression définitive ships détruits | Archivage | Simplifie + crée du poids tactique |
| Combat replay | Seed `random.Random(seed)` dans rounds | Pure SystemRandom | Auditable et rejouable |
| Auth | JWT HS256 + refresh rotation | Sessions stateful | Stateless, scale facile |

---

## 7. Roadmap — état actuel

### Sprint 1 — Infrastructure prod ✅ FAIT
- Dockerfile multi-stage non-root user
- docker-compose.prod.yml (Nginx + Certbot + api + db + cache)
- nginx.conf complet (SSL, WS proxy, gzip, HSTS, CSP)
- GitHub Actions CI (pytest + codecov + ghcr)
- GitHub Actions CD (SSH appleboy → docker compose pull/up)
- Script `install_vps.sh` + `backup_postgres.sh`
- Endpoint `/health` (DB + Redis check, 503 si dégradé)

### Sprint 2 — Sécurité & qualité ✅ MAJORITAIREMENT FAIT
- Rate limiting (slowapi sliding window)
- Vérification participation `/combat/{id}` (helper `_is_participant`)
- Subscribers WebSocket sécurisés (channel `player:{id}` strict via Redis pub/sub)
- Tests intégration `tests/routers/test_auth.py`, `test_ships.py`, `test_forge.py`
- Tests services `test_ship_services.py` (47 assertions sur RNG/stats/combat/forge)

### Sprint 3 — Frontend complet ✅ FAIT
- Page Combat Report (`CombatReportPage.tsx`)
- Composant `GalaxyMap.tsx` interactif
- Intégration WS complète (invalidation queries TanStack)
- Notification Panel WS connecté
- Animations spéciales : `RarityReveal` (build), `SpectreAwakening` (Grade 5)

### Sprint 4 — Alliances ✅ FAIT
- Migration 0004 (alliance_members, alliance_wars, enums AllianceRole/WarStatus)
- Routers `alliances.py` (8 endpoints)
- WS `alliance.war_declared`
- Page `AlliancesPage.tsx`
- GDD complet `GDD_ALLIANCES.md`

### Phase 2 — En attente

Voir [10_ameliorations.md](./10_ameliorations.md) pour la liste détaillée. Points saillants :

- **Espionnage** (sondes, contre-espionnage, niveau de détection)
- **Marché galactique** (échange ressources joueurs)
- **Colonisation avancée** (conditions, MAX planètes)
- **Tutoriel narratif premier joueur**
- **Système anti-farm complet**
- **Module inventory player** (table dédiée, drop expé persisté)
- **Audit performance Postgres** (EXPLAIN ANALYZE indexation)
- **Scale-out à 500+ joueurs** (multi-VPS api/db séparés)

---

## 8. Questions ouvertes à arbitrer

| Question | Urgence | Agents concernés |
|---|---|---|
| Limite MAX vaisseaux par hangar | Moyenne | Agent 2 → Agent 7 |
| Saisons / univers permanent / reset | Basse | Agent 1 + Agent 2 |
| Stratégie de monétisation (cosmétique uniquement) | Basse | Agent 1 |
| Tutoriel/onboarding premier joueur | Haute | Agent 4 + Agent 6 |
| Système d'espionnage (résultats, contre-espionnage) | Moyenne | Agent 2 + Agent 5 |
| Anti-farm : protection joueurs inactifs/débutants | Haute | Agent 2 + Agent 8 |
| Mécaniques d'alliance avancées (diplomatie, sous-guildes) | Basse | Agent 2 + Agent 3 |
| Purge combat_logs anciens (archivage S3 ou DELETE >30j) | Basse | Agent 7 + Agent 9 |
| Celery vs APScheduler à >1000 joueurs | Basse | Agent 3 + Agent 9 |
| WebSocket horizontal (sticky sessions ip_hash) | Basse | Agent 3 + Agent 9 |

---

## 9. Tableau de bord global des tâches

| Agent | Rôle | FAIT | EN COURS | À FAIRE |
|---|---|---|---|---|
| 1 | Chef de projet | 7 | 1 | 5 |
| 2 | Game Designer | 13 | 1 | 8 |
| 3 | Architecte | 9 | 1 | 5 |
| 4 | UI/UX Designer | 12 | 1 | 4 |
| 5 | Dev Backend | 16 | 2 | 8 |
| 6 | Dev Frontend | 14 | 1 | 8 |
| 7 | Dev BDD | 7 | 1 | 4 |
| 8 | QA & Sécurité | 12 | 1 | 9 |
| 9 | DevOps | 11 | 1 | 4 |

Détails dans chaque doc agent dédiée + [`10_ameliorations.md`](./10_ameliorations.md).

---

## 10. Coordination & rituels

- **Standup hebdomadaire (Agent 1)** : `/engineering:standup` — synthèse de la semaine inter-agents.
- **Revue mensuelle d'architecture (Agent 1 + Agent 3)** : audit dette technique, ajustement roadmap.
- **Audit sécurité trimestriel (Agent 1 + Agent 8)** : OWASP checklist, audit headers HTTP, replay tests combat.
- **Préparation pré-déploiement (Agent 1 + Agent 9)** : `/engineering:deploy-checklist` avant tout push prod.

---

*Document Agent 1 — Mai 2026*
