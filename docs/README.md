# Emago — Documentation projet

> **Emago** — Jeu de stratégie spatiale multijoueur en temps réel par navigateur
>
> Stack : Python / FastAPI · React / TypeScript · PostgreSQL · Redis · Docker · Nginx
>
> Version : 0.1.0 (Mai 2026)

---

## Vue d'ensemble

Emago est un jeu de stratégie spatiale en temps réel, accessible via navigateur. Il conserve les mécaniques fondamentales d'OGame (gestion de ressources, bâtiments, recherches, colonisation, classements, alliances) et y ajoute un **système de vaisseaux RPG** différenciateur : chaque vaisseau est unique, possède des stats générées aléatoirement à la fabrication, un niveau de rareté, des modules installables, accumule de l'expérience en combat, peut hériter d'un Pedigree, gagner des cicatrices narratives, recevoir un trait procédural, et fusionner via la Forge.

**Philosophie :** fun, moderne, équitable — zéro pay-to-win.

---

## Organisation de cette documentation

Chaque agent du projet rédige sa propre section. Les docs sont structurées par responsabilité technique pour permettre à chaque agent de retrouver rapidement son périmètre.

### Documentation utilisateur (joueurs)

- [`00_guide_utilisateur.md`](./00_guide_utilisateur.md) — guide du joueur, lore, mécaniques de jeu, FAQ

### Documentation par agent

| Agent | Rôle | Doc |
|---|---|---|
| **Agent 1** | Chef de projet | [`01_chef_de_projet.md`](./01_chef_de_projet.md) |
| **Agent 2** | Game Designer | [`02_game_designer.md`](./02_game_designer.md) |
| **Agent 3** | Architecte système | [`03_architecte.md`](./03_architecte.md) |
| **Agent 4** | UI/UX Designer | [`04_uiux_designer.md`](./04_uiux_designer.md) |
| **Agent 5** | Dev Backend | [`05_dev_backend.md`](./05_dev_backend.md) |
| **Agent 6** | Dev Frontend | [`06_dev_frontend.md`](./06_dev_frontend.md) |
| **Agent 7** | Dev Base de données | [`07_base_de_donnees.md`](./07_base_de_donnees.md) |
| **Agent 8** | QA & Sécurité | [`08_qa_securite.md`](./08_qa_securite.md) |
| **Agent 9** | DevOps | [`09_devops.md`](./09_devops.md) |

### Documents transversaux

- [`10_ameliorations.md`](./10_ameliorations.md) — Roadmap des améliorations à prévoir (tous agents)

---

## État global du projet (1er mai 2026)

| Domaine | État | Commentaire |
|---|---|---|
| Modèles BDD | **FAIT** | 6 migrations Alembic appliquées (initial, scar_tags, daily_data, alliances, expedition_logs, RPG fields) |
| Services backend | **FAIT** | ship_build, ship_stats, combat_engine, forge, expedition, naming, ship_trait |
| Routers backend | **FAIT** | 14 routers (auth, ships, modules, forge, planets, fleets, combat, ranking, scars, galaxy, expeditions, tech, daily, alliances) |
| Tâches asynchrones | **FAIT** | resource_tick, build_tick, fleet_arrival, forge_tick, ranking, immunity_reset |
| WebSocket | **FAIT** | ConnectionManager + handler + subscribers Redis pub/sub |
| Tests backend | **PARTIEL** | Tests unitaires services + routers auth/ships/forge. Tests intégration alliances/combat à compléter |
| Frontend pages | **FAIT** | 14 pages implémentées (Login, Dashboard, Planet, Buildings, Hangar, ShipDetail, Forge, Galaxy, Tech, Expedition, Ranking, Alliances, Combats, CombatReport) |
| Frontend composants | **FAIT** | ShipCard, ResourceBar, ForgeProgress, CombatReport, GalaxyMap, BuildingCardUX, RarityReveal, SpectreAwakening, NotificationPanel, AppLayout |
| Docker dev | **FAIT** | docker-compose.yml |
| Docker prod | **FAIT** | Dockerfile multi-stage + docker-compose.prod.yml + Nginx + Certbot |
| CI/CD | **FAIT** | GitHub Actions (CI pytest+codecov, CD via SSH) |
| Backups & Monitoring | **PARTIEL** | Script `backup_postgres.sh` livré ; Uptime Kuma à configurer |
| Sécurité | **PARTIEL** | Vecteurs critiques traités (ownership, double-soumission Forge, immuabilité base_stats). Rate limit en place via slowapi. Tests d'intégration security à compléter |

Détails par agent dans les docs respectives.

---

## Stack technique — récapitulatif

```
┌────────────────────────────────────────────────────────────────┐
│  Internet (HTTPS 443)                                          │
│         │                                                      │
│  Nginx (SSL, WebSocket proxy, static files, gzip)              │
│         ├── /api/v1/*  →  FastAPI (Uvicorn 4 workers, :8000)   │
│         ├── /ws        →  FastAPI WebSocket                    │
│         └── /          →  React build (Vite)                   │
│                                                                │
│  Docker Compose (prod) :                                       │
│   - nginx                                                      │
│   - api  (FastAPI + APScheduler)                               │
│   - db   (PostgreSQL 16)                                       │
│   - cache (Redis 7)                                            │
│   - certbot (SSL Let's Encrypt)                                │
└────────────────────────────────────────────────────────────────┘
```

---

## Lecture conseillée

- **Nouveau dans le projet ?** Commence par [`01_chef_de_projet.md`](./01_chef_de_projet.md) puis [`00_guide_utilisateur.md`](./00_guide_utilisateur.md).
- **Tu codes le backend ?** [`05_dev_backend.md`](./05_dev_backend.md) + [`03_architecte.md`](./03_architecte.md) + [`07_base_de_donnees.md`](./07_base_de_donnees.md).
- **Tu codes le frontend ?** [`06_dev_frontend.md`](./06_dev_frontend.md) + [`04_uiux_designer.md`](./04_uiux_designer.md) + [`03_architecte.md`](./03_architecte.md) (section API/WS).
- **Tu déploies ?** [`09_devops.md`](./09_devops.md) + [`08_qa_securite.md`](./08_qa_securite.md).
- **Tu équilibres ?** [`02_game_designer.md`](./02_game_designer.md).
- **Tu cherches la prochaine étape ?** [`10_ameliorations.md`](./10_ameliorations.md).

---

*Document Emago v1.0 — Mai 2026*
