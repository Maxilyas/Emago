# Emago — Checklist mise en production
# Agent 9 — DevOps | Sprint 1

## Avant le premier déploiement

### Infrastructure
- [ ] VPS provisionné (Hetzner CX21 ou OVH VPS-2 minimum : 4 Go RAM, 2 vCPU)
- [ ] Accès SSH configuré (clé publique sur le VPS)
- [ ] DNS configuré : `YOUR_DOMAIN.COM` → IP du VPS (TTL ≤ 300)
- [ ] `install_vps.sh` exécuté avec succès

### Secrets & Variables
- [ ] `backend/.env` créé depuis `.env.example` (jamais committé)
- [ ] `SECRET_KEY` généré : `python -c "import secrets; print(secrets.token_hex(32))"`
- [ ] `POSTGRES_PASSWORD` fort (généré aléatoirement)
- [ ] `REDIS_PASSWORD` fort (généré aléatoirement)
- [ ] Variables GitHub Actions configurées :
  - [ ] `VPS_HOST`
  - [ ] `VPS_USER`
  - [ ] `VPS_SSH_KEY`
  - [ ] `VPS_DEPLOY_DIR`

### SSL
- [ ] Certificat Let's Encrypt obtenu (via certbot dans le conteneur)
- [ ] HTTPS testé : `curl -I https://YOUR_DOMAIN.COM`
- [ ] Redirect HTTP → HTTPS vérifié
- [ ] Renouvellement automatique testé : `docker compose run --rm certbot renew --dry-run`

### Base de données
- [ ] Migrations appliquées : `docker compose run --rm api alembic upgrade head`
- [ ] Tables vérifiées : `docker compose exec db psql -U emago -c "\dt"`
- [ ] Backup manuel testé : `./scripts/backup_postgres.sh`
- [ ] Cron backup configuré sur le VPS

### Application
- [ ] `GET /health` retourne 200 en HTTPS
- [ ] `POST /api/v1/auth/register` fonctionne
- [ ] `POST /api/v1/auth/login` fonctionne
- [ ] WebSocket `wss://YOUR_DOMAIN.COM/ws?token=XXX` accepte la connexion
- [ ] Swagger désactivé en prod (`DEBUG=false`)

### Monitoring
- [ ] Uptime Kuma installé (optionnel sur VPS, ou service externe)
- [ ] Alerte email/Discord configurée sur `GET /health`
- [ ] Logs structurés vérifiés : `docker compose logs api | head -20`

## Procédure de rollback

En cas de déploiement raté :

```bash
# Sur le VPS
cd /opt/emago/backend

# Identifier le tag précédent
docker images ghcr.io/YOUR_ORG/emago-api --format "{{.Tag}}" | head -5

# Revenir à la version précédente
docker compose -f docker-compose.prod.yml stop api
docker compose -f docker-compose.prod.yml run -e IMAGE_TAG=sha-PREVIOUS api up -d

# Si la migration a cassé quelque chose
docker compose -f docker-compose.prod.yml run --rm api alembic downgrade -1
```
