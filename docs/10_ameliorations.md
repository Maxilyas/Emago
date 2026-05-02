# Améliorations à prévoir — Roadmap consolidée

> Vue agrégée de toutes les tâches "À FAIRE / EN COURS" mentionnées dans les docs des 9 agents. Triées par priorité et par sprint.

---

## 1. Sprint Phase 2A — Sécurité & robustesse (Priorité Haute)

### Backend

- [ ] **Migrer `_active_research` (mémoire dans `tech.py`) en BDD** — `research_queue` table dédiée. Actuellement perdu au redémarrage Uvicorn.
- [ ] **Ajouter `with_for_update`** aux opérations sensibles : `expeditions/launch`, `tech/start_research`, `alliances/create_alliance`, `daily/claim_daily_login`.
- [ ] **Tests d'intégration manquants** : alliances (8 tests), fleets (4 tests), combat (3 tests), expeditions (4 tests), tech (3 tests), planets (5 tests), scars (3 tests), daily (2 tests).
- [ ] **Tests d'intégration WebSocket** : auth (4001/4004), isolation cross-player, reconnexion auto, message JSON malformé.
- [ ] **Heartbeat WebSocket serveur-side** : timeout détection des connexions zombies.
- [ ] **Optim ranking job** : N+1 queries actuelles → batch SELECTs avec JOIN.
- [ ] **Rate limit slowapi** sur `/auth/register`, `/auth/login` plus strict.

### Sécurité

- [ ] **Audit OWASP A05** (Configuration) — CSP plus stricte (suppression `unsafe-inline`).
- [ ] **`pip-audit`** + **`npm audit`** automatisés en CI.
- [ ] **Audit OWASP A06** (Vulnerable Components) trimestriel.
- [ ] **Tests de charge** (locust ou k6) sur endpoints critiques (`/ships/build`, `/forge`, `/fleets`).
- [ ] **Replay combat déterminisme** : test que même seed → mêmes rounds.
- [ ] **Test équilibrage** Légendaire Grade 5 vs 50 Communs Grade 0.

### DevOps

- [ ] **Configurer Uptime Kuma** (`louislam/uptime-kuma:1`, port 3001) avec monitors HTTP `/health`, TCP db/redis, WS heartbeat.
- [ ] **Notifications Discord/Slack** en cas de fail CD ou alerte Uptime Kuma.
- [ ] **Tester procédure de rollback** complet en staging (rollback image + rollback migration + restauration backup).
- [ ] **Documentation runbook incidents** : DB down, Redis down, OOM, disk full.

---

## 2. Sprint Phase 2B — Mécaniques de jeu

### Game design (Agent 2)

- [ ] **Espionnage** : sondes, niveau de détection, contre-espionnage, rapport (Phase 2 GDD complet).
- [ ] **Colonisation** : conditions, MAX planètes par joueur, initialisation ressources.
- [ ] **Anti-farm complet** : protections joueurs débutants/inactifs, ratio pillage max.
- [ ] **Tutoriel narratif** premier joueur (onboarding guidé, story-driven).
- [ ] **Limites de hangar** : MAX vaisseaux par joueur ou par planète.
- [ ] **Marché galactique** : échange de ressources entre joueurs.

### Backend

- [ ] **Routers espionnage** (Phase 2 GDD) — endpoints `/espionage/*`.
- [ ] **Service espionnage** : calcul résultats sonde selon tech niveau, contre-espionnage.
- [ ] **Routers colonisation** : conditions, MAX planètes, init.
- [ ] **Routers marché galactique** : offres d'achat/vente entre joueurs.
- [ ] **Implémenter ESPIONAGE** dans `fleet_arrival.py` (actuellement stub `is_recalled = True`).
- [ ] **Implémenter COLONIZE** dans `fleet_arrival.py` (création planète à coordonnées).
- [ ] **Module inventory player** : table `player_module_inventory` pour persister les drops d'expédition.
- [ ] **Implémenter `hull_damage` / `module_damage` flags expédition** dans `expedition_service.py`.
- [ ] **Pool `EXPEDITION_SCAR_TAGS`** : remplacer `tag_id = 1` hardcodé par lookup réel via `EXPEDITION_SCAR_TAGS`.

### Frontend

- [ ] **Page Profil joueur** : stats globales, historique combats, alliance, vaisseaux les plus glorieux.
- [ ] **Pages Phase 2** : espionnage, marché galactique.
- [ ] **Flow onboarding / tutoriel** premier joueur (interactif, story-driven).
- [ ] **Affichage Pedigree** dans `ShipDetailPage` (mention parent + lignée généalogique).
- [ ] **Tooltip narratif** sur cicatrices au survol.
- [ ] **Tests Vitest + RTL** : Hangar, Forge, ShipDetail, Combat (priorité haute).
- [ ] **Wrappers API manquants** : `tech.ts`, `daily.ts`, `scars.ts`, `missions.ts`.
- [ ] **Optim re-renders** `ResourceBar` (memo, useCallback).

### UI/UX

- [ ] **Concevoir écrans Profil joueur**.
- [ ] **Améliorer NotificationPanel** : groupement par type, priorités, sticky pour critiques.
- [ ] **Animations de combat** plus poussées : rounds animés, vaisseaux qui explosent.
- [ ] **Skins de vaisseaux** : système cosmétiques pour missions complétées (Phase 2).

---

## 3. Sprint Phase 2C — Performance & scalabilité

### Base de données (Agent 7)

- [ ] **Index JSONB** sur `combat_logs.attacker_ships_snapshot` pour participation combat (`combat.py:107`).
- [ ] **EXPLAIN ANALYZE** : `fleet_arrival`, `resource_tick`, hangar query, ranking, alliance score.
- [ ] **Compléter `scar_tags`** jusqu'à ~500 entrées (actuellement ~30 dans le seed migration 0002).
- [ ] **Procédure de purge** `combat_logs > 30 jours` (DELETE ou archivage S3).
- [ ] **Partitionnement `combat_logs`** par mois si volume > 1 M lignes.
- [ ] **Migration Redis → BDD pour expéditions** si besoin de persistance long terme (table `expedition_logs` déjà créée par migration 0005).
- [ ] **Vérification `BYPASS_STATS_TRIGGER`** en context Alembic — tester en CI.
- [ ] **Audit FK orphelines** : planets owner_id NULL si player supprimé.

### Architecture (Agent 3)

- [ ] **Spec endpoints Phase 2** : alliances avancées, espionnage, marché.
- [ ] **Charger `alliance_tag`** dans ranking (`ranking.py:53`).
- [ ] **WebSocket horizontal** : sticky sessions Nginx `ip_hash` ou activation Redis pub/sub strict.
- [ ] **Stratégie multi-VPS** (api + db séparés) à 500+ joueurs.
- [ ] **Celery + Redis broker** à 1000+ joueurs (au lieu d'APScheduler).

### DevOps (Agent 9)

- [ ] **Migration Caddy v2** (alternative à Nginx + Certbot) — option plus simple.
- [ ] **Logs centralisés** : Loki + Grafana, ou Papertrail.
- [ ] **Métriques Prometheus + Grafana**.
- [ ] **Audit trimestriel** des security headers (`securityheaders.com`).
- [ ] **Tests de charge automatisés** en staging.
- [ ] **Stratégie sticky sessions WS** via `ip_hash` Nginx.

---

## 4. Sprint Phase 3 — Croissance

### Mécaniques

- [ ] **Univers / saisons** : permanent vs reset 3 mois (décision Agent 1).
- [ ] **Cosmétiques** : skins de vaisseaux pour missions complétées, boutique cosmétique (jamais P2W).
- [ ] **Événements serveur** : invasions, tournois, classements hebdomadaires.
- [ ] **Système de guildes intra-alliance** (sous-groupes de combat).
- [ ] **Mécaniques alliance avancées** : diplomatie (PNA), chat alliance, ambassades.
- [ ] **Missions globales** serveur : invasions extérieures coopératives.
- [ ] **Phase 2 alliances dual-leader paix** : exiger l'accord des 2 leaders.

### Frontend

- [ ] **Page profil détaillé alliance** (Phase 2).
- [ ] **Heartbeat handling** (timeout reconnect plus agressif).
- [ ] **Animations skins / cosmétiques**.
- [ ] **Extraction helper commun** `hexToRgb` dans `lib/utils.ts` (actuellement dupliqué).

### Infrastructure

- [ ] **Tableau de bord admin** : monitoring joueurs, anti-triche, bans.
- [ ] **Honeypot endpoint** pour détecter scans automatisés.
- [ ] **Anti-bot** (CAPTCHA optionnel) sur register en cas d'abus détecté.
- [ ] **Migration vers PgBouncer** si > 500 joueurs simultanés (transaction pooling).
- [ ] **Sharding** stratégie pour > 10 000 joueurs.

---

## 5. Décisions techniques encore ouvertes

| Décision | Options | Agent responsable | Urgence |
|---|---|---|---|
| Limite MAX vaisseaux par hangar | 50 / 100 / illimité avec coût | Agent 2 → Agent 7 | Moyenne |
| Saisons / univers permanent / reset | Permanent / Saisons 3 mois | Agent 1 + Agent 2 | Basse |
| Stratégie monétisation (cosmétique uniquement) | Boutique cosmétiques / sans monétisation | Agent 1 | Basse |
| Tutoriel/onboarding premier joueur | Story-driven / quickstart / les deux | Agent 4 + Agent 6 | Haute |
| Système d'espionnage (résultats, contre-espionnage) | Plusieurs designs possibles | Agent 2 + Agent 5 | Moyenne |
| Anti-farm (protection joueurs inactifs/débutants) | Protection X jours / score-based | Agent 2 + Agent 8 | Haute |
| Mécaniques d'alliance avancées (diplomatie, sous-guildes) | À designer | Agent 2 + Agent 3 | Basse |
| Purge combat_logs anciens | Archive S3 / DELETE > 30j | Agent 7 + Agent 9 | Basse |
| Celery vs APScheduler à > 1 000 joueurs | À benchmark | Agent 3 + Agent 9 | Basse |
| WebSocket horizontal (sticky sessions) | Nginx ip_hash / Redis pub/sub | Agent 3 + Agent 9 | Basse |
| Stockage skins cosmétiques | URL fichiers statiques / JSONB | Agent 3 + Agent 7 | Basse |
| Limite scope CSP | Tightening progressif | Agent 8 + Agent 9 | Moyenne |

---

## 6. Tableau récapitulatif par agent

| Agent | À FAIRE Haute | À FAIRE Moyenne | À FAIRE Basse |
|---|---:|---:|---:|
| Agent 1 — Chef de projet | 2 | 2 | 1 |
| Agent 2 — Game Designer | 5 | 4 | 3 |
| Agent 3 — Architecte | 3 | 3 | 4 |
| Agent 4 — UI/UX | 2 | 4 | 3 |
| Agent 5 — Backend | 6 | 5 | 2 |
| Agent 6 — Frontend | 4 | 5 | 4 |
| Agent 7 — Base de données | 2 | 3 | 4 |
| Agent 8 — QA & Sécurité | 6 | 4 | 2 |
| Agent 9 — DevOps | 4 | 4 | 5 |
| **TOTAL** | **34** | **34** | **28** |

Total : ~96 améliorations identifiées.

---

## 7. Ordre d'exécution recommandé (top 10 priorités absolues)

1. **Tests d'intégration alliances + fleets + combat** (Agent 8) — fondation pour les futures mécaniques.
2. **Migration `_active_research` mémoire → BDD** (Agent 5) — bug critique au redémarrage.
3. **`with_for_update` sur expeditions/launch + tech/research + alliances/create + daily/login** (Agent 5) — race conditions.
4. **`pip-audit` + `npm audit` automatisés CI** (Agent 8/9) — sécurité dépendances.
5. **Configurer Uptime Kuma + alertes Discord** (Agent 9) — observabilité prod.
6. **Heartbeat WebSocket server-side** (Agent 5) — robustesse connexions longues.
7. **Tests de charge initiaux** (Agent 8) — comprendre la limite actuelle avant scale.
8. **Index JSONB combat participation** (Agent 7) — perf query history.
9. **Espionnage GDD + impl** (Agent 2 → 5 → 6) — mécanique manquante très demandée.
10. **Tutoriel onboarding** (Agent 4 → 6) — rétention nouveaux joueurs.

---

## 8. Backlog Phase 4+ (long terme)

- Multi-langue (EN, ES, DE, JP) avec i18next.
- Mode "ironman" / hardcore (vaisseaux détruits = perte permanente, déjà partiellement implémenté).
- Marché PvP des modules avec enchères.
- Intelligence artificielle (NPCs pirates qui attaquent automatiquement).
- Saisons compétitives avec récompenses cosmétiques exclusives.
- Mode coop : alliances qui partagent des bâtiments mutualisés.
- Replay des combats légendaires (rejoués via le seed sauvegardé).
- API publique pour widgets externes (classement, statut alliance).
- App mobile native (React Native / Capacitor).

---

*Document Agent 1 — Synthèse roadmap — Mai 2026*
