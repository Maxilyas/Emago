# Emago — Spécification DevOps complète
> Document destiné à **Agent 9 — DevOps**
> Stack : Docker + Nginx + GitHub Actions + Let's Encrypt + pg_dump

---

## 1. Architecture de déploiement

```
Internet (443/80)
    │
  Nginx (SSL termination, WS proxy, static files)
    ├── /api/v1/*  →  FastAPI :8000
    ├── /ws        →  FastAPI :8000 (WebSocket — upgrade headers obligatoires)
    └── /*         →  React build (fichiers statiques)

Docker Compose (VPS unique) :
  nginx     — reverse proxy
  api       — FastAPI (Uvicorn)
  db        — PostgreSQL 16
  redis     — Redis 7
  certbot   — renouvellement SSL Let's Encrypt
```

---

## 2. Variables d'environnement requises

Le fichier `.env` **ne doit jamais être commité**. Utiliser `.env.example` comme template.

```bash
# Obligatoire — générer avec :
# python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=<64-char-hex>

# PostgreSQL
DATABASE_URL=postgresql+asyncpg://emago:<password>@db:5432/emago
POSTGRES_PASSWORD=<strong-password>

# Redis
REDIS_URL=redis://redis:6379/0

# App
APP_NAME=Emago
APP_VERSION=0.1.0
DEBUG=false

# JWT
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=30

# Game tuning
RESOURCE_TICK_SECONDS=60
BUILD_QUEUE_MAX=5
FLEET_SPEED_BASE=1.0
RANKING_RECALC_MINUTES=10
FORGE_DURATION_HOURS=8
```

---

## 3. nginx/nginx.conf à créer

```nginx
# /nginx/nginx.conf
# ⚠️ Le proxy WebSocket nécessite les headers Upgrade et Connection

events {
    worker_connections 1024;
}

http {
    upstream api {
        server api:8000;
    }

    # Redirect HTTP → HTTPS
    server {
        listen 80;
        server_name emago.yourdomain.com;

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        location / {
            return 301 https://$host$request_uri;
        }
    }

    server {
        listen 443 ssl;
        server_name emago.yourdomain.com;

        ssl_certificate     /etc/letsencrypt/live/emago.yourdomain.com/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/emago.yourdomain.com/privkey.pem;

        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
        ssl_prefer_server_ciphers off;

        # Sécurité headers
        add_header X-Content-Type-Options nosniff;
        add_header X-Frame-Options SAMEORIGIN;
        add_header X-XSS-Protection "1; mode=block";

        # API REST
        location /api/ {
            proxy_pass http://api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # Timeouts
            proxy_read_timeout 60s;
            proxy_connect_timeout 10s;
        }

        # WebSocket — headers Upgrade/Connection OBLIGATOIRES
        location /ws {
            proxy_pass http://api;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;

            # WS keepalive — doit dépasser le ping client (60s recommandé)
            proxy_read_timeout 120s;
            proxy_send_timeout 120s;
        }

        # React build (fichiers statiques)
        location / {
            root /var/www/frontend;
            try_files $uri $uri/ /index.html;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }

        # Assets statiques avec cache long
        location ~* \.(js|css|png|jpg|gif|ico|svg|woff2)$ {
            root /var/www/frontend;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
}
```

---

## 4. docker-compose.yml production (à compléter depuis la base livrée)

Le fichier `docker-compose.yml` fourni dans le ZIP est la base de dev.
Pour la **production**, créer `docker-compose.prod.yml` :

```yaml
# docker-compose.prod.yml
version: "3.9"

services:
  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./frontend/dist:/var/www/frontend:ro   # build React
      - certbot_data:/etc/letsencrypt:ro
      - certbot_www:/var/www/certbot:ro
    depends_on:
      - api

  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: emago
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: emago
    volumes:
      - postgres_data:/var/lib/postgresql/data
    # Ne pas exposer le port 5432 en production

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: redis-server --save 60 1 --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    # Ne pas exposer le port 6379 en production

  api:
    build: .
    restart: unless-stopped
    env_file: .env
    environment:
      DATABASE_URL: postgresql+asyncpg://emago:${POSTGRES_PASSWORD}@db:5432/emago
      REDIS_URL: redis://:${REDIS_PASSWORD}@redis:6379/0
      DEBUG: "false"
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    # Pas de volume mount en prod (image immuable)

  certbot:
    image: certbot/certbot
    volumes:
      - certbot_data:/etc/letsencrypt
      - certbot_www:/var/www/certbot
    # Exécuter manuellement : docker compose run certbot certonly ...

volumes:
  postgres_data:
  redis_data:
  certbot_data:
  certbot_www:
```

---

## 5. GitHub Actions CI/CD

```yaml
# .github/workflows/deploy.yml
name: Deploy Emago Backend

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run unit tests (no DB required)
        run: pytest tests/services/ -v --tb=short
        env:
          SECRET_KEY: "ci-test-key-not-real"
          DATABASE_URL: "postgresql+asyncpg://x:x@localhost/x"

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v4

      - name: Deploy to VPS
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.VPS_HOST }}
          username: ${{ secrets.VPS_USER }}
          key: ${{ secrets.VPS_SSH_KEY }}
          script: |
            cd /opt/emago
            git pull origin main
            docker compose -f docker-compose.prod.yml build api
            docker compose -f docker-compose.prod.yml up -d --no-deps api
            docker compose -f docker-compose.prod.yml exec -T api alembic upgrade head
            echo "Déploiement terminé"
```

**Secrets GitHub à configurer :**
- `VPS_HOST` — IP ou domaine du VPS
- `VPS_USER` — utilisateur SSH (ex: `emago`)
- `VPS_SSH_KEY` — clé privée SSH (sans passphrase)

---

## 6. Initialisation du VPS (première fois)

```bash
# 1. Sur le VPS — cloner le repo
ssh user@vps
git clone https://github.com/yourorg/emago /opt/emago
cd /opt/emago

# 2. Créer le .env
cp .env.example .env
nano .env   # renseigner tous les champs obligatoires

# 3. SSL Let's Encrypt (avant de lancer nginx)
docker compose -f docker-compose.prod.yml run certbot certonly \
  --webroot -w /var/www/certbot \
  -d emago.yourdomain.com \
  --email admin@yourdomain.com \
  --agree-tos --non-interactive

# 4. Premier démarrage
docker compose -f docker-compose.prod.yml up -d

# 5. Migrations BDD
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
# → Crée toutes les tables + seed scar_tags (500 tags narratifs)

# 6. Vérification
curl https://emago.yourdomain.com/health
# → {"status": "ok", "version": "0.1.0"}
```

---

## 7. Backup automatique PostgreSQL

```bash
# /opt/emago/scripts/backup.sh
#!/bin/bash
set -e

BACKUP_DIR="/opt/backups/emago"
DATE=$(date +%Y%m%d_%H%M%S)
FILENAME="emago_db_${DATE}.sql.gz"

mkdir -p $BACKUP_DIR

docker compose -f /opt/emago/docker-compose.prod.yml exec -T db \
  pg_dump -U emago emago | gzip > "$BACKUP_DIR/$FILENAME"

# Garder seulement les 30 derniers backups
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

echo "Backup : $FILENAME ($(du -sh "$BACKUP_DIR/$FILENAME" | cut -f1))"
```

```bash
# Crontab (sudo crontab -e)
# Backup quotidien à 3h du matin
0 3 * * * /opt/emago/scripts/backup.sh >> /var/log/emago-backup.log 2>&1

# Renouvellement SSL mensuel
0 0 1 * * docker compose -f /opt/emago/docker-compose.prod.yml run certbot renew \
  && docker compose -f /opt/emago/docker-compose.prod.yml restart nginx
```

---

## 8. Monitoring

**Uptime Kuma** (recommandé — auto-hébergé) :

```yaml
# Ajouter dans docker-compose.prod.yml
  uptime-kuma:
    image: louislam/uptime-kuma:1
    restart: unless-stopped
    ports:
      - "3001:3001"
    volumes:
      - uptime_data:/app/data
```

Moniteurs à configurer dans Uptime Kuma :
- **HTTP** : `https://emago.yourdomain.com/health` → vérifie `status: ok`
- **TCP** : `db:5432` (interne Docker)
- **TCP** : `redis:6379` (interne Docker)
- **WebSocket** : `wss://emago.yourdomain.com/ws` (heartbeat ping/pong)

---

## 9. Procédure de rollback

```bash
# Rollback rapide (revenir à l'image précédente)
cd /opt/emago
git log --oneline -5   # trouver le hash du commit précédent

# Option 1 : git rollback
git checkout <previous-commit-hash>
docker compose -f docker-compose.prod.yml build api
docker compose -f docker-compose.prod.yml up -d --no-deps api

# Option 2 : rollback migration Alembic si schéma changé
docker compose -f docker-compose.prod.yml exec api alembic downgrade -1
```

---

## 10. Logs

```bash
# Logs API en temps réel
docker compose -f docker-compose.prod.yml logs -f api

# Logs avec timestamps, 100 dernières lignes
docker compose -f docker-compose.prod.yml logs --tail=100 -t api

# Logs nginx (access log)
docker compose -f docker-compose.prod.yml logs -f nginx
```

Les logs applicatifs sont au format texte standard Python logging.
Pour les passer en **JSON structuré** (recommandé pour ingestion ELK/Loki), ajouter dans `app/main.py` :

```python
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "level": record.levelname,
            "msg": record.getMessage(),
            "name": record.name,
            "time": self.formatTime(record),
        })

# Dans lifespan ou au démarrage
logging.basicConfig(handlers=[logging.StreamHandler()])
logging.getLogger().handlers[0].setFormatter(JSONFormatter())
```

---

## 11. Points de vigilance spécifiques au projet

### WebSocket et Nginx
Le header `Upgrade: websocket` **doit** être proxyfié. Sans les deux lignes :
```nginx
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection "upgrade";
```
Le WebSocket ne fonctionnera pas — les clients recevront une erreur 426.

### APScheduler et redémarrage
Au redémarrage du conteneur `api`, APScheduler repart de zéro. Les forges en cours continueront à être finalisées au prochain tick (60s max de décalage). **Aucune donnée n'est perdue** car `completed_at` est stocké en BDD.

### Scaling horizontal (si nécessaire plus tard)
Le `ConnectionManager` WebSocket est **en mémoire** — un seul processus. Pour scaler à plusieurs instances, remplacer par un broker Redis pub/sub inter-process. La fonction `subscribe_player_events` est déjà prête pour cette migration (elle écoute Redis).

### Migrations en production
Toujours exécuter `alembic upgrade head` **avant** de redémarrer l'API (ordre dans le script CI/CD).
La migration 0001 crée le trigger PostgreSQL qui protège `base_stats` — c'est critique.
