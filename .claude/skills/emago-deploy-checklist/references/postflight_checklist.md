# Checklist post-déploiement Emago

À exécuter dans les 5 minutes suivant un déploiement.

## 1. Health endpoint

```bash
curl -sf https://YOUR_DOMAIN.COM/health
```

**Attendu** : status `200`, JSON avec `status: "ok"`, `version: "0.X.Y"`, `checks: { db: "ok", redis: "ok" }`.

**Si 503** : un des composants est dégradé. Détail dans `checks`. Investigate.

**Si pas de réponse** : Nginx ne répond pas → vérifier `docker compose ps` + DNS.

## 2. WebSocket smoke test

### Test rapide via curl
```bash
curl -i \
  -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" \
  -H "Sec-WebSocket-Version: 13" \
  https://YOUR_DOMAIN.COM/ws
```

**Attendu** : `HTTP/1.1 101 Switching Protocols` (avec un token, sinon close 4001).

**Si 426 Upgrade Required** : Nginx ne proxifie pas les headers Upgrade. Vérifier `nginx/conf.d/emago.conf` location /ws.

### Test fonctionnel via websocat
```bash
# Avec un token valide :
TOKEN=$(curl -s -X POST https://YOUR_DOMAIN.COM/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"smoke@test.com","password":"smoketest123"}' \
  | jq -r '.access_token')

websocat "wss://YOUR_DOMAIN.COM/ws?token=$TOKEN"
# Doit recevoir : {"type":"connected","data":{"player_id":"..."}}
```

## 3. Logs API

```bash
docker compose -f docker-compose.prod.yml logs --tail=100 -t api
```

**Vérifier** :
- Pas de stack trace fraîche.
- "Application startup complete" présent.
- "Scheduler started" présent.
- "Scheduler running" périodique (resource_tick, build_tick, etc.).

**Si erreurs** :
- "ConnectionError" sur Redis → Redis pas démarré.
- "OperationalError" SQLAlchemy → DB pas accessible ou migration manquante.
- "Token decode failed" → SECRET_KEY pas chargé ou changé entre 2 deployments (= invalide tous les access tokens).

## 4. Alembic current

```bash
docker compose exec api alembic current
```

**Attendu** : revision attendue (ex. `0007_espionage_reports (head)`).

**Si pas head** : exécuter `alembic upgrade head`.

## 5. Smoke tests utilisateur

Faire passer un joueur factice (ou un compte de test) à travers les flows critiques :

```
1. Login → access_token reçu
2. GET /ships → liste hangar (peut être vide pour nouveau compte)
3. GET /planets → homeworld créé automatiquement
4. POST /ships/build (frigate_attack) → 201, rareté tirée, base_stats présents
5. GET /ranking → top 100 retourné, status 200
6. WebSocket : connect avec token → "connected" reçu
```

**Si un de ces tests échoue** : rollback ou hotfix urgent.

## 6. Métriques Uptime Kuma

Si configuré : tous les monitors doivent passer ✅ vert :
- HTTP /health
- TCP db:5432 (interne)
- TCP redis:6379 (interne)
- WebSocket heartbeat (Phase 2)

## 7. Cron backup

```bash
crontab -l | grep backup_postgres
ls -lh /opt/emago/backups/ | tail -3
```

**Vérifier** : backup le plus récent < 25h. Si déploiement vient juste de se faire et que le cron n'a pas encore tourné → déclencher manuellement :
```bash
bash /opt/emago/scripts/backup_postgres.sh
```

## 8. Annonce post-deploy

Une fois tout vert :
- ☐ Annonce dans le canal interne ("Deploy v0.X.Y OK").
- ☐ Mise à jour `docs/01_chef_de_projet.md` si milestone.
- ☐ Tag Git : `git tag v0.X.Y && git push --tags`.

---

## Si quelque chose cloche

### Symptômes courants

| Symptôme | Cause probable | Action |
|---|---|---|
| /health 503 | DB ou Redis down | `docker compose logs db redis` |
| WS 426 | Nginx Upgrade headers manquants | Fix `emago.conf` + `restart nginx` |
| 500 sur tous endpoints | SECRET_KEY invalide | Vérifier `.env`, restart api |
| 404 sur /api/v1/* | Nginx mauvaise route | Fix `emago.conf` location /api/ |
| Migrations not applied | `alembic upgrade` pas exécuté | `docker compose exec api alembic upgrade head` |
| Slow queries | Index manquant ou dégradation | `EXPLAIN ANALYZE` ; voir Agent 7 |
| OOM api | Workers mal dimensionnés | Revoir `--workers 4` du Dockerfile selon CPU |
| Disk full | Logs ou backups non purgés | `du -sh /var/log/* /opt/emago/backups/*` |

### Rollback express

Si plus de 5 min de down :

```bash
# Option 1 : rollback image (plus rapide)
docker compose -f docker-compose.prod.yml pull api  # avec tag précédent
# Modifier .env ou docker-compose.prod.yml pour utiliser image:tag-precedent
docker compose -f docker-compose.prod.yml up -d --no-deps api

# Option 2 : rollback migration (si breaking change)
docker compose exec api alembic downgrade -1

# Option 3 : restauration backup (si data corruption)
gunzip /opt/emago/backups/emago_<DATE>.sql.gz
docker compose exec -T db psql -U emago -d emago < /opt/emago/backups/emago_<DATE>.sql
```

Cf. `references/rollback_paths.md` pour le détail.
