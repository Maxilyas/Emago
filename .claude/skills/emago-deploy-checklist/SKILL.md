---
name: emago-deploy-checklist
description: Génère et exécute la checklist de pré-déploiement Emago — DNS pointé, .env complet et sécurisé (DEBUG=false, SECRET_KEY 64-char hex, mots de passe forts), Docker + Compose disponibles, alembic upgrade head, /health 200, certbot SSL actif, WS proxifié (Upgrade headers Nginx), backup pg_dump quotidien programmé, cron renew certbot mensuel, GitHub Secrets configurés (VPS_HOST/USER/SSH_KEY/DEPLOY_DIR), tests passants en CI, image Docker buildable, healthcheck Docker répond. Adapté au stack Docker + Nginx + Certbot + GitHub Actions Emago. Use when l'utilisateur dit "deploy Emago", "checklist prod", "mise en prod", "vérif avant push main", "préparation déploiement", "release Emago", "ship to prod".
license: MIT
metadata:
  author: Antoine
  version: 1.0.0
  project: emago
  agent: 9-devops
---

# emago-deploy-checklist

Garantit qu'aucun déploiement Emago ne part en prod avec un risque évitable. Workflow orchestrant lecture config + tests + smoke checks pré et post-déploiement.

---

## Quand utiliser ce skill

- Avant **tout** déploiement prod (premier ou Nème).
- Après une refonte majeure (migration grosse, refonte stack, changement Nginx config).
- Avant un release tag (`v0.X.Y`).
- Pour vérifier qu'un environnement staging est prêt à recevoir des tests utilisateurs.

## Quand NE PAS utiliser ce skill

- Pour un hotfix urgent en cours de prod → utiliser `engineering:incident-response` à la place.
- Pour un dev local → pas nécessaire, `docker compose up` suffit.
- Pour un audit de sécurité approfondi → utiliser `engineering:security-review` ou `emago-attack-vector-audit`.

---

## Instructions

### Étape 1 — Identifier le contexte

Demande à l'utilisateur :
1. **Type de déploiement** : initial / mise à jour mineure / migration BDD majeure / hotfix ?
2. **Environnement cible** : staging / production ?
3. **Changements depuis le dernier déploiement** : nouvelles migrations Alembic ? Nouveau service Docker ? Modif Nginx ? Mise à jour deps ?
4. **Branche déployée** : `main` (default) ou autre ?

### Étape 2 — Lancer la checklist pré-déploiement

Exécute `references/preflight_checklist.md` section par section. Pour chaque item :

- ✅ OK : passer.
- ❌ KO : corriger avant de continuer.
- ⚠️ Warning : noter, peut être OK selon contexte.

Sections obligatoires :

1. **Repo & branche**
2. **Variables d'environnement** (`.env` prod)
3. **Migrations Alembic**
4. **Tests CI**
5. **Build Docker**
6. **Configuration Nginx**
7. **Certbot SSL**
8. **GitHub Secrets**
9. **Backup pg_dump**
10. **Monitoring & alerting**

### Étape 3 — Lancer le déploiement

Si tout est ✅, exécuter le déploiement. Trois options :

**A. CI/CD automatique (recommandé)**
```bash
git push origin main
# → GitHub Actions CI → CD → SSH VPS → docker compose pull / migrate / up
```

**B. Déploiement manuel SSH**
```bash
ssh user@vps
cd /opt/emago
git pull origin main
docker compose -f docker-compose.prod.yml pull api
docker compose -f docker-compose.prod.yml run --rm api /opt/venv/bin/alembic upgrade head
docker compose -f docker-compose.prod.yml up -d --no-deps api
```

**C. Déploiement initial complet**
```bash
ssh root@vps
bash /opt/emago/scripts/install_vps.sh
# Suit les étapes manuelles : .env, certbot, cron
```

### Étape 4 — Lancer la checklist post-déploiement

Cf. `references/postflight_checklist.md` :

1. **Health endpoint** répond 200 sur `/health` (pas 503).
2. **WebSocket** : tester un connect via curl + websocat ou client web (DevTools).
3. **Logs** : pas d'erreur fraîche dans `docker compose logs api`.
4. **Migration Alembic** appliquée (`alembic current` retourne le head attendu).
5. **Smoke tests utilisateur** : login, build ship, voir hangar.
6. **Métriques** : Uptime Kuma vert (si configuré).
7. **Cron backup** a tourné dans la dernière fenêtre attendue.

### Étape 5 — Annoncer le déploiement

Si tout est ✅ :
- Tag Git : `git tag v0.X.Y && git push --tags` (si milestone).
- Annonce dans le canal interne (Discord/Slack).
- Mise à jour `docs/01_chef_de_projet.md` section 7 (roadmap).

Si problème détecté :
- **Rollback immédiat** via `emago-rollback-runbook` ou méthode manuelle.

### Étape 6 — Mettre à jour `docs/09_devops.md`

Si la checklist a révélé un nouveau cas non documenté, l'ajouter à la section 11 du doc DevOps pour les prochains déploiements.

---

## Examples

### Exemple 1 — Déploiement initial

**User** : "Premier déploiement de Emago en prod, vérifie tout avant"

**Actions** :
1. Demande VPS IP, domaine.
2. Lance la checklist complète :
   - Génère SECRET_KEY si manquant.
   - Vérifie `.env.example` → guide la création de `.env`.
   - Vérifie DNS A record → `dig YOUR_DOMAIN.COM`.
   - Vérifie `install_vps.sh` exécuté sans erreur.
   - Vérifie certbot SSL actif via `curl -I https://YOUR_DOMAIN.COM`.
   - Vérifie WS via `websocat wss://YOUR_DOMAIN.COM/ws?token=invalid` doit retourner close 4001.
3. Sort un rapport "✅ Prêt pour déploiement" ou "❌ X items à corriger".

### Exemple 2 — Déploiement avec migration

**User** : "Push main avec migration 0007 (espionage_reports), vérifie que c'est safe"

**Actions** :
1. Vérifie test CI passent (`pytest`).
2. Charge la migration `0007`. Identifie : nouvelle table, pas de breaking change, downgrade fourni.
3. Vérifie qu'un backup récent existe : `ls -la /opt/backups/emago/ | head -5`.
4. Si backup > 24h → demande à le déclencher avant.
5. Note : "Migration ajoute table espionage_reports, downgrade testé OK, backup récent OK → GO".
6. Suggère post-deploy : tester `POST /espionage/probe` smoke test.

### Exemple 3 — Hotfix mineur

**User** : "Hotfix sur planets.py (math.floor manquant), je peux push direct ?"

**Actions** :
1. Reconnaît : pas de migration, pas de modif Docker/Nginx, juste 1 fichier Python.
2. Checklist allégée :
   - Tests passent en CI ? ✅
   - Le fix est-il couvert par un test régression ? Si non, fortement encouragé.
   - Pas de breaking API ? ✅
3. Verdict : "GO, mais ajoute `test_resources_floor_safety` avant ou juste après pour anti-régression".

---

## Troubleshooting

### `curl /health` retourne 503 après déploiement

**Cause** : DB ou Redis pas encore prêts (timing).
**Solution** : attendre 10-30s puis re-tester. Si persistant : `docker compose logs db redis`.

### Migration Alembic échoue avec erreur trigger

**Cause** : la migration tente de modifier `base_stats` sans bypass session var.
**Solution** : ajouter `SET LOCAL emago.bypass_stats_trigger = 'true'` au début de la migration. **Faire un backup avant de re-tenter.**

### WebSocket renvoie 426 Upgrade Required

**Cause** : Nginx n'a pas les headers `Upgrade` et `Connection "upgrade"` sur `/ws`.
**Solution** : vérifier `nginx/conf.d/emago.conf` location `/ws` :
```nginx
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
```
Puis `docker compose restart nginx`.

### CI passe mais déploiement échoue

**Cause** : différence d'env (variables manquantes en prod, version Python différente).
**Solution** : comparer Dockerfile avec versions Python CI. Vérifier `.env` complet (cf. checklist).

### `docker compose logs api` affiche "scheduler crashed"

**Cause** : APScheduler a crashé suite à exception non catchée.
**Solution** : redémarrer api uniquement (`docker compose up -d --no-deps api`). Investiguer avec `docker compose logs --tail=200 api`. Souvent dû à une migration manquante ou Redis indisponible au démarrage.

### Backup cron pas exécuté

**Cause** : cron pas configuré OU script pas exécutable.
**Solution** :
```bash
crontab -l | grep backup_postgres
chmod +x /opt/emago/scripts/backup_postgres.sh
# Tester en mode manuel :
bash /opt/emago/scripts/backup_postgres.sh
ls -lh /opt/emago/backups/
```

### Certbot renouvellement raté

**Cause** : DNS change ou port 80 bloqué.
**Solution** :
```bash
docker compose run --rm certbot renew --dry-run
# Si erreur DNS : vérifier que le record A pointe toujours sur le VPS
# Si erreur port 80 : vérifier le firewall + Nginx HTTP server actif
```

---

## References

- `references/preflight_checklist.md` — checklist complète pré-déploiement (15 items).
- `references/postflight_checklist.md` — checklist post-déploiement (7 items).
- `references/env_template.md` — variables `.env` requises avec exemples sécurisés.
- `references/rollback_paths.md` — résumé des 3 méthodes de rollback (image, migration, backup).

## Scripts

- `scripts/preflight.sh` — exécute automatiquement les checks faciles (DNS, ports, /health local, .env présence).
- `scripts/postdeploy.sh` — vérifie /health, WS, logs, alembic current.
- `scripts/check_secrets.sh` — vérifie qu'aucun secret n'a fuité dans le repo.
