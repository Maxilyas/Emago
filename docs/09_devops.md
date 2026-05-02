# Agent 9 — DevOps

> Déploiement, conteneurisation, CI/CD, monitoring, backups, scripts VPS. Tout ce qu'il faut pour mettre Emago en production.

---

## 1. Architecture de déploiement cible

```
Internet (HTTPS 443 / HTTP 80 redirect)
    │
  Nginx (alpine, image volatile, conf montée RO)
    ├── /api/v1/*          →  api:8000          (FastAPI Uvicorn 4 workers)
    ├── /ws                →  api:8000          (WebSocket — Upgrade headers obligatoires)
    └── /                  →  React build (volumé /usr/share/nginx/html)

Docker Compose prod (`docker-compose.prod.yml`) :
  ├── nginx     — reverse proxy SSL + WS proxy + static React
  ├── api       — FastAPI + APScheduler (4 workers Uvicorn)
  ├── db        — PostgreSQL 16-alpine
  ├── redis     — Redis 7-alpine (avec password)
  └── certbot   — boucle perpétuelle de renouvellement Let's Encrypt (sleep 12h)

Networks : 2 bridges Docker
  ├── internal — db + redis + api + nginx
  └── external — nginx uniquement (port 80/443 exposé)

Volumes persistants :
  - postgres_data, redis_data, certbot_webroot, certbot_certs
  - frontend/dist monté en bind RO sur nginx
```

VPS unique pour le lancement (Hetzner / OVH ~10€/mois). Scalable horizontalement à terme si > 500 joueurs simultanés.

---

## 2. Dockerfile (multi-stage)

```dockerfile
# Stage 1 : builder
FROM python:3.12-slim AS builder
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install -r requirements.txt

# Stage 2 : runtime
FROM python:3.12-slim AS runtime
RUN groupadd -r emago && useradd -r -g emago -d /app emago
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY --chown=emago:emago . .
USER emago
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

Caractéristiques :
- Multi-stage pour image runtime plus légère (~150 MB).
- Utilisateur non-root `emago`.
- HEALTHCHECK Docker via `/health`.
- Pas d'hot-reload en prod (mount supprimé vs dev).
- 4 workers Uvicorn (à ajuster selon CPU VPS).

---

## 3. docker-compose

### Dev (`docker-compose.yml`)

```yaml
services:
  db:        postgres:16-alpine, user=emago, db=emago, exposé port 5432
  redis:     redis:7-alpine, exposé port 6379
  api:       build: ., port 8000, hot-reload via volume `./app:/app/app`
volumes:     postgres_data, redis_data
```

Mot de passe par défaut `emago_dev`. Hot-reload activé pour dev.

### Prod (`docker-compose.prod.yml`)

Différences clés :
- 4 services au lieu de 3 : ajout `nginx` + `certbot`.
- `restart: always` partout.
- `db` et `redis` **non exposés** (uniquement réseau interne).
- Pas de hot-reload api.
- `redis` avec `--requirepass ${REDIS_PASSWORD}`.
- 2 réseaux `internal` (api, db, redis, nginx) et `external` (nginx uniquement).
- Logs JSON structurés avec rotation (`max-size: 10m`, `max-file: 3-5`).
- Certbot en boucle perpétuelle : `while :; do certbot renew; sleep 12h; done`.
- Volume `./frontend/dist:/usr/share/nginx/html:ro` pour servir le React build.

---

## 4. Nginx configuration

### `nginx/nginx.conf` (config globale)

- `worker_processes auto`, `worker_connections 1024`, `epoll`, `multi_accept on`.
- **Format de log JSON** `json_combined` :
  ```
  {time, remote_addr, method, uri, status, bytes_sent, request_time, upstream_response_time}
  ```
- Sendfile, tcp_nopush, tcp_nodelay on, keepalive_timeout 65.
- Gzip on : level 6, min_length 1024. Types : text/plain, css, javascript, json, xml.
- **Proxy buffers (WebSocket)** : `proxy_buffer_size 128k`, `proxy_buffers 4 256k`, `proxy_busy_buffers_size 256k`.

### `nginx/conf.d/emago.conf`

**Server 1 : HTTP (80) → HTTPS redirect** + ACME challenge `/.well-known/acme-challenge/` pour Certbot.

**Server 2 : HTTPS (443 ssl http2)**

```nginx
ssl_certificate /etc/letsencrypt/live/YOUR_DOMAIN.COM/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/YOUR_DOMAIN.COM/privkey.pem;
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers HIGH:!aNULL:!MD5;
ssl_prefer_server_ciphers on;
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;

# Security headers
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self' wss://YOUR_DOMAIN.COM;" always;

# /api/ → FastAPI
location /api/ {
    proxy_pass http://api:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_connect_timeout 10s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;
    proxy_hide_header Access-Control-Allow-Origin;  # CORS géré par FastAPI
}

# /ws — WebSocket (CRITIQUE : Upgrade headers obligatoires)
location /ws {
    proxy_pass http://api:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_read_timeout 3600s;     # 1h pour les sessions longues
    proxy_send_timeout 3600s;
    proxy_buffering off;          # streaming temps réel
}

# / — React SPA
location / {
    root /usr/share/nginx/html;
    index index.html;
    try_files $uri $uri/ /index.html;

    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2?)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    location = /index.html {
        add_header Cache-Control "no-store, no-cache, must-revalidate";
    }
}

# Health check Nginx local
location /nginx-health {
    return 200 "ok\n";
    access_log off;
    add_header Content-Type text/plain;
}
```

> ⚠️ **Sans les headers `Upgrade` et `Connection "upgrade"` sur `/ws`, Nginx renvoie 426 Upgrade Required** — le WebSocket ne fonctionne pas.

---

## 5. CI/CD GitHub Actions

### `ci.yml` — Tests + build image

Trigger : push sur `main`/`develop`, PR vers main.

**Job `test`** :
- Python 3.12, cache pip sur `backend/requirements.txt`.
- `pip install -r requirements.txt`.
- `pytest tests/services/ -v --cov=app/services --cov-report=xml:coverage.xml`.
- Upload coverage codecov v4.

**Job `build`** (needs test, branche main only) :
- Login GHCR.io avec `GITHUB_TOKEN`.
- Tags via `docker/metadata-action@v5` : `branch`, `sha-{shortsha}`, `latest` si main.
- Build multi-stage avec `target: runtime`, push GHCR avec cache GHA mode=max.
- Image : `ghcr.io/<repo>/emago-api`.

### `cd.yml` — Déploiement automatique

Trigger : `workflow_run` après CI réussi sur main.

**Job `deploy`** (si `conclusion == 'success'`) :
- `appleboy/ssh-action@v1.0.3` sur VPS.
- Script SSH inline :
  ```bash
  set -e
  cd $VPS_DEPLOY_DIR
  docker compose -f docker-compose.prod.yml pull api
  docker compose -f docker-compose.prod.yml run --rm api /opt/venv/bin/alembic upgrade head
  docker compose -f docker-compose.prod.yml up -d --no-deps api
  sleep 5
  curl -sf http://localhost:8000/health || (echo "HEALTH KO" && exit 1)
  ```

**Job `notify-failure`** : log "Déploiement échoué — rollback manuel requis". (TODO : Discord/Slack).

### Secrets GitHub à configurer

- `VPS_HOST` — IP ou DNS du VPS.
- `VPS_USER` — utilisateur SSH (`emago` créé par `install_vps.sh`).
- `VPS_SSH_KEY` — clé privée SSH (sans passphrase).
- `VPS_DEPLOY_DIR` — `/opt/emago`.
- `GITHUB_TOKEN` (auto pour GHCR).

---

## 6. Initialisation d'un VPS (procédure)

### Script `scripts/install_vps.sh`

Pour un Ubuntu 22.04 LTS frais, exécuté en root :

```bash
# 1. apt-get update && upgrade
# 2. Installation Docker (clé GPG officielle, repo Docker)
# 3. Création utilisateur `emago` (bash, groupe docker)
# 4. git clone du repo dans /opt/emago
# 5. PAUSE : copier .env.example → .env, éditer
# 6. docker compose -f docker-compose.prod.yml pull
# 7. up -d db redis
# 8. sleep 10
# 9. run --rm api alembic upgrade head
# 10. up -d (full stack)
# 11. sleep 5 + curl /health
```

### Étapes manuelles complémentaires

```bash
# DNS
# → Pointer YOUR_DOMAIN.COM vers $(curl -s ifconfig.me)

# SSL initial via Certbot
docker compose -f docker-compose.prod.yml run certbot certonly \
  --webroot -w /var/www/certbot \
  -d YOUR_DOMAIN.COM \
  --email admin@YOUR_DOMAIN.COM \
  --agree-tos --non-interactive

# Reload Nginx
docker compose -f docker-compose.prod.yml restart nginx

# Backup cron
echo "0 3 * * * /opt/emago/backend/scripts/backup_postgres.sh >> /var/log/emago_backup.log 2>&1" | crontab -
```

---

## 7. Variables d'environnement

### Production (`.env` — JAMAIS committé)

```bash
SECRET_KEY=<64-char-hex>                  # python -c "import secrets; print(secrets.token_hex(32))"
DATABASE_URL=postgresql+asyncpg://emago:<password>@db:5432/emago
POSTGRES_PASSWORD=<strong-password>
REDIS_URL=redis://:<password>@redis:6379/0
REDIS_PASSWORD=<strong-password>
APP_NAME=Emago
APP_VERSION=0.1.0
DEBUG=false                               # CRITIQUE : false en prod
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=30
RESOURCE_TICK_SECONDS=60
BUILD_QUEUE_MAX=5
FLEET_SPEED_BASE=1.0
RANKING_RECALC_MINUTES=10
FORGE_DURATION_HOURS=8
```

### Dev (`.env` actuel committé pour bootstrap, à régénérer en prod)

```bash
SECRET_KEY=467651bf5af95b0140238e48b3fe7d7be50577c0528ed2999800f11c37ad6b32
DATABASE_URL=postgresql+asyncpg://emago:emago_dev@localhost:5432/emago
REDIS_URL=redis://localhost:6379/0
DEBUG=true
# (autres valeurs identiques aux defaults)
```

---

## 8. Backups PostgreSQL

### Script `scripts/backup_postgres.sh`

Cron quotidien `0 3 * * *`. Logique :

1. Crée `$PROJECT_DIR/backups/` si absent.
2. `docker compose -f docker-compose.prod.yml exec -T db pg_dump -U emago -d emago --no-owner --no-acl | gzip -9 > emago_${TIMESTAMP}.sql.gz`.
3. Log la taille du fichier généré.
4. **Si `BACKUP_S3_BUCKET` set** : `aws s3 cp ... s3://$BUCKET/emago_backups/`.
5. **Purge** : `find ... -name "emago_*.sql.gz" -mtime +$RETAIN_DAYS -delete` (défaut 30j).

Tous les logs ont un timestamp ISO 8601 UTC en préfixe.

### Restauration

```bash
# Décompresser et restaurer un backup
gunzip emago_20260501_030000.sql.gz
docker compose -f docker-compose.prod.yml exec -T db psql -U emago -d emago < emago_20260501_030000.sql
```

---

## 9. Monitoring

### Endpoint `/health`

Retourne 200 (ok) ou 503 (degraded) selon état DB + Redis :

```json
{
  "status": "ok",
  "version": "0.1.0",
  "checks": { "db": "ok", "redis": "ok" },
  "timestamp": 1714521600.123
}
```

### Uptime Kuma (recommandation)

Image : `louislam/uptime-kuma:1`. Port 3001.

Monitors recommandés :
- HTTP `https://YOUR_DOMAIN.COM/health` (toutes les 60 s).
- TCP `db:5432`.
- TCP `redis:6379`.
- WebSocket heartbeat ping/pong sur `wss://YOUR_DOMAIN.COM/ws` (Phase 2).

Alertes : email + Discord/Slack (Phase 2).

### Logs

```bash
# Tail live
docker compose -f docker-compose.prod.yml logs -f api

# 100 dernières lignes timestampées
docker compose -f docker-compose.prod.yml logs --tail=100 -t api

# Nginx
docker compose -f docker-compose.prod.yml logs -f nginx
```

Logs JSON-structurés sur tous les services via `logging.json-file` driver Docker (max 10-20m / 3-5 fichiers de rotation).

---

## 10. Rollback

### Méthode 1 — Rollback image

```bash
cd /opt/emago
git log --oneline -5
git checkout <previous-commit-hash>
docker compose -f docker-compose.prod.yml build api
docker compose -f docker-compose.prod.yml up -d --no-deps api
```

### Méthode 2 — Rollback migration

```bash
docker compose -f docker-compose.prod.yml exec api alembic downgrade -1
```

### Méthode 3 — Restauration backup

```bash
docker compose -f docker-compose.prod.yml exec -T db psql -U emago -d emago < backups/emago_<DATE>.sql
```

---

## 11. Checklist de mise en production

```
[ ] DNS pointé vers le VPS (YOUR_DOMAIN.COM A → IP)
[ ] .env créé et rempli (SECRET_KEY 64-char hex, mots de passe forts)
[ ] DEBUG=false en prod
[ ] Docker + Compose installés (`install_vps.sh`)
[ ] git clone /opt/emago
[ ] docker compose pull
[ ] docker compose up -d db redis (sleep 10)
[ ] alembic upgrade head (crée toutes les tables + trigger immuabilité + seed scar_tags)
[ ] docker compose up -d (full stack)
[ ] Certbot SSL initial (certonly --webroot)
[ ] Reload Nginx
[ ] curl /health → 200
[ ] Tester depuis browser https://YOUR_DOMAIN.COM
[ ] Tester WebSocket (login → DevTools Network → ws frame)
[ ] Cron backup PostgreSQL (0 3 * * *)
[ ] Cron renew Certbot (0 0 1 * * — premier de chaque mois)
[ ] Configurer GitHub Secrets (VPS_HOST, USER, SSH_KEY, DEPLOY_DIR)
[ ] Push test sur main → CD trigger → deploy auto
[ ] Configurer Uptime Kuma (Phase 2)
[ ] Tester rollback procedure (sur env stage)
```

---

## 12. Points de vigilance

1. **WebSocket et Nginx** : sans les headers `Upgrade $http_upgrade` et `Connection "upgrade"`, Nginx renvoie **426 Upgrade Required**. Vérifier en CI ou manuellement après chaque modif Nginx.

2. **APScheduler et redémarrage** : au restart container `api`, le scheduler redémarre. Forges en cours seront finalisées au prochain tick (60 s max décalage). **Aucune donnée perdue** car `completed_at` est en BDD.

3. **Scaling horizontal** : `ConnectionManager` WebSocket est en mémoire — un seul process. Pour scaler, **remplacer par broker Redis pub/sub**. La fonction `subscribe_player_events` est déjà préparée (écoute Redis sur `emago:events:player:{id}`).

4. **Migrations en production** : toujours exécuter `alembic upgrade head` **AVANT** de redémarrer l'API. La migration 0001 crée le trigger PG `prevent_base_stats_update` — c'est critique.

5. **Sticky sessions WebSocket** : si scale-out vers plusieurs workers Uvicorn (ou plusieurs VPS), Nginx doit utiliser `ip_hash` pour conserver la même connexion WS sur le même backend.

6. **Secrets management** : `.env` contient SECRET_KEY, POSTGRES_PASSWORD, REDIS_PASSWORD. **Ne jamais commit**. En CI, utiliser GitHub Secrets exclusivement.

7. **Migrations destructrices** : tester `alembic downgrade` avant tout déploiement migration risquée. Si rollback impossible (ex. drop table avec data) → backup obligatoire avant.

8. **Limites slowapi** : rate limits Redis. En cas de redémarrage Redis sans persistance → quotas remis à zéro. Pas dramatique mais à noter.

---

## 13. Métriques opérationnelles cibles

| Métrique | Cible |
|---|---|
| Disponibilité (uptime) | 99 % (audit Uptime Kuma) |
| Latence API p95 | < 200 ms |
| Latence WS roundtrip | < 100 ms |
| Tick scheduler exécution | resource_tick < 5 s, fleet_arrival < 3 s, forge_tick < 2 s |
| Joueurs simultanés (1 VPS) | jusqu'à 100-200 |
| Backup quotidien | < 5 min, taille < 500 MB compressé |
| Renouvellement SSL | sans interruption (zero-downtime via certbot --webroot) |

---

## 14. Améliorations DevOps à prévoir

| Tâche | Priorité |
|---|---|
| Configurer Uptime Kuma + alertes Discord | Haute |
| Ajouter notifications Discord/Slack en cas de fail CD | Haute |
| Tester procédure de rollback complet en staging | Haute |
| Audit trimestriel de sécurité headers (`securityheaders.com`) | Moyenne |
| Migration vers Caddy v2 (alternative à Nginx + Certbot) | Basse |
| Stratégie multi-VPS api + db séparés (>500 joueurs) | Basse |
| Migration vers Celery + Redis broker (>1000 joueurs) | Basse |
| Sticky sessions WS via `ip_hash` Nginx (scale horizontal) | Basse |
| Logs centralisés (Loki + Grafana, ou Papertrail) | Moyenne |
| Métriques Prometheus + Grafana | Moyenne |
| `pip-audit` + `npm audit` automatisés en CI | Haute |
| Stratégie de purge `combat_logs > 30j` (archivage S3) | Basse |
| Tests de charge automatisés en staging | Moyenne |
| Documentation runbook incidents (DB down, Redis down, OOM, disk full) | Haute |

---

*Document Agent 9 — Mai 2026*
